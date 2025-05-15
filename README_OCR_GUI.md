# OCR Document Processing GUI

A cross-platform PyQt6 application for Windows and macOS that processes images/PDFs with OCR, produces JSON files with extracted information, and renames files based on the JSON data.

## Features

- User-friendly graphical interface for OCR processing
- Support for multiple file formats (PDF, JPG, PNG, TIFF)
- OCR processing modes: Receipt and General Text
- Process single or multiple pages in PDF files
- Automatic file renaming based on extracted information
- Real-time progress tracking and logging

## Screenshots

![OCR GUI Application](screenshots/ocr_gui_screenshot.png)

## Requirements

- Python 3.6+
- PyQt6
- pdf2image (with Poppler dependency)
- Pillow
- requests
- Other dependencies listed in requirements.txt

## Installation

1. Clone or download this repository

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Install Poppler (required for PDF processing):

   - **Windows**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - **macOS**: Use Homebrew: `brew install poppler`

## Usage

1. Run the application:

```bash
python ocr_gui.py
```

2. Select an input directory containing images or PDFs to process

3. (Optional) Select a different output directory for JSON files

4. Choose OCR mode:
   - **Receipt**: For structured data extraction from receipts
   - **Text (General)**: For general text extraction from documents

5. Choose whether to process all pages in PDF files or just the first page

6. Choose whether to rename files after processing (based on extracted data)

7. Click "Start Processing" to begin OCR processing

## File Renaming Format

When renaming is enabled, files will be renamed according to the following format:

```
{payment_date}_{store_name}_{total_price}.{original_extension}
```

Where:
- `payment_date`: Date in MMDD format (e.g., 0425 for April 25)
- `store_name`: Store name with special characters and spaces removed
- `total_price`: Total price with only digits kept

## Notes

- This application requires an internet connection to communicate with the Naver Cloud OCR API
- API credentials are included in the main OCR script
- For processing large batches of files, consider increasing timeout values in the OCR script

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Naver Cloud OCR API for providing OCR services
- PyQt6 for the GUI framework