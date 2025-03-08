# test_db_manager.py

import os
import pytest
import sqlite3
from watercolour_processing.database.db_manager import (
    DatabaseManager, DatabaseError, DuplicateImageError
)

TEST_DB = "../data/watercolours_test.db"
SCHEMA_FILE = "../src/database/db_schema.sql"

@pytest.fixture
def clean_test_db():
    """
    Pytest fixture to remove an existing test DB if present, then yield.
    After tests, removes it again.
    """
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_insert_image_ok(clean_test_db):
    """
    Inserts a valid raw image and verifies the returned image_id.
    Also checks that a subsequent duplicate MD5 triggers DuplicateImageError.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
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
                md5_checksum="abcdef1234567890abcdef1234567890",  # same MD5
                date_taken="2025-01-29T12:35:00"
            )

def test_update_image(clean_test_db):
    """
    Inserts and then updates an image record.
    Verifies changes in DB.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
        img_id = db.insert_image(
            filename="_DSC0002.NEF",
            md5_checksum="11111111111111111111111111111111",
            date_taken="2025-01-29T10:00:00"
        )
        db.update_image(img_id, cropped=1, cropped_date="2025-01-29T11:00:00")

        # Confirm the update
        row = db.get_image_by_md5("11111111111111111111111111111111")
        assert row is not None
        # Indices: 0=image_id, 1=filename, 2=md5_checksum, 3=is_raw, ...
        assert row[9] == 1  # cropped
        assert row[10] == "2025-01-29T11:00:00"  # cropped_date

def test_insert_painting_ok(clean_test_db):
    """
    Inserts a painting and verifies a valid painting_id is returned.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
        p_id = db.insert_painting(
            name="Sunset",
            description="A lovely warm painting",
            explicit_year=2020
        )
        assert p_id > 0

def test_update_painting(clean_test_db):
    """
    Inserts and then updates a painting record.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
        p_id = db.insert_painting(name="Boat Scene", explicit_year=2014)
        db.update_painting(p_id, inferred_year=2015, personal_favourite=1)

        # Verify
        cur = db.conn.cursor()
        cur.execute("SELECT inferred_year, personal_favourite FROM paintings WHERE painting_id = ?", (p_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 2015
        assert row[1] == 1

def test_link_painting_to_image(clean_test_db):
    """
    Creates an image and a painting, then links them via painting_images.
    Verifies the link was inserted.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
        img_id = db.insert_image(
            filename="_DSC9999.NEF",
            md5_checksum="cccccccccccccccccccccccccccccccc",
            date_taken="2025-01-29T09:09:09"
        )
        p_id = db.insert_painting(name="MultiShots")
        db.link_painting_to_image(p_id, img_id)

        # Confirm the link
        sql = "SELECT painting_id, image_id FROM painting_images"
        cur = db.conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        assert row == (p_id, img_id)

def test_insert_rating(clean_test_db):
    """
    Inserts a painting, an image, then a rating referencing both.
    """
    with DatabaseManager(TEST_DB, schema_path=SCHEMA_FILE) as db:
        i_id = db.insert_image(
            filename="_DSC7777.NEF",
            md5_checksum="dddddddddddddddddddddddddddddddd",
            date_taken="2025-01-29T08:08:08"
        )
        p_id = db.insert_painting(name="Rating Test")
        rating_id = db.insert_rating(p_id, i_id, score=5, user="Juan")
        assert rating_id > 0

        # Quick check
        cur = db.conn.cursor()
        cur.execute("SELECT painting_id, image_id, score, user FROM ratings WHERE rating_id = ?", (rating_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == p_id
        assert row[1] == i_id
        assert row[2] == 5
        assert row[3] == "Juan"