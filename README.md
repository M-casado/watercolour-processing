# Digital Archiving and Processing of Watercolour Paintings

This repository contains the code and workflow for digitising, processing, and cataloguing a collection of watercolour paintings created by **María Barbero Lozano**. The goal is to preserve these works in high-quality digital formats, organise metadata for each painting, and prepare selected pieces for inclusion in a professionally printed book.

## Objectives
1. Digitise and process watercolour paintings stored in `.NEF` (RAW) format.
2. Automate:
   - Cropping and rotating paintings.
   - Adjusting lighting and colour consistency.
   - Creating and updating a structured metadata database.
3. Provide a UI within Jupyter Notebooks for manual review and editing where needed.
4. Output high-resolution files suitable for:
   - Archival purposes.
   - Printing a book of selected works.

---

## Workflow

1. **Digitisation**:
   - Original paintings are photographed in RAW format (`.NEF`).
   - Images are stored in a structured folder system.

2. **Preprocessing**:
   - Convert `.NEF` files to `.PNG` or `.TIFF` for faster processing.
   - Apply automated cropping and rotation using edge detection (OpenCV).
   - Adjust lighting and colours consistently across images.

3. **Metadata Management**:
   - A Pandas DataFrame is used to track:
     - File information (original and processed).
     - Painting details (e.g., title, year, description).
     - Process metadata (e.g., rotation, manual edits).
   - If needed be, outputs can be saved as `.CSV` or to a database (e.g., SQLite).

4. **Manual Review**:
   - Jupyter Notebook with interactive widgets allows:
     - Quick visualisation of each painting.
     - Manual corrections (e.g., cropping, rotation, or metadata editing).

5. **Export**:
   - Save high-resolution processed images.
   - Generate selected works for inclusion in a book.

---

## How to Reproduce

### Requirements
Install the required Python packages:
````bash
pip install -r requirements.txt
````

### Folder Structure
Ensure the following folder structure exists:
````plaintext
/data/
├── raw/                # Original .NEF files
├── processed/          # Processed high-resolution images
/notebooks/             # Jupyter notebooks for workflow
/src/                   # Python scripts for automation
````

### Running the Workflow
1. Add `.NEF` files to `/data/raw/`.
2. Open and run the main notebook in `/notebooks/`.
3. Follow the steps in the notebook:
   - Preprocessing (automated cropping, rotation, adjustments).
   - Manual review of paintings.
4. Export results to `/data/processed/` and save metadata.

---

## License
- **Copyright for artworks**: María Barbero Lozano. All rights reserved.
- **Code license**: [MIT License](LICENSE.md).

---

## Contributing
This repository is a personal project and not currently open for contributions. For any inquiries, please contact the repository owner at mcasado [at] ebi.ac.uk.
