import os
import re
from flask import (
    Flask, request, render_template, redirect,
    url_for, session, flash, send_file, Response, 
    stream_with_context, send_file
)
import mimetypes
import time
from watercolour_processing.database.db_manager import DatabaseManager, DatabaseError
from watercolour_processing.ingestion.ingest_raw_images import ingest_raw_images
from watercolour_processing.utils import get_db_path, get_thumbnails_dir, get_db_schema_path, get_data_raw_path

app = Flask(__name__)

# Temporary hardcoded credentials
app.secret_key = "CHANGE_THIS_IN_PRODUCTION"  #! Required for session handling
ADMIN_PASSWORD = "admin123" #!
INLINE_IMAGE_TYPES = {
    "image/png", "image/jpeg", "image/gif",
    "image/webp", "image/bmp", "image/tiff"
}

# -------------------------------------------------------------------------
# HOME / LANDING
# -------------------------------------------------------------------------
@app.route("/")
def home():
    """
    Simple home/landing page. 
    Could show overall status or links to admin login.
    """
    return render_template("home.html")

# -------------------------------------------------------------------------
# ADMIN LOGIN / LOGOUT
# -------------------------------------------------------------------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    """
    Basic admin login. In production, we'd store hashed passwords 
    in a user table, not in plain text.
    """
    if request.method == "POST":
        entered_pw = request.form.get("password")
        if entered_pw == ADMIN_PASSWORD:
            session["admin"] = True
            flash("Logged in successfully as Admin.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Wrong password!", "error")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")

@app.route("/admin_logout")
def admin_logout():
    """
    Log the admin user out, clear the session.
    """
    session.pop("admin", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

def admin_required(func):
    """
    Decorator for routes that require admin login.
    """
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            flash("Admin login required.", "warning")
            return redirect(url_for("admin_login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# -------------------------------------------------------------------------
# ADMIN DASHBOARD
# -------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    The main admin panel. 
    For now, just a placeholder with links to other admin tasks.
    """
    return render_template("admin_dashboard.html")

# -------------------------------------------------------------------------
# LIST IMAGES (EXAMPLE ADMIN TASK)
# -------------------------------------------------------------------------
@app.route("/admin/images", methods=["GET"])
@admin_required
def admin_list_images():
    db_path = get_db_path()
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    filename_filter = request.args.get("filename", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    is_raw_filter = request.args.get("is_raw")     # None if unchecked, '1' if checked
    cropped_filter = request.args.get("cropped")
    rotated_filter = request.args.get("rotated")

    offset = (page - 1) * per_page

    sql_base = """
        SELECT image_id, filename, md5_checksum, date_taken, is_raw, cropped
        FROM images
        WHERE 1=1
    """
    params = []

    if filename_filter:
        sql_base += " AND filename LIKE ?"
        params.append(f"%{filename_filter}%")

    if date_from:
        sql_base += " AND date_taken >= ?"
        params.append(date_from)

    if date_to:
        sql_base += " AND date_taken <= ?"
        params.append(date_to)

    if is_raw_filter == '1':
        sql_base += " AND is_raw = 1"

    if cropped_filter == '1':
        sql_base += " AND cropped = 1"

    if rotated_filter == '1':
        sql_base += " AND rotation_degrees != 0"

    sql_base += " ORDER BY image_id LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    images = []
    total_count = 0

    try:
        with DatabaseManager(db_path) as db:
            cur = db.conn.cursor()
            cur.execute(sql_base, params)
            images = cur.fetchall()

            # total count ignoring limit
            count_sql = "SELECT COUNT(*) FROM images WHERE 1=1"
            count_params = []

            if filename_filter:
                count_sql += " AND filename LIKE ?"
                count_params.append(f"%{filename_filter}%")

            if date_from:
                count_sql += " AND date_taken >= ?"
                count_params.append(date_from)

            if date_to:
                count_sql += " AND date_taken <= ?"
                count_params.append(date_to)

            if is_raw_filter == '1':
                count_sql += " AND is_raw = 1"

            if cropped_filter == '1':
                count_sql += " AND cropped = 1"

            if rotated_filter == '1':
                count_sql += " AND rotation_degrees != 0"

            cur.execute(count_sql, count_params)
            total_count = cur.fetchone()[0]

    except DatabaseError as e:
        flash(f"Database error: {e}", "error")
        return render_template("admin_images.html", images=[], total_count=0, page=1, per_page=20, total_pages=1)

    total_pages = (total_count + per_page - 1) // per_page

    if not images:
        flash("No images found in the DB." if total_count == 0 else "No images match your filters.", "info")

    return render_template(
        "admin_images.html",
        images=images,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_count=total_count,
        filename_filter=filename_filter,
        date_from=date_from,
        date_to=date_to,
        is_raw_filter=is_raw_filter,
        cropped_filter=cropped_filter,
        rotated_filter=rotated_filter
    )

def fetch_image_record(db_path, image_id):
    """
    Helper function to retrieve a row from 'images' for a given image_id.
    Returns the entire row or None if not found.
    Raises DatabaseError if there's a DB-level issue.
    """
    with DatabaseManager(db_path) as db:
        cur = db.conn.cursor()
        cur.execute("SELECT * FROM images WHERE image_id = ?", (image_id,))
        return cur.fetchone()

def fetch_file_path(db_path, image_id):
    """
    Helper to retrieve file_path from the 'images' table for a given image_id.
    Returns the file_path string, or None if not found.
    Raises DatabaseError if there's a DB error.
    """
    with DatabaseManager(db_path) as db:
        cur = db.conn.cursor()
        cur.execute("SELECT file_path FROM images WHERE image_id = ?", (image_id,))
        row = cur.fetchone()
        return row[0] if row else None

from datetime import datetime

@app.route("/admin/image/<int:image_id>", methods=["GET", "POST"])
@admin_required
def admin_image_detail(image_id):
    """
    Displays the details of a single image. By default in read-only mode.
    If the user appends ?edit=1 in the URL, the page is in edit mode (GET).
    If the user submits the form (POST), we update the editable fields
    and redirect back to read-only mode.
    """

    db_path = get_db_path()

    # 1) If POST -> user clicked "Save Changes" in edit mode
    if request.method == "POST":
        # Extract form data for the six editable fields
        # Defaulting checkboxes to "0" if not present
        is_raw_val = request.form.get("is_raw", "0")
        date_taken_val = request.form.get("date_taken", None)
        order_in_batch_val = request.form.get("order_in_batch", None)
        pipeline_version_val = request.form.get("pipeline_version", "")
        flash_missing_val = request.form.get("flash_missing", "0")
        cropped_val = request.form.get("cropped", "0")

        # Convert booleans/ints
        is_raw_val = int(is_raw_val)
        flash_missing_val = int(flash_missing_val)
        cropped_val = int(cropped_val)
        order_in_batch_val = int(order_in_batch_val) if order_in_batch_val else None
        now_str = datetime.now().isoformat(timespec='seconds')

        # Perform DB update
        update_sql = """
            UPDATE images
               SET is_raw = ?,
                   date_taken = ?,
                   order_in_batch = ?,
                   pipeline_version = ?,
                   flash_missing = ?,
                   cropped = ?,
                   last_changed = ?
             WHERE image_id = ?
        """

        try:
            with DatabaseManager(db_path) as db:
                cur = db.conn.cursor()
                cur.execute(
                    update_sql,
                    (
                        is_raw_val,
                        date_taken_val,
                        order_in_batch_val,
                        pipeline_version_val,
                        flash_missing_val,
                        cropped_val,
                        now_str,
                        image_id
                    )
                )
                db.conn.commit()
            flash("Image fields updated successfully.", "success")

        except DatabaseError as e:
            flash(f"Error updating image fields for image_id='{image_id}': {e}", "error")

        # After saving, redirect to read-only detail view (no ?edit=1)
        return redirect(url_for("admin_image_detail", image_id=image_id))

    # 2) If GET -> either read-only or edit mode, depending on ?edit=1
    is_edit_mode = (request.args.get("edit") == "1")
    allow_inline = False
    row = None

    # 2a) Fetch the row from the DB
    try:
        row = fetch_image_record(db_path, image_id)
    except DatabaseError as e:
        flash(f"Database error while fetching image_id '{image_id}': {e}", "error")
        return redirect(url_for("admin_list_images"))

    if not row:
        flash(f"No database record found for image_id '{image_id}'.", "warning")
        return redirect(url_for("admin_list_images"))

    # 2b) Get column names
    col_names = []
    try:
        with DatabaseManager(db_path) as db:
            c2 = db.conn.cursor()
            c2.execute("PRAGMA table_info(images)")
            table_info = c2.fetchall()
            col_names = [t[1] for t in table_info]
    except DatabaseError as e:
        flash(f"Database error while reading table structure for image '{image_id}': {e}", "error")
        return redirect(url_for("admin_list_images"))

    # 2c) Check if we can display the image inline
    file_path = None
    if "file_path" in col_names:
        # We assume row is a tuple, so find the index of "file_path"
        fp_index = col_names.index("file_path")
        file_path = row[fp_index]
        if file_path:
            mime_type, _ = mimetypes.guess_type(file_path.lower())
            if mime_type in INLINE_IMAGE_TYPES:
                allow_inline = True
    else:
        flash("The 'file_path' column is missing in 'images' table.", "warning")

    # 2d) Render the detail template, passing 'is_edit_mode' to show the form if needed
    return render_template(
        "admin_image_detail.html",
        image_id=image_id,
        row=row,
        col_names=col_names,
        allow_inline=allow_inline,
        is_edit_mode=is_edit_mode  # indicates whether we show <input> or read-only
    )

@app.route("/admin/thumbnail/<int:image_id>")
def admin_thumbnail(image_id):
    """
    Serves a thumbnail (PNG) for the specified image_id if it exists.
    """
    thumb_dir = get_thumbnails_dir()
    thumbnail_file = os.path.join(thumb_dir, f"{image_id}.png")

    if not os.path.exists(thumbnail_file):
        # Return a plain text 404 or do 'return send_file(...)' of a placeholder
        return f"No thumbnail found for image_id '{image_id}' at '{thumbnail_file}'", 404

    return send_file(thumbnail_file, mimetype="image/png")

@app.route("/admin/full_image/<int:image_id>")
def admin_full_image(image_id):
    """
    Serves the full-size image file for a given image record,
    attempting inline display if the format is browser-friendly,
    else forcing download.
    """
    db_path = get_db_path()
    try:
        file_path = fetch_file_path(db_path, image_id)
    except DatabaseError as e:
        flash(f"Database error fetching file path for image '{image_id}': {e}", "error")
        return redirect(url_for("admin_image_detail", image_id=image_id))

    if not file_path:
        flash(f"No file_path found in DB for image_id '{image_id}'.", "error")
        return redirect(url_for("admin_image_detail", image_id=image_id))

    if not os.path.exists(file_path):
        flash(f"File does not exist on disk: '{file_path}'.", "error")
        return redirect(url_for("admin_image_detail", image_id=image_id))

    # Guess MIME
    mime_type, _ = mimetypes.guess_type(file_path.lower())
    if not mime_type:
        mime_type = "application/octet-stream"

    allow_inline = mime_type in INLINE_IMAGE_TYPES

    response = send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=not allow_inline  # Force download if not inline-friendly
    )
    disposition = "inline" if allow_inline else "attachment"
    response.headers["Content-Disposition"] = f'{disposition}; filename="{os.path.basename(file_path)}"'
    return response

# -------------------------------------------------------------------------
# TRIGGER INGESTION (EXAMPLE)
# -------------------------------------------------------------------------
@app.route("/admin/ingest", methods=["GET", "POST"])
@admin_required
def admin_ingest():
    db_path = get_db_path()
    schema_path = get_db_schema_path()
    default_data_folder = get_data_raw_path()

    if request.method == "POST":
        folder = request.form.get("folder", default_data_folder).strip()
        lines = []

        try:
            ingestion_results = run_ingestion_with_logs(
                folder,
                db_path=db_path,
                schema_path=schema_path
            )
            lines.extend(ingestion_results)
            lines.append("\nIngestion completed successfully.")
        except Exception as e:
            lines.append(f"ERROR: {e}")
            flash(f"Ingestion failed: {e}", "error")

        return render_template("admin_ingest_status.html", lines=lines)

    else:
        # GET: show how many image files are at the default folder
        folder = default_data_folder
        count_files = 0
        if os.path.isdir(folder):
            count_files = sum(1 for f in os.listdir(folder))

        return render_template("admin_ingest.html", folder=folder, count_files=count_files)

def run_ingestion_with_logs(folder, db_path, schema_path=None):
    """
    A sample function that calls an existing 'ingest_raw_images' logic 
    but captures line-by-line or summary info in a list of lines.
    """
    lines = []
    lines.append(f"Ingesting from: '{folder}'")
    stats = ingest_raw_images(
        paths=[folder],
        db_path=db_path,
        schema_path=schema_path
    )
    # Then build lines with stats
    lines.append(f"Total scanned: {stats.get('scanned',0)}")
    lines.append(f"Inserted: {stats.get('inserted',0)}")
    lines.append(f"Duplicates: {stats.get('duplicates',0)}")
    lines.append(f"End of ingestion.")
    return lines

# -------------------------------------------------------------------------
# CREATE THE APP
# -------------------------------------------------------------------------
def create_app():
    """
    Factory function for a more flexible config approach.
    """
    return app

if __name__ == "__main__":
    """
    Run with: python -m watercolour_processing.app
    """
    app.run(debug=True, host="0.0.0.0", port=5000)
