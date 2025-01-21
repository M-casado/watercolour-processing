import os
import rawpy
import imageio
import pandas as pd
from datetime import datetime
import exifread
from PIL import Image, ImageEnhance, ExifTags

class Painting:
    """
    Represents an individual painting and provides methods for
    image processing and metadata updates.
    """

    def __init__(self, id, original_file, date_taken, processed_dir, metadata=None):
        """
        Initialize a Painting object.

        Args:
            id (int): Unique ID of the painting.
            original_file (str): Path to the original .NEF file.
            date_taken (str): Date the painting was taken (or created).
            processed_dir (str): Directory to save processed images.
            metadata (dict): Additional metadata for the painting.
        """
        self.id = id
        self.original_file = original_file
        self.date_taken = date_taken
        self.processed_dir = processed_dir
        self.metadata = metadata or {
            "cropped": False,
            "cropped_date": None,
            "rotated": "no",  # "yes", "no", or "not needed"
            "rotated_date": None,
            "adjusted": False,
            "adjusted_date": None,
            "explicit_year": None,
            "inferred_year": None,
            "rating": None,
            "name": None,
            "description": None,
            "last_reviewed": None,
            "flash_missing": False,  # Example extra column
        }
        self.processed_file = None

    @staticmethod
    def extract_date_taken(file_path):
        """
        Extracts date from NEF file using 'exifread'.
        Returns a string in YYYY-MM-DD format, or None if unavailable.
        """
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag='EXIF DateTimeOriginal')
            # Common tag names: 'EXIF DateTimeOriginal' or 'EXIF DateTimeDigitized'
            date_tag = tags.get("EXIF DateTimeOriginal")
            if date_tag:
                # Typically "YYYY:MM:DD HH:MM:SS"
                dt_str = str(date_tag)
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                return dt.date().isoformat()
        except Exception as e:
            print(f"Error extracting date from {file_path} using exifread: {e}")
        return None
    
    def convert_to_png(self):
        """
        Converts the .NEF file to PNG format and updates the processed_file path.
        """
        if not os.path.exists(self.processed_dir):
            os.makedirs(self.processed_dir)

        base_name = os.path.basename(self.original_file)  # e.g. "_DSC0014.NEF"
        root, ext = os.path.splitext(base_name)           # ("_DSC0014", ".NEF")
        output_file = os.path.join(self.processed_dir, f"{root}.png")

        print(f"Converting {self.original_file} to {output_file}")
        try:
            with rawpy.imread(self.original_file) as raw:
                rgb_image = raw.postprocess()
                imageio.imsave(output_file, rgb_image)
            self.processed_file = output_file
        except Exception as e:
            print(f"Error converting {self.original_file} to PNG: {e}")
            
    def adjust_brightness_contrast(self, brightness_factor=1.0, contrast_factor=1.0):
        """
        Adjust the brightness and/or contrast of the processed image.

        Args:
            brightness_factor (float): Factor by which to adjust brightness (1.0 = no change).
            contrast_factor (float): Factor by which to adjust contrast (1.0 = no change).
        """
        if not self.processed_file or not os.path.exists(self.processed_file):
            print(f"[ID {self.id}] No processed file to adjust.")
            return

        try:
            img = Image.open(self.processed_file)
            if brightness_factor != 1.0:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(brightness_factor)

            if contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast_factor)

            img.save(self.processed_file)
            self.metadata["adjusted"] = True
            self.metadata["adjusted_date"] = datetime.now().isoformat()
        except Exception as e:
            print(f"[ID {self.id}] Error adjusting image: {e}")

    def rotate_image(self, degrees=90):
        """
        Rotate the processed image by the specified degrees (e.g., 90, -90, 180).
        """
        if not self.processed_file or not os.path.exists(self.processed_file):
            print(f"[ID {self.id}] No processed file to rotate.")
            return

        try:
            img = Image.open(self.processed_file)
            img = img.rotate(degrees, expand=True)
            img.save(self.processed_file)
            self.metadata["rotated"] = "yes"
            self.metadata["rotated_date"] = datetime.now().isoformat()
        except Exception as e:
            print(f"[ID {self.id}] Error rotating image: {e}")

    def crop_image(self, crop_box):
        """
        Crop the processed image according to a (left, upper, right, lower) tuple.

        Args:
            crop_box (tuple): (left, upper, right, lower) pixel coordinates.
        """
        if not self.processed_file or not os.path.exists(self.processed_file):
            print(f"[ID {self.id}] No processed file to crop.")
            return

        try:
            img = Image.open(self.processed_file)
            cropped_img = img.crop(crop_box)
            cropped_img.save(self.processed_file)
            self.metadata["cropped"] = True
            self.metadata["cropped_date"] = datetime.now().isoformat()
        except Exception as e:
            print(f"[ID {self.id}] Error cropping image: {e}")

    def update_metadata(self, df):
        """
        Updates this painting's metadata in the DataFrame.

        Args:
            df (pandas.DataFrame): The DataFrame storing metadata.

        Returns:
            pandas.DataFrame: Updated DataFrame.
        """
        record = {
            "id": self.id,
            "original_file": self.original_file,
            "order": int(self.original_file.split("DSC")[-1].split(".")[0]),
            "date_taken": self.date_taken,
            "processed_file": self.processed_file,
            **self.metadata,
        }

        if self.id in df.index:
            df.loc[self.id] = record
        else:
            df = df.append(record, ignore_index=True)

        return df
