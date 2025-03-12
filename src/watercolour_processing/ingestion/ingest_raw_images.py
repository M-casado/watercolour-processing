"""
ingest_raw_images.py

Scans files or folders for raw images (by default .NEF), computes MD5,
extracts EXIF date, and inserts them into the watercolour DB if not duplicates.
"""

import os
import hashlib
import exifread
from typing import List, Optional

from watercolour_processing.logging_config import get_logger
from watercolour_processing.database.db_manager import DatabaseManager, DuplicateImageError

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
    if extensions is None:
        extensions = [".nef"]

    stats = {"scanned": 0, "inserted": 0, "duplicates": 0, "total_paths": len(paths)}
    logger.info(f"Starting ingestion with paths={paths}")

    with DatabaseManager(db_path, schema_path) as db:

        def _process_file(file_path: str):
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in extensions:
                return

            stats["scanned"] += 1
            md5 = compute_md5(file_path)
            exif_date = extract_exif_date(file_path)
            filename = os.path.basename(file_path)

            logger.debug(f"Processing '{file_path}' (MD5={md5}, exif_date={exif_date})")
            try:
                db.insert_image(
                    filename=filename,
                    file_path=file_path,
                    md5_checksum=md5,
                    date_taken=exif_date,
                    pipeline_version=pipeline_version
                )
                stats["inserted"] += 1
                logger.info(f"Inserted new image: {file_path}")
            except DuplicateImageError:
                stats["duplicates"] += 1
                logger.warning(f"Duplicate MD5 found for '{file_path}', skipping.")

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
        default="data/watercolours.db",
        help="Path to the SQLite DB file (e.g. 'data/watercolours.db')."
    )
    parser.add_argument(
        "--schema",
        default="src/watercolour_processing/database/db_schema.sql",
        help="Optional path to db_schema.sql if the DB schema may need applying (e.g. 'src/watercolour_processing/database/db_schema.sql')."
    )
    parser.add_argument(
        "--extensions",
        nargs='+',
        default=[".nef"],
        help="List of file extensions to process (default is ['.nef'])."
    )
    parser.add_argument(
        "--pipeline_version",
        default="v0.1.0",
        help="Pipeline version string to record in DB (default: v0.1.0)."
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
