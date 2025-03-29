----------------------------
-- TABLE: images
----------------------------
CREATE TABLE IF NOT EXISTS images (
    image_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename           TEXT NOT NULL,
    file_path          TEXT NOT NULL,
    md5_checksum TEXT NOT NULL CHECK (length(md5_checksum) = 32 AND md5_checksum GLOB '[0-9A-Fa-f]*'),      
    is_raw             INTEGER DEFAULT 1,   -- 1 = raw, 0 = processed
    parent_image_id    INTEGER,            -- if this is derived from another image
    date_taken         TEXT CHECK (date_taken GLOB '????-??-??T??:??:??'),
    order_in_batch     INTEGER,
    pipeline_version   TEXT CHECK (pipeline_version GLOB 'v[0-9]*[.][0-9]*[.][0-9]*'),
    flash_missing      INTEGER DEFAULT 0,
    cropped            INTEGER DEFAULT 0,
    cropped_date       TEXT CHECK (cropped_date GLOB '????-??-??T??:??:??'),
    rotation_degrees   INTEGER DEFAULT 0 CHECK (rotation_degrees BETWEEN 0 AND 360),
    rotated_date       TEXT CHECK (rotated_date GLOB '????-??-??T??:??:??'),
    last_changed       TEXT CHECK (rotated_date GLOB '????-??-??T??:??:??'),
    embedded_images    INTEGER DEFAULT 0,
    FOREIGN KEY (parent_image_id)
       REFERENCES images(image_id)
       ON DELETE SET NULL
       ON UPDATE NO ACTION,
    CHECK (
        -- We don't want processed images without the parent image ID, nor raw images with it
        (is_raw = 1 AND parent_image_id IS NULL)
        OR
        (is_raw = 0 AND parent_image_id IS NOT NULL)
    )
);

----------------------------
-- TABLE: paintings
----------------------------
CREATE TABLE IF NOT EXISTS paintings (
    painting_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT,
    description   TEXT,
    explicit_year INTEGER CHECK (explicit_year BETWEEN 1900 AND 2050),
    inferred_year INTEGER CHECK (inferred_year BETWEEN 1900 AND 2050),
    personal_favourite     INTEGER DEFAULT 0,
    last_changed       TEXT CHECK (last_changed GLOB '????-??-??T??:??:??')
);

----------------------------
-- TABLE: painting_images
----------------------------
CREATE TABLE IF NOT EXISTS painting_images (
    painting_id   INTEGER NOT NULL,
    image_id      INTEGER NOT NULL,
    PRIMARY KEY (painting_id, image_id),
    FOREIGN KEY (painting_id) REFERENCES paintings(painting_id) ON DELETE CASCADE,
    FOREIGN KEY (image_id)    REFERENCES images(image_id)        ON DELETE CASCADE
);

----------------------------
-- TABLE: ratings
----------------------------
CREATE TABLE IF NOT EXISTS ratings (
    rating_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    painting_id   INTEGER NOT NULL,
    image_id      INTEGER NOT NULL,
    score         INTEGER CHECK(score >= 1 AND score <= 5),
    rating_date   TEXT DEFAULT (datetime('now')),
    user         TEXT,
    FOREIGN KEY (painting_id) REFERENCES paintings(painting_id),
    FOREIGN KEY (image_id)    REFERENCES images(image_id)
);
