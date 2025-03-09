# test_ingest_raw_images.py

import os
import shutil
import pytest
import sqlite3

from watercolour_processing.ingestion.ingest_raw_images import ingest_raw_images
from watercolour_processing.database.db_manager import DatabaseManager

TEST_DB = "data/watercolours_test.db"
SCHEMA_FILE = "src/watercolour_processing/database/db_schema.sql"
TEST_FOLDER = "tests/testdata/ingestion"

@pytest.fixture
def setup_ingest_test():
    """
    Creates a temporary folder with dummy .NEF files and
    ensures a clean test DB. Cleans up afterward.
    """
    # 1) Create test folder & files
    os.makedirs(TEST_FOLDER, exist_ok=True)

    # Write some dummy bytes to simulate .NEF (or empty files)
    with open(os.path.join(TEST_FOLDER, "test001.NEF"), "wb") as f:
        f.write(b"FAKE_NEFDATA_001")

    with open(os.path.join(TEST_FOLDER, "test002.nef"), "wb") as f:
        f.write(b"FAKE_NEFDATA_002")

    # 2) Remove any existing test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    yield

    # Teardown: remove folder & DB
    shutil.rmtree(TEST_FOLDER, ignore_errors=True)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_ingest_single_folder(setup_ingest_test):
    """
    Tests ingest_raw_images on a folder containing 2 dummy NEF files.
    Expects both to be inserted (no duplicates).
    """
    stats = ingest_raw_images(
        paths=[TEST_FOLDER],
        db_path=TEST_DB,
        schema_path=SCHEMA_FILE,
        extensions=[".nef"]
    )

    # Check stats
    assert stats["total_paths"] == 1     # We passed 1 folder
    assert stats["scanned"] == 2        # 2 .nef files
    assert stats["inserted"] == 2
    assert stats["duplicates"] == 0

    # Confirm data in DB
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    cur = db.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    row = cur.fetchone()
    assert row[0] == 2, "Expected 2 rows in 'images' table"
    db.close_connection()

def test_ingest_duplicates(setup_ingest_test):
    """
    Calls ingest_raw_images twice on the same folder to check that
    second pass sees them as duplicates (same MD5).
    """
    # First ingestion
    stats1 = ingest_raw_images(
        paths=[TEST_FOLDER],
        db_path=TEST_DB,
        schema_path=SCHEMA_FILE,
        extensions=[".nef"]
    )
    assert stats1["inserted"] == 2
    assert stats1["duplicates"] == 0

    # Second ingestion with same folder
    stats2 = ingest_raw_images(
        paths=[TEST_FOLDER],
        db_path=TEST_DB,
        schema_path=SCHEMA_FILE,
        extensions=[".nef"]
    )
    assert stats2["inserted"] == 0, "All should be duplicates now"
    assert stats2["duplicates"] == 2

def test_ingest_no_matching_extensions(setup_ingest_test):
    """
    If we pass an extension list that doesn't include .nef,
    we should insert nothing.
    """
    stats = ingest_raw_images(
        paths=[TEST_FOLDER],
        db_path=TEST_DB,
        schema_path=SCHEMA_FILE,
        extensions=[".jpg"]  # no .nef
    )
    assert stats["scanned"] == 0
    assert stats["inserted"] == 0
    assert stats["duplicates"] == 0