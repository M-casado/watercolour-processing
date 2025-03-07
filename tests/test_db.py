import unittest
import sqlite3
import os

TEST_DB_NAME = "../data/watercolours_test.db"
SCHEMA_FILE = "../src/database/db_schema.sql"

def apply_schema_to_db(db_path=TEST_DB_NAME, schema_file=SCHEMA_FILE):
    """
    Creates a new SQLite DB or overwrites an existing test DB, applying the schema.
    """
    # If the file exists, remove it to get a fresh DB for testing.
    if os.path.exists(db_path):
        os.remove(db_path)

    # Connect to the new or just-deleted file
    conn = sqlite3.connect(db_path)
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

class TestDBSchema(unittest.TestCase):
    def setUp(self):
        """
        Ensure the test DB is freshly created from db_schema.sql before each test method.
        """
        apply_schema_to_db(TEST_DB_NAME, SCHEMA_FILE)
        self.conn = sqlite3.connect(TEST_DB_NAME)
        self.cur = self.conn.cursor()

    def tearDown(self):
        """
        Closes the test DB connection. 
        Optionally removes the test DB file to ensure a clean state for the next run.
        """
        self.conn.close()
        if os.path.exists(TEST_DB_NAME):
            os.remove(TEST_DB_NAME)

    def test_insert_raw_image_ok(self):
        """
        Example test for inserting a raw image with valid constraints.
        """
        sql = """
        INSERT INTO images (
            filename, md5_checksum, is_raw, parent_image_id,
            date_taken, order_in_batch, pipeline_version, flash_missing
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cur.execute(sql, (
            "_DSC0001.NEF",
            "abcdef1234567890abcdef1234567890",  # 32 hex
            1,          # is_raw
            None,
            "2025-01-29T12:34:56",
            1,
            "v0.1.0",
            0
        ))
        self.conn.commit()

        # Check the row
        self.cur.execute("SELECT filename, md5_checksum, is_raw, parent_image_id FROM images")
        row = self.cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "_DSC0001.NEF")
        self.assertEqual(row[1], "abcdef1234567890abcdef1234567890")
        self.assertEqual(row[2], 1)   # is_raw
        self.assertIsNone(row[3])     # raw => parent_image_id should be NULL

    def test_insert_invalid_md5(self):
        """
        Attempt to insert an image with invalid md5 (not 32 hex chars).
        Expect an integrity error due to the CHECK constraint.
        """
        with self.assertRaises(sqlite3.IntegrityError):
            self.cur.execute("""
                INSERT INTO images (filename, md5_checksum, is_raw, parent_image_id, date_taken)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "_DSC0003.NEF",
                "ZZZZZZZZZZZZZZ",  # invalid length & characters
                1,
                None,
                "2025-01-29T10:00:00"
            ))
            self.conn.commit()

    def test_insert_painting_ok(self):
        """
        Insert a painting with minimal fields, check 'personal_favourite' default=0.
        """
        self.cur.execute("""
            INSERT INTO paintings (name, explicit_year, personal_favourite)
            VALUES (?, ?, ?)
        """, ("Landscape 2021", 2021, 1))
        self.conn.commit()

        self.cur.execute("SELECT name, explicit_year, personal_favourite FROM paintings")
        row = self.cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Landscape 2021")
        self.assertEqual(row[1], 2021)
        self.assertEqual(row[2], 1)

    def test_painting_images_ok(self):
        """
        Many-to-many link: painting_images
        """
        # Insert painting
        self.cur.execute("INSERT INTO paintings (name) VALUES (?)", ("MultiShots",))
        p_id = self.cur.lastrowid

        # Insert two images
        self.cur.execute("""
            INSERT INTO images (filename, md5_checksum, is_raw, parent_image_id, date_taken)
            VALUES (?, ?, ?, ?, ?)
        """, ("_DSC0100.NEF", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, None, "2025-01-29T09:00:00"))
        img1_id = self.cur.lastrowid

        self.cur.execute("""
            INSERT INTO images (filename, md5_checksum, is_raw, parent_image_id, date_taken)
            VALUES (?, ?, ?, ?, ?)
        """, ("_DSC0101.NEF", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", 1, None, "2025-01-29T09:01:01"))
        img2_id = self.cur.lastrowid

        # Link them in painting_images
        self.cur.execute("INSERT INTO painting_images (painting_id, image_id) VALUES (?, ?)", (p_id, img1_id))
        self.cur.execute("INSERT INTO painting_images (painting_id, image_id) VALUES (?, ?)", (p_id, img2_id))
        self.conn.commit()

        # Verify
        self.cur.execute("SELECT painting_id, image_id FROM painting_images")
        rows = self.cur.fetchall()
        self.assertEqual(len(rows), 2)
        self.assertIn((p_id, img1_id), rows)
        self.assertIn((p_id, img2_id), rows)

    def test_ratings_ok(self):
        """
        Insert a rating with score in [1..5]. Also store a user.
        """
        # Insert painting & image
        self.cur.execute("""
            INSERT INTO paintings (name) VALUES (?)
        """, ("Boats at Sunset",))
        pid = self.cur.lastrowid

        self.cur.execute("""
            INSERT INTO images (filename, md5_checksum, is_raw, parent_image_id, date_taken)
            VALUES (?, ?, ?, ?, ?)
        """, ("_DSC9999.NEF", "cccccccccccccccccccccccccccccccc", 1, None, "2025-01-29T20:20:20"))
        imgid = self.cur.lastrowid

        # Insert rating
        self.cur.execute("""
            INSERT INTO ratings (painting_id, image_id, score, user)
            VALUES (?, ?, ?, ?)
        """, (pid, imgid, 5, "Carlos"))
        self.conn.commit()

        # Retrieve and check
        self.cur.execute("SELECT painting_id, image_id, score, user FROM ratings")
        row = self.cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], pid)
        self.assertEqual(row[1], imgid)
        self.assertEqual(row[2], 5)
        self.assertEqual(row[3], "Carlos")

    def test_ratings_invalid_score(self):
        """
        Try inserting a rating outside [1..5].
        """
        # Insert painting & image
        self.cur.execute("""INSERT INTO paintings (name) VALUES (?)""", ("Bad Rating Test",))
        pid = self.cur.lastrowid
        self.cur.execute("""
            INSERT INTO images (filename, md5_checksum, is_raw, parent_image_id, date_taken)
            VALUES (?, ?, ?, ?, ?)
        """, ("_DSC9998.NEF", "dddddddddddddddddddddddddddddddd", 1, None, "2025-01-29T21:21:21"))
        imgid = self.cur.lastrowid

        with self.assertRaises(sqlite3.IntegrityError):
            self.cur.execute("""
                INSERT INTO ratings (painting_id, image_id, score)
                VALUES (?, ?, ?)
            """, (pid, imgid, 10))  # invalid
            self.conn.commit()

if __name__ == "__main__":
    unittest.main()
