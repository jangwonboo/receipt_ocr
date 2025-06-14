#!/usr/bin/env python3
"""
Gemini OCR Module
Google Gemini 기반 OCR 모듈

This module handles document OCR and information extraction using Google Gemini's LLM capabilities.
이 모듈은 Google Gemini의 LLM 기능을 사용하여 문서 OCR 및 정보 추출을 처리합니다.

It processes various document formats (PDF, JPG, PNG, etc.) and extracts key receipt information 
including date, place, amount, and currency.
다양한 문서 형식(PDF, JPG, PNG 등)을 처리하고 날짜, 장소, 금액, 통화 등 영수증 주요 정보를 추출합니다.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import img2pdf
from pathlib import Path
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
import img2pdf

# Google Gemini API
from google import genai
from google.genai import types
import pathlib as pl
import httpx


prompt = """
        Extract the following information from this receipt:
        
        1. Date: Look for transaction date with keywords like:
           - In Korean: '거래일시', '결제시간', '승인시간', '판매일', '판매시간', '일시', '승인일자', '거래일자'
           - In English: 'Date', 'Transaction Date', 'Purchase Date', 'Date of Sale'
           - Common formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, YYYY.MM.DD
           - Example: 2023-05-16, 05/16/2023, 16.05.2023
           - Date must be returned in YYYYMMDD format (e.g., 20230516)
        
        2. Place: Look for the merchant or store name with keywords like:
           - In Korean: '가맹점명', '상호', '결제가맹점명', '상점명', '판매자정보', '판매자', '판매자상호'
           - In English: 'Merchant', 'Store', 'Business name', 'Seller'
        
        3. Amount: Look for the total payment amount with keywords like:
           - In Korean: '합계', '결제금액', '총결제금액', '승인금액', '받은금액', '합계금액', '결제', '총액'
           - In English: 'Total', 'Amount', 'Total Amount', 'Payment Amount'
           - Be sure NOT to use tax-related amounts like '과세', '면세', '부가세', 'VAT', 'Tax'
           - Usually the largest amount in the receipt
        
        4. Currency: Detect if the amount is in foreign currency (USD, EUR, etc.)
           - Default to 'KRW' for Korean receipts if not specified

        
        Important:
        - If any field is not found, set it to null
        - For date, ensure it is in YYMMDD format (e.g., 230516 for May 16, 2023)
        - For amount, return only the number without any currency symbols or formatting
        
        Return only the JSON object, nothing else.
        
        Respond with ONLY a JSON object in the following format: 
        {"date": "YYYYMMDD", "place": "store name", "amount": number, "currency": "currency code"}

        Example response:
        {
        "date": "230516",
        "place": "Starbucks",
        "amount": 6500,
        "currency": "KRW"
        }"""
    

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s-\t%(asctime)s\t-%(filename)s:%(lineno)d-%(funcName)s(): \t%(message)s'
)
logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']

def convert_image_to_pdf(image_path: Path) -> Optional[Path]:
    """Convert image to PDF for processing"""
    try:
        image = Image.open(image_path)
        pdf_bytes = img2pdf.convert(image.filename)
        temp_pdf_path = image_path.with_suffix('.pdf')
        with open(temp_pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        return temp_pdf_path
    except Exception as e:
        logger.error(f"Failed to convert image to PDF: {e}")
        return None

def setup_directory(input_dir: Path, output_dir: Optional[Path] = None) -> Tuple[Path, Path, Path]:
    """Setup input, output, and temp directories"""
    input_dir = Path(input_dir)
    if output_dir is None:
        output_dir = input_dir / "output"
    temp_dir = input_dir / "temp"
    output_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)
    return input_dir, output_dir, temp_dir

def generate_filename_from_info(extracted_info: Dict[str, Any], original_path: Path) -> str:
    """Generate a filename based on extracted receipt information"""
    date = extracted_info.get('date', 'NA')
    place = extracted_info.get('place', 'NA')
    amount = extracted_info.get('amount', 'NA')
    currency = extracted_info.get('currency', 'NA')
    
    # Clean up place name for filename
    if place and place.lower() != 'na':
        place = re.sub(r'[^\w\s]', '', place)
        place = place.replace(' ', '_')[:30]
    
    parts = []
    
    # Add date if available (format: YYMMDD for filename)
    if date and date.lower() != 'na':
        if isinstance(date, str) and len(date) >= 8:
            if date[:2] in ["19", "20"] and date[:8].isdigit():
                parts.append(date[2:8])  # YYMMDD format
            else:
                parts.append(date[:8])
    else:
        parts.append('NA')  # Add NA if date is missing
    
    # Add place if available
    if place and place.lower() != 'na':
        place = re.sub(r'[^\w\s\u3131-\u3163\uac00-\ud7a3]', '', place)
        parts.append(place)
    
    # Add amount and currency if available
    if amount is not None and amount != 'NA' and currency and currency != 'NA':
        parts.append(f"{amount}_{currency}")
    elif amount is not None and amount != 'NA':
        parts.append(str(amount))
    
    # If we have meaningful parts, create a filename
    if any(part != 'NA' for part in parts):
        return "_".join(parts) + ".pdf"
    else:
        return original_path.stem + "_receipt.pdf"

def extract_info_with_gemini(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Extract information from a receipt using Google Gemini
    
    Args:
        file_path: Path to the PDF file to process
        
    Returns:
        Dictionary with extracted receipt information
    """
    client = genai.Client()
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(
                    data=file_path.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        logger.info(f"Gemini response: {response_text}")
        
        # Extract JSON from markdown code block if present
        if '```json' in response_text:
            json_str = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            json_str = response_text.split('```')[1].strip()
        else:
            json_str = response_text
            
        result = json.loads(json_str)
        return result
        
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None

def process_file(file_path: Union[str, Path], temp_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Process a file and extract information using Gemini, then rename the file in place
    
    Args:
        file_path: Path to the file to process
        temp_dir: Directory to store temporary files
        
    Returns:
        Dictionary with extracted information or None if processing failed
    """
    temp_pdf_path = None
    final_pdf_path = None
    info_path = None
    missing_fields = []
    
    try:
        file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
        
        # Validate file exists and has supported extension
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file extension: {file_path.suffix}")
            return None
        
        # Convert image to PDF if needed
        is_image = file_path.suffix.lower() in IMAGE_EXTENSIONS
        if is_image:
            logger.info(f"Converting image to PDF: {file_path}")
            temp_pdf_path = convert_image_to_pdf(file_path)
            if temp_pdf_path is None:
                logger.error(f"Failed to convert image to PDF: {file_path}")
                return None
            process_path = temp_pdf_path
        else:
            process_path = file_path
        
        # Extract information using Gemini
        extracted_info = extract_info_with_gemini(process_path)
        
        # Fill missing fields with 'NA' for date, place, amount, currency
        for field in ["date", "place", "amount", "currency"]:
            value = extracted_info.get(field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                extracted_info[field] = "NA"
        
        if not extracted_info:
            logger.error(f"Failed to extract information from OCR text for {file_path}")
            return None
        
        # Generate new filename based on extracted info
        new_filename = generate_filename_from_info(extracted_info, file_path)
        logger.info(f"Generated filename: {new_filename}")
        
        # Save OCR text to temp directory
        text_path = temp_dir / f"{file_path.stem}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(extracted_info, ensure_ascii=False, indent=2))
        logger.info(f"OCR text saved to: {text_path}")
        
        # Save extracted info to temp directory
        info_path = temp_dir / f"{file_path.stem}.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_info, f, ensure_ascii=False, indent=2)
        logger.info(f"Extracted information saved to: {info_path}")
        
        # Determine source PDF (original or converted from image)
        source_pdf = temp_pdf_path if temp_pdf_path else file_path
        
        # Rename the file in place
        try:
            target_path = file_path.parent / new_filename
            
            # If we converted an image to PDF, remove the original image
            if is_image and temp_pdf_path:
                os.remove(file_path)  # Remove original image
                file_path = temp_pdf_path  # Update file_path to point to the PDF
            
            # Rename the file
            os.rename(file_path, target_path)
            logger.info(f"File renamed to: {target_path}")
            
            # Add final path to the extracted info
            extracted_info['final_path'] = str(target_path)
            
        except Exception as e:
            logger.error(f"Failed to rename file {file_path} to {target_path}: {e}")
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)  # Clean up temp PDF if rename failed
            raise
        
        # Track missing fields
        for field in ["date", "place", "amount", "currency"]:
            if not extracted_info.get(field):
                missing_fields.append(field)
        extracted_info['missing_fields'] = missing_fields
        
        return extracted_info
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        logger.error(traceback.format_exc())
        return None

def process_directory(input_dir: Union[str, Path]) -> None:
    """
    Process all files in a directory, renaming them in place
    
    Args:
        input_dir: Path to the input directory containing files to process
    """
    try:
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            logger.error(f"Input directory not found: {input_dir}")
            return
            
        # Create temp directory in the input directory
        temp_path = input_path / "temp_ocr_processing"
        temp_path.mkdir(exist_ok=True, parents=True)
        
        processed_files = []
        failed_files = []
        missing_info_files = []  # (file_path, missing_fields)
        missing_field_stats = {"date": 0, "place": 0, "amount": 0, "currency": 0}
        
        # Process each file in the input directory
        for file_path in sorted(input_path.glob('*')):  # Sort for consistent processing order
            # Skip the temp directory itself and hidden files
            if file_path == temp_path or file_path.name.startswith('.'):
                continue
                
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                logger.info(f"Processing file: {file_path}")
                
                # Process file with temp directory only
                extracted_info = process_file(file_path, temp_path)
                
                if extracted_info:
                    processed_files.append((file_path, extracted_info.get('final_path', '')))
                    
                    # Track missing fields
                    missing_fields = extracted_info.get('missing_fields', [])
                    if missing_fields:
                        missing_info_files.append((file_path, missing_fields))
                        for field in missing_fields:
                            if field in missing_field_stats:
                                missing_field_stats[field] += 1
                else:
                    failed_files.append(file_path)
        
        # Clean up temp directory if empty
        try:
            if temp_path.exists():
                if not any(temp_path.iterdir()):
                    temp_path.rmdir()
                    logger.info(f"Removed empty temp directory: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {temp_path}: {e}")
        
        # Log processing summary
        logger.info(f"\n=== Processing Summary ===")
        logger.info(f"Processed files: {len(processed_files)}")
        if failed_files:
            logger.warning(f"Failed files: {len(failed_files)}")
        
        if missing_info_files:
            logger.warning("\nSome files are missing key information:")
            for file_path, fields in missing_info_files:
                logger.warning(f"- {file_path}: missing {fields}")
            
            logger.warning("\nMissing fields statistics:")
            for field, count in missing_field_stats.items():
                if count > 0:
                    logger.warning(f"- {field}: {count} files")
        else:
            logger.info("\nAll processed files have all key information extracted.")
            
    except Exception as e:
        logger.error(f"Error processing directory {input_dir}: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Rename receipt files in place using information extracted by Google Gemini API")
    parser.add_argument("input", help="Path to input file or directory")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    try:
        if input_path.is_file():
            # For single file processing, create temp directory in the same directory
            temp_dir = input_path.parent / "temp_ocr_processing"
            temp_dir.mkdir(exist_ok=True, parents=True)
            
            if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                logger.info(f"Processing file: {input_path}")
                result = process_file(input_path, temp_dir)
                if result:
                    logger.info(f"Extracted information: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.info(f"File renamed to: {result.get('final_path', 'Unknown')}")
                else:
                    logger.error(f"Failed to extract information from {input_path}")
                
                # Clean up temp directory if empty
                try:
                    if temp_dir.exists() and not any(temp_dir.iterdir()):
                        temp_dir.rmdir()
                        logger.info(f"Removed empty temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
            else:
                logger.error(f"Unsupported file extension: {input_path.suffix}")
        elif input_path.is_dir():
            logger.info(f"Processing directory: {input_path}")
            process_directory(input_path)
        else:
            logger.error(f"Input path does not exist: {input_path}")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())