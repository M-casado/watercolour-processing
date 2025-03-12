# Digital Archiving and Processing of Watercolour Paintings

This repository contains the code and workflow for digitising, processing, and cataloguing a collection of watercolour paintings created by **María Barbero Lozano**. The goal is to preserve these works in high-quality digital formats, organise metadata for each painting, and prepare selected pieces for inclusion in a professionally printed book.

## Objectives
1. Digitise and process watercolour paintings stored in `.NEF` (RAW) format.
2. Automate:
   - Cropping and rotating paintings.
   - Adjusting lighting and colour consistency.
   - Creating and updating a structured metadata database.
3. Provide a UI  for manual review and editing where needed.
4. Output high-resolution files suitable for:
   - Archival purposes.
   - Printing a book of selected works.

---

## How to Reproduce

### Requirements
Install the required Python packages:
````bash
pip install -r requirements.txt
````

````bash
python3 src/watercolour_processing/ingestion/ingest_raw_images.py data/raw
````

````bash
cd /mnt/c/GitHub/watercolour-processing
python3 -m watercolour_processing.app
````



## License
- **Copyright for artworks**: María Barbero Lozano. All rights reserved.
- **Code license**: [MIT License](LICENSE.md).

---

## Contributing
This repository is a personal project and not currently open for contributions. For any inquiries, please contact the repository owner at mcasado [at] ebi.ac.uk.
