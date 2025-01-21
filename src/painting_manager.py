import os
import glob
import time
import pandas as pd
from datetime import datetime
from painting import Painting

class PaintingManager:
    """
    Manages a collection of Painting objects, including
    batch operations and metadata persistence.
    """

    def __init__(self, raw_dir, processed_dir, metadata_file="metadata.csv", backup_dir="metadata_backups"):
        """
        Args:
            raw_dir (str): Directory containing raw .NEF files.
            processed_dir (str): Directory for saving processed images.
            metadata_file (str): Path to the main CSV file for metadata.
            backup_dir (str): Directory where backup CSVs are stored.
        """
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.metadata_file = metadata_file
        self.backup_dir = backup_dir

        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        self.df = self._load_metadata()

    def _load_metadata(self):
        """
        Load metadata from the CSV or create a new DataFrame.

        Returns:
            pandas.DataFrame: Metadata DataFrame with 'id' as index.
        """
        if os.path.exists(self.metadata_file):
            df = pd.read_csv(self.metadata_file, index_col="id")
            print(f"Loaded metadata with {len(df)} records.")
            return df
        else:
            columns = [
                "id", "original_file", "order", "date_taken", "processed_file",
                "cropped", "cropped_date", "rotated", "rotated_date",
                "adjusted", "adjusted_date", "explicit_year", "inferred_year",
                "rating", "name", "description", "last_reviewed", "flash_missing"
            ]
            return pd.DataFrame(columns=columns).set_index("id")

    def save_metadata(self):
        """
        Save the metadata DataFrame to the main CSV.
        """
        self.df.to_csv(self.metadata_file, index=True)
        print(f"Metadata saved to {self.metadata_file}")

    def save_metadata_with_backup(self):
        """
        Saves the metadata CSV and also creates a backup with a timestamp.
        Maintains up to 10 rolling backups.
        """
        self.save_metadata()

        # Create a timestamped backup file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"metadata_{timestamp}.csv")
        self.df.to_csv(backup_path, index=True)
        print(f"Backup created at: {backup_path}")

        # Clean up old backups if exceeding 10
        backups = sorted(glob.glob(os.path.join(self.backup_dir, "metadata_*.csv")), reverse=True)
        if len(backups) > 10:
            for old_backup in backups[10:]:
                os.remove(old_backup)
                print(f"Removed old backup: {old_backup}")

    def process_painting(self, file_name):
        """
        Process a single painting by converting to PNG and updating metadata.

        Args:
            file_name (str): Name of the .NEF file in raw_dir.
        """
        order = int(file_name.split("DSC")[-1].split(".")[0])
        original_file = os.path.join(self.raw_dir, file_name)

        date_taken = Painting.extract_date_taken(original_file)
        painting = Painting(
            id=order,
            original_file=original_file,
            date_taken=date_taken,
            processed_dir=self.processed_dir,
        )

        # Convert raw -> PNG
        painting.convert_to_png()

        # Example: update 'flash_missing' if in a known ID range
        # (custom logic can be placed here)
        if 100 <= order <= 150:  # Example range
            painting.metadata["flash_missing"] = True

        # Insert or update the DataFrame
        self.df = painting.update_metadata(self.df)

    def process_all_paintings(self):
        """
        Process all .NEF files in the raw directory (convert, metadata).
        """
        files = [f for f in os.listdir(self.raw_dir) if f.lower().endswith(".nef")]
        for file_name in files:
            self.process_painting(file_name)
        self.save_metadata_with_backup()

    def bulk_adjust_brightness_contrast(self, ids, brightness_factor=1.0, contrast_factor=1.0):
        """
        Adjust brightness/contrast for a list of paintings identified by ID.

        Args:
            ids (list): List of painting IDs.
            brightness_factor (float): Brightness factor.
            contrast_factor (float): Contrast factor.
        """
        for painting_id in ids:
            row = self.df.loc[painting_id]
            p = Painting(
                id=painting_id,
                original_file=row["original_file"],
                date_taken=row["date_taken"],
                processed_dir=self.processed_dir,
                metadata={   # reconstruct any existing metadata from the row
                    "cropped": row["cropped"],
                    "cropped_date": row["cropped_date"],
                    "rotated": row["rotated"],
                    "rotated_date": row["rotated_date"],
                    "adjusted": row["adjusted"],
                    "adjusted_date": row["adjusted_date"],
                    "explicit_year": row["explicit_year"],
                    "inferred_year": row["inferred_year"],
                    "rating": row["rating"],
                    "name": row["name"],
                    "description": row["description"],
                    "last_reviewed": row["last_reviewed"],
                    "flash_missing": row["flash_missing"],
                }
            )
            p.processed_file = row["processed_file"]
            p.adjust_brightness_contrast(brightness_factor, contrast_factor)
            self.df = p.update_metadata(self.df)

        self.save_metadata_with_backup()

    def bulk_rotate(self, ids, degrees=90):
        """
        Rotate a list of paintings by a specified angle (commonly ±90 or 180).
        """
        for painting_id in ids:
            row = self.df.loc[painting_id]
            p = Painting(
                id=painting_id,
                original_file=row["original_file"],
                date_taken=row["date_taken"],
                processed_dir=self.processed_dir,
                metadata={   # same pattern as above
                    "cropped": row["cropped"],
                    "cropped_date": row["cropped_date"],
                    "rotated": row["rotated"],
                    "rotated_date": row["rotated_date"],
                    "adjusted": row["adjusted"],
                    "adjusted_date": row["adjusted_date"],
                    "explicit_year": row["explicit_year"],
                    "inferred_year": row["inferred_year"],
                    "rating": row["rating"],
                    "name": row["name"],
                    "description": row["description"],
                    "last_reviewed": row["last_reviewed"],
                    "flash_missing": row["flash_missing"],
                }
            )
            p.processed_file = row["processed_file"]
            p.rotate_image(degrees)
            self.df = p.update_metadata(self.df)

        self.save_metadata_with_backup()

    def auto_detect_crop(self, painting_id):
        """
        Stub for automatic cropping detection (edge detection, etc.).
        Real implementation would likely use OpenCV or advanced PIL methods.
        """
        # Example of a placeholder bounding box:
        # (left=10, upper=10, right=100, lower=100)
        auto_box = (10, 10, 100, 100)

        row = self.df.loc[painting_id]
        p = Painting(
            id=painting_id,
            original_file=row["original_file"],
            date_taken=row["date_taken"],
            processed_dir=self.processed_dir,
            metadata=row.to_dict()
        )
        p.processed_file = row["processed_file"]

        # Perform the crop
        p.crop_image(auto_box)
        self.df = p.update_metadata(self.df)
        self.save_metadata()
