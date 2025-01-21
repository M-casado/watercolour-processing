import os
from PIL import Image
import ipywidgets as widgets
from IPython.display import display
import numpy as np

def interactive_crop_and_rotate(painting, manager):
    """
    A basic example of an interactive tool to crop and rotate an image in a Jupyter notebook.
    This modifies the image file on disk and updates the manager's metadata.

    Args:
        painting (Painting): Painting object for the image to be edited.
        manager (PaintingManager): Manager with the loaded DataFrame.
    """
    if not painting.processed_file or not os.path.exists(painting.processed_file):
        print(f"No processed file found for ID {painting.id}")
        return

    # Load the current image
    img = Image.open(painting.processed_file)
    width, height = img.size

    # Crop sliders
    left_slider = widgets.IntSlider(value=0, min=0, max=width-1, description='Left')
    top_slider = widgets.IntSlider(value=0, min=0, max=height-1, description='Top')
    right_slider = widgets.IntSlider(value=width, min=1, max=width, description='Right')
    bottom_slider = widgets.IntSlider(value=height, min=1, max=height, description='Bottom')

    # Rotation dropdown
    rotate_options = [0, 90, -90, 180]
    rotate_dropdown = widgets.Dropdown(
        options=rotate_options,
        value=0,
        description='Rotation (°)'
    )

    # Preview button
    preview_button = widgets.Button(description="Preview")
    save_button = widgets.Button(description="Save & Next")

    output = widgets.Output()

    def on_preview_click(b):
        with output:
            output.clear_output()
            # Generate cropped/rotated image preview
            temp_img = img.copy()
            crop_box = (left_slider.value, top_slider.value, 
                        right_slider.value, bottom_slider.value)
            try:
                temp_img = temp_img.crop(crop_box)
                temp_img = temp_img.rotate(rotate_dropdown.value, expand=True)
                display(temp_img)
            except Exception as e:
                print(f"Error in preview: {e}")

    def on_save_click(b):
        # Perform actual crop & rotate, then update metadata
        crop_box = (left_slider.value, top_slider.value, 
                    right_slider.value, bottom_slider.value)
        painting.crop_image(crop_box)
        if rotate_dropdown.value != 0:
            painting.rotate_image(rotate_dropdown.value)
        # Update last_reviewed
        painting.metadata["last_reviewed"] = str(manager._get_timestamp())
        # Update manager’s DataFrame
        manager.df = painting.update_metadata(manager.df)
        manager.save_metadata_with_backup()

        with output:
            output.clear_output()
            print(f"Painting ID {painting.id} updated and metadata saved.")

    preview_button.on_click(on_preview_click)
    save_button.on_click(on_save_click)

    widget_box = widgets.VBox([
        widgets.HBox([left_slider, top_slider, right_slider, bottom_slider]),
        rotate_dropdown,
        widgets.HBox([preview_button, save_button]),
        output
    ])

    display(widget_box)
