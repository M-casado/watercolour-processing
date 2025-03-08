# tests/test_db_manager.py

import os
import pytest
import sqlite3
from watercolour_processing.database.db_manager import (
    DatabaseManager,
    DatabaseError,
    DuplicateImageError
)

TEST_DB = "data/watercolours_test.db"
SCHEMA_FILE = "src/watercolour_processing/database/db_schema.sql"

@pytest.fixture
def clean_test_db():
    """
    Removes any existing test DB before tests, then yields.
    After tests, remove it again for cleanliness.
    """
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_insert_image_ok(clean_test_db):
    """
    Inserts a valid raw image, verifying the returned ID.
    Checks that a duplicate MD5 triggers DuplicateImageError.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    img_id = db.insert_image(
        filename="_DSC0001.NEF",
        md5_checksum="abcdef1234567890abcdef1234567890",  # 32 hex
        date_taken="2025-01-29T12:34:56",
        order_in_batch=1,
        pipeline_version="v0.1.0"
    )
    assert img_id > 0

    with pytest.raises(DuplicateImageError):
        db.insert_image(
            filename="_DSC0001_DUP.NEF",
            md5_checksum="abcdef1234567890abcdef1234567890",
            date_taken="2025-01-29T12:35:00"
        )
    db.close_connection()

def test_update_image(clean_test_db):
    """
    Inserts then updates an image record, verifying DB changes.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    img_id = db.insert_image(
        filename="_DSC0002.NEF",
        md5_checksum="11111111111111111111111111111111",
        date_taken="2025-01-29T10:00:00"
    )
    db.update_image(img_id, cropped=1, cropped_date="2025-01-29T11:00:00")
    row = db.get_image_by_md5("11111111111111111111111111111111")
    assert row is not None
    # row columns: (image_id, filename, md5_checksum, is_raw, parent_image_id, date_taken, order_in_batch,
    #               pipeline_version, flash_missing, cropped, cropped_date, rotation_degrees, rotated_date)
    assert row[9] == 1  # cropped
    assert row[10] == "2025-01-29T11:00:00"

def test_insert_painting_ok(clean_test_db):
    """
    Inserts a painting, verifying painting_id > 0.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    p_id = db.insert_painting(
        name="Sunset",
        description="Warm painting",
        explicit_year=2020
    )
    assert p_id > 0

def test_update_painting(clean_test_db):
    """
    Inserts and updates a painting record.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    p_id = db.insert_painting(name="Boat Scene", explicit_year=2014)
    db.update_painting(p_id, inferred_year=2015, personal_favourite=1)
    cur = db.conn.cursor()
    cur.execute("SELECT inferred_year, personal_favourite FROM paintings WHERE painting_id = ?", (p_id,))
    row = cur.fetchone()
    assert row == (2015, 1)

def test_link_painting_to_image(clean_test_db):
    """
    Checks many-to-many linking in painting_images.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    img_id = db.insert_image(
        filename="_DSC9999.NEF",
        md5_checksum="cccccccccccccccccccccccccccccccc",
        date_taken="2025-01-29T09:09:09"
    )
    p_id = db.insert_painting(name="MultiShots")
    db.link_painting_to_image(p_id, img_id)
    cur = db.conn.cursor()
    cur.execute("SELECT painting_id, image_id FROM painting_images")
    row = cur.fetchone()
    assert row == (p_id, img_id)

def test_insert_rating(clean_test_db):
    """
    Inserts an image, painting, then rating referencing both.
    """
    db = DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE)
    i_id = db.insert_image(
        filename="_DSC7777.NEF",
        md5_checksum="dddddddddddddddddddddddddddddddd",
        date_taken="2025-01-29T08:08:08"
    )
    p_id = db.insert_painting(name="Rating Test")
    r_id = db.insert_rating(p_id, i_id, score=5, user="Maria")
    assert r_id > 0
    cur = db.conn.cursor()
    cur.execute("SELECT painting_id, image_id, score, user FROM ratings WHERE rating_id = ?", (r_id,))
    row = cur.fetchone()
    assert row == (p_id, i_id, 5, "Maria")
