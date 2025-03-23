"""
ingest_raw_images.py

Scans files or folders for raw images (by default .NEF), computes MD5,
extracts EXIF date, and inserts them into the watercolour DB if not duplicates.
"""

import os
import hashlib
import exifread
from typing import List, Optional
from PIL import Image

from watercolour_processing.logging_config import get_logger
from watercolour_processing.database.db_manager import DatabaseManager, DuplicateImageError
from watercolour_processing.utils import get_db_path, get_thumbnails_dir, get_db_schema_path, get_data_raw_path, get_pipeline_version

logger = get_logger(__name__)

def compute_md5(file_path: str) -> str:
    """
    Computes the MD5 checksum (lowercase hex) of the file at file_path.
    """
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_exif_date(file_path: str) -> Optional[str]:
    """
    Extracts the DateTimeOriginal EXIF tag (if available) and converts
    it to 'YYYY-MM-DDTHH:MM:SS' format. Returns None if absent or on error.
    """
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
        dt_raw = tags.get('EXIF DateTimeOriginal')
        if dt_raw:
            value = str(dt_raw)  # e.g. "2023:01:02 10:11:12"
            date_part, time_part = value.split()
            date_part = date_part.replace(":", "-")  # "2023:01:02" -> "2023-01-02"
            return f"{date_part}T{time_part}"
    except Exception as e:
        logger.debug(f"Failed to read EXIF from {file_path}: {e}")
    return None

def ingest_raw_images(
    paths: List[str],
    db_path: str,
    schema_path: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    pipeline_version: str = "v0.1.0"
) -> dict:
    """
    Scans the given file/folder paths for images with certain extensions,
    computes MD5 & extracts EXIF date, then inserts into DB if not duplicates.

    Args:
        paths: A list of file or directory paths to process.
        db_path: Path to the SQLite DB file.
        schema_path: Optional path to db_schema.sql (if needed).
        extensions: List of file extensions (e.g. [".nef", ".cr2"]).
                    Defaults to [".nef"] if None provided.
        pipeline_version: String describing the pipeline version (stored in DB).

    Returns:
        A summary dict with counts of scanned, inserted, duplicates, and total paths.
    """
    all_image_extensions = [".nef", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".bmp", ".webp", ".heic", ".heif", ".raw"]
    if extensions is None:
        extensions = all_image_extensions
    elif type(extensions) is list:
        print(extensions)
        print(len(extensions))
        if len(extensions) == 0:
            extensions = all_image_extensions

    stats = {"scanned": 0, "inserted": 0, "duplicates": 0, "total_paths": len(paths)}
    logger.info(f"Starting ingestion with paths={paths}")

    with DatabaseManager(db_path, schema_path) as db:

        def _process_file(file_path: str):
            # Convert the given file path to an absolute path, in case a relative path was given
            abs_path = os.path.abspath(file_path)

            ext = os.path.splitext(abs_path)[1].lower()
            if ext not in extensions:
                logger.info(f"Skipping '{abs_path}' (unsupported extension: '{ext}' not in {extensions})")
                return

            stats["scanned"] += 1
            md5 = compute_md5(abs_path)
            exif_date = extract_exif_date(abs_path)
            filename = os.path.basename(abs_path)

            logger.debug(f"Processing '{abs_path}' (MD5={md5}, exif_date={exif_date})")
            try:
                image_id = db.insert_image(
                    filename=filename,
                    file_path=abs_path,   # Storing absolute path instead of file_path
                    md5_checksum=md5,
                    date_taken=exif_date,
                    pipeline_version=pipeline_version
                )
                create_thumbnail(abs_path, image_id)
                stats["inserted"] += 1
                logger.info(f"Inserted new image: {abs_path}")
            except DuplicateImageError:
                stats["duplicates"] += 1
                logger.warning(f"Duplicate MD5 found for '{abs_path}', skipping.")

        def _process_path(path: str):
            if os.path.isfile(path):
                _process_file(path)
            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for f in files:
                        _process_file(os.path.join(root, f))
            else:
                logger.error(f"Invalid path: {path}")

        # Process each path
        for p in paths:
            _process_path(p)

    logger.info(f"Finished ingestion. Stats: {stats}")
    return stats

def create_thumbnail(full_image_path: str, image_id: int):
    """
    Creates a small 200px-wide thumbnail in thumb_dir with name {image_id}.png
    """
    thumb_dir = get_thumbnails_dir()
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir, exist_ok=True)

    thumbnail_path = os.path.join(thumb_dir, f"{image_id}.png")
    with Image.open(full_image_path) as img:
        img.thumbnail((200, 200))  # 200 px wide, aspect ratio
        img.save(thumbnail_path, "PNG")
    return thumbnail_path

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Scans files or folders for raw images, computes MD5 checksums, "
            "extracts EXIF date, and inserts them into a watercolour DB if not duplicates."
        )
    )
    parser.add_argument(
        "--db",
        default=get_db_path(),
        help="Path to the SQLite DB file (e.g. 'data/watercolours.db')."
    )
    parser.add_argument(
        "--schema",
        default=get_db_schema_path(),
        help="Optional path to db_schema.sql if the DB schema may need applying (e.g. 'src/watercolour_processing/database/db_schema.sql')."
    )
    parser.add_argument(
        "--extensions",
        nargs="*", # zero or more arguments
        default=[],
        help="List of file extensions (e.g., ['.nef', '.png']) to process (default is an empty list, where all image formats will be picked)."
    )
    parser.add_argument(
        "--pipeline_version",
        default=get_pipeline_version(),
        help="Pipeline version string to record in DB (e.g., v0.1.0)."
    )
    parser.add_argument(
        "paths",
        nargs='+',
        help="One or more file or directory paths to ingest."
    )

    args = parser.parse_args()

    ingest_raw_images(
        paths=args.paths,
        db_path=args.db,
        schema_path=args.schema,
        extensions=args.extensions,
        pipeline_version=args.pipeline_version
    )
