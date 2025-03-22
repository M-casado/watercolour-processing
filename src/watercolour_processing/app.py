import os
import re
from flask import (
    Flask, request, render_template, redirect,
    url_for, session, flash, send_file, Response, 
    stream_with_context
)
import time
from watercolour_processing.database.db_manager import DatabaseManager, DatabaseError
from watercolour_processing.ingestion.ingest_raw_images import ingest_raw_images
from watercolour_processing.utils import get_db_path, get_thumbnails_dir, get_db_schema_path, get_data_raw_path

app = Flask(__name__)

# Temporary hardcoded credentials
app.secret_key = "CHANGE_THIS_IN_PRODUCTION"  #! Required for session handling
ADMIN_PASSWORD = "admin123" #!

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

@app.route("/admin/image/<int:image_id>")
@admin_required
def admin_image_detail(image_id):
    db_path = get_db_path()
    row = None
    col_names = []
    try:
        with DatabaseManager(db_path) as db:
            cur = db.conn.cursor()

            # figure out columns from the 'images' table
            cur.execute("PRAGMA table_info(images)")
            table_info = cur.fetchall()
            col_names = [t[1] for t in table_info]  # 'name' is t[1]

            cur.execute("SELECT * FROM images WHERE image_id=?", (image_id,))
            row = cur.fetchone()

    except DatabaseError as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_list_images"))

    if not row:
        flash("Image not found in DB.", "warning")
        return redirect(url_for("admin_list_images"))
    
    # 'row' is a tuple of columns, col_names is a list of column names
    # We pass both to the template
    return render_template(
        "admin_image_detail.html",
        image_id=image_id,
        row=row,
        col_names=col_names
    )

@app.route("/admin/thumbnail/<int:image_id>")
@admin_required
def admin_thumbnail(image_id):
    thumb_dir = get_thumbnails_dir()
    thumbnail_file = os.path.join(thumb_dir, f"{image_id}.png")
    if not os.path.exists(thumbnail_file):
        return "No thumbnail", 404
    return send_file(thumbnail_file, mimetype="image/png")

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
