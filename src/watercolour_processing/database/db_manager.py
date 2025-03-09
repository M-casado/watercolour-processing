"""
db_manager.py

Provides a DatabaseManager class for interacting with the watercolour SQLite DB.
Ensures the schema is present, offers CRUD methods, and handles custom exceptions.
"""

import os
import sqlite3
from typing import Optional

from watercolour_processing.logging_config import get_logger
logger = get_logger(__name__)

class DatabaseError(Exception):
    """General exception for database-related errors."""
    pass

class DuplicateImageError(DatabaseError):
    """Raised when attempting to insert an image whose MD5 already exists."""
    pass

class DatabaseManager:
    """
    Manages a single connection to the SQLite database, verifying schema
    and providing basic insert/update methods for images, paintings, etc.
    """

    def __init__(self, db_path: str, schema_path: Optional[str] = None):
        """
        Initialises a DatabaseManager with a DB file path.
        If the main tables are missing, tries to apply db_schema.sql if schema_path is provided.
        """
        self.db_path = db_path
        self.schema_path = schema_path
        self.conn: Optional[sqlite3.Connection] = None
        self.open_connection()
        self._ensure_schema()

    def open_connection(self) -> None:
        """Opens the SQLite connection and enables foreign key constraints."""
        if not self.conn:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.execute("PRAGMA foreign_keys = ON;")
                logger.info(f"Opened SQLite connection to '{self.db_path}' with foreign keys on.")
            except sqlite3.Error as e:
                msg = f"Failed to connect to {self.db_path}: {e}"
                logger.error(msg)
                raise DatabaseError(msg)

    def close_connection(self) -> None:
        """Closes the SQLite connection if it exists."""
        if self.conn:
            try:
                self.conn.close()
                logger.info(f"Closed connection to '{self.db_path}'.")
            except sqlite3.Error as e:
                msg = f"Error closing DB connection: {e}"
                logger.error(msg)
                raise DatabaseError(msg)
            self.conn = None

    def _ensure_schema(self) -> None:
        """
        Checks if core tables exist. If not, applies db_schema.sql (if schema_path is set).
        Otherwise raises an error if no schema_path is available.
        """
        if not self._tables_present():
            if not self.schema_path or not os.path.exists(self.schema_path):
                msg = "Database schema is missing and schema_path was not provided or invalid."
                logger.error(msg)
                raise DatabaseError(msg)
            try:
                logger.info(f"No existing schema found; applying from '{self.schema_path}'.")
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                self.conn.executescript(sql_script)
                logger.info("Database schema applied successfully.")
            except sqlite3.Error as e:
                msg = f"Error applying schema: {e}"
                logger.error(msg)
                raise DatabaseError(msg)

    def _tables_present(self) -> bool:
        """Quick check for key tables. We'll need to add more if we change the db_schema.sql."""
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing = {row[0] for row in cur.fetchall()}
            required = {"images", "paintings", "painting_images", "ratings"}
            tables_found = required.issubset(existing)
            logger.debug(f"Tables present check:  Result={tables_found} Found: [{existing}], Needed [{required}]")
            return tables_found
        except sqlite3.Error as e:
            msg = f"Error checking existing tables: {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    def __del__(self):
        """Ensures connection is closed on object deletion."""
        self.close_connection()

    # -----------------------------------------------------------------------
    # IMAGE METHODS
    # -----------------------------------------------------------------------

    def insert_image(
        self,
        filename: str,
        file_path: Optional[str],
        md5_checksum: str,
        is_raw: int = 1,
        parent_image_id: Optional[int] = None,
        date_taken: Optional[str] = None,
        order_in_batch: Optional[int] = None,
        pipeline_version: Optional[str] = None,
        flash_missing: int = 0,
        cropped: int = 0,
        cropped_date: Optional[str] = None,
        rotation_degrees: int = 0,
        rotated_date: Optional[str] = None
    ) -> int:
        """Inserts a new row into images, returning the new image_id."""
        if self.get_image_by_md5(md5_checksum) is not None:
            logger.warning(f"Duplicate MD5 {md5_checksum} detected for file '{file_path}'.")
            raise DuplicateImageError(f"Duplicate MD5: {md5_checksum}")

        sql = """
        INSERT INTO images (
            filename, file_path, md5_checksum, is_raw, parent_image_id, date_taken,
            order_in_batch, pipeline_version, flash_missing,
            cropped, cropped_date, rotation_degrees, rotated_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            filename,
            file_path,
            md5_checksum,
            is_raw,
            parent_image_id,
            date_taken,
            order_in_batch,
            pipeline_version,
            flash_missing,
            cropped,
            cropped_date,
            rotation_degrees,
            rotated_date
        )
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            self.conn.commit()
            new_id = cur.lastrowid
            logger.debug(f"Inserted image (ID={new_id}, filename='{filename}'), file_path='{file_path}'.")
            return new_id
        except sqlite3.Error as e:
            msg = f"Error inserting image '{filename}': {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    def get_image_by_md5(self, md5_checksum: str):
        """Fetches a row from images by MD5 or returns None if not found."""
        sql = "SELECT * FROM images WHERE md5_checksum = ?"
        try:
            cur = self.conn.cursor()
            cur.execute(sql, (md5_checksum,))
            row = cur.fetchone()
            logger.debug(f"get_image_by_md5({md5_checksum}) -> image_id: {row} {row is not None}")
            return row
        except sqlite3.Error as e:
            msg = f"Error retrieving image by MD5={md5_checksum}: {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    def update_image(self, image_id: int, **kwargs) -> None:
        """
        Updates fields of an existing image record.
        Example usage: update_image(image_id=5, cropped=1, cropped_date='2025-01-30T10:00:00')
        """
        if not kwargs:
            logger.debug(f"No update requested for image_id={image_id}.")
            return

        columns = []
        params = []
        for key, val in kwargs.items():
            columns.append(f"{key} = ?")
            params.append(val)
        sql = f"UPDATE images SET {', '.join(columns)} WHERE image_id = ?"
        params.append(image_id)
        try:
            cur = self.conn.cursor()
            cur.execute(sql, tuple(params))
            self.conn.commit()
            logger.debug(f"Updated image_id={image_id} with {kwargs}.")
        except sqlite3.Error as e:
            msg = f"Error updating image_id={image_id}: {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    # -----------------------------------------------------------------------
    # PAINTING METHODS
    # -----------------------------------------------------------------------

    def insert_painting(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        explicit_year: Optional[int] = None,
        inferred_year: Optional[int] = None,
        personal_favourite: int = 0
    ) -> int:
        """Inserts a painting into paintings, returning painting_id."""
        sql = """
        INSERT INTO paintings
        (name, description, explicit_year, inferred_year, personal_favourite)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (name, description, explicit_year, inferred_year, personal_favourite)
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            self.conn.commit()
            new_id = cur.lastrowid
            logger.debug(f"Inserted painting with painting_id={new_id}, name='{name}'.")
            return new_id
        except sqlite3.Error as e:
            msg = f"Error inserting painting '{name}': {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    def update_painting(self, painting_id: int, **kwargs) -> None:
        """
        Updates fields of an existing painting record.
        e.g. update_painting(3, inferred_year=2015)
        """
        if not kwargs:
            logger.debug(f"No update requested for painting_id={painting_id}.")
            return

        columns = []
        params = []
        for key, val in kwargs.items():
            columns.append(f"{key} = ?")
            params.append(val)
        sql = f"UPDATE paintings SET {', '.join(columns)} WHERE painting_id = ?"
        params.append(painting_id)
        try:
            cur = self.conn.cursor()
            cur.execute(sql, tuple(params))
            self.conn.commit()
            logger.debug(f"Updated painting_id={painting_id} with {kwargs}.")
        except sqlite3.Error as e:
            msg = f"Error updating painting_id={painting_id}: {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    # -----------------------------------------------------------------------
    # LINK METHODS
    # -----------------------------------------------------------------------

    def link_painting_to_image(self, painting_id: int, image_id: int) -> None:
        """Inserts a row into painting_images for many-to-many linking."""
        sql = "INSERT INTO painting_images (painting_id, image_id) VALUES (?, ?)"
        try:
            cur = self.conn.cursor()
            cur.execute(sql, (painting_id, image_id))
            self.conn.commit()
            logger.debug(f"Linked painting_id={painting_id} to image_id={image_id}.")
        except sqlite3.Error as e:
            msg = f"Error linking painting_id={painting_id} to image_id={image_id}: {e}"
            logger.error(msg)
            raise DatabaseError(msg)

    # -----------------------------------------------------------------------
    # RATING METHODS
    # -----------------------------------------------------------------------

    def insert_rating(
        self,
        painting_id: int,
        image_id: int,
        score: int,
        user: Optional[str] = None
    ) -> int:
        """Inserts a row into ratings, returning rating_id."""
        sql = """
        INSERT INTO ratings (painting_id, image_id, score, user)
        VALUES (?, ?, ?, ?)
        """
        params = (painting_id, image_id, score, user)
        try:
            cur = self.conn.cursor()
            cur.execute(sql, params)
            self.conn.commit()
            new_id = cur.lastrowid
            logger.debug(f"Inserted rating_id={new_id} for painting_id={painting_id}, image_id={image_id}, score={score}.")
            return new_id
        except sqlite3.Error as e:
            msg = f"Error inserting rating for painting_id={painting_id}, image_id={image_id}: {e}"
            logger.error(msg)
            raise DatabaseError(msg)