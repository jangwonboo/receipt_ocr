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
import traceback
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
from dotenv import load_dotenv

# Load environment variables from .env file
# .env 파일에서 환경 변수 로드
# override=True: .env 파일의 값이 환경 변수를 덮어씁니다 (환경 변수에 이미 값이 있어도 .env 우선)
# override=True: .env 파일의 값이 환경 변수를 덮어씁니다
load_dotenv(override=True)

# Get API key from environment variable (.env file)
# 환경 변수에서 API 키 가져오기 (.env 파일)
# strip()을 사용하여 공백 제거 (.env 파일에 공백이 있을 수 있음)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# Helper function to mask API key for logging
# 로깅을 위한 API 키 마스킹 헬퍼 함수
def mask_api_key(api_key: str) -> str:
    """
    Mask API key for safe logging (show first 4 and last 4 characters)
    안전한 로깅을 위해 API 키 마스킹 (처음 4자와 마지막 4자만 표시)
    """
    if not api_key or len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"


prompt = """
        Extract the following information from this receipt:
        
        1. Date: Look for transaction date with keywords like:
           - In Korean: '거래일시', '결제시간', '승인시간', '판매일', '판매시간', '일시', '승인일자', '거래일자'
           - In English: 'Date', 'Transaction Date', 'Purchase Date', 'Date of Sale'
           - Common formats: YY-MM-DD, YYYY-MM-DD, DD/MM/YYYY, DD/MM/YY, MM/DD/YY, MM/DD/YYYY, YY.MM.DDYYYY.MM.DD
           - Example: 2023-05-16, 05/16/2023, 16.05.2023
           - Date must be returned in YYYYMMDD format (e.g., 20230516 for May 16, 2023)
           - Note: The system will automatically convert 4-digit years to 2-digit years (e.g., 2025 -> 25)
        
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
        - All the characters in the response must be in Korean or English including numbers
        - If any field is not found, set it to null
        - For date, return in YYYYMMDD format (e.g., 20230516 for May 16, 2023)
          The system will automatically extract the last 2 digits of the year (e.g., 2025 -> 25)
        - For amount, return only the number without any currency symbols or formatting
        
        Return only the JSON object, nothing else.
        
        Respond with ONLY a JSON object in the following format: 
        {"date": "YYYYMMDD", "place": "store name", "amount": number, "currency": "currency code"}

        Example response:
        {
        "date": "20230516",
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

# Log API key status after logger is initialized
# 로거 초기화 후 API 키 상태 로깅
if GOOGLE_API_KEY:
    logger.info(f"GOOGLE_API_KEY loaded from .env: {mask_api_key(GOOGLE_API_KEY)}")
    logger.info(f"Full GOOGLE_API_KEY from .env: {GOOGLE_API_KEY}")
    
    # Check if there's a mismatch between .env and environment variable
    # .env와 환경 변수 간 불일치 확인
    # Note: After load_dotenv(override=True), os.environ should match .env
    # 참고: load_dotenv(override=True) 후에는 os.environ이 .env와 일치해야 함
    env_var_key = os.environ.get("GOOGLE_API_KEY")
    if env_var_key and env_var_key != GOOGLE_API_KEY:
        logger.warning(f"⚠️ Environment variable GOOGLE_API_KEY differs from .env file!")
        logger.warning(f"Environment var: {mask_api_key(env_var_key)}")
        logger.warning(f"Using .env value: {mask_api_key(GOOGLE_API_KEY)}")
        logger.info(f"Full .env GOOGLE_API_KEY: {GOOGLE_API_KEY}")
else:
    logger.warning("GOOGLE_API_KEY not found in .env file")


# Supported file extensions
SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']

def get_genai_client():
    """
    Get genai.Client with API key authentication
    API 키 인증으로 genai.Client 가져오기
    
    Returns:
        genai.Client instance
    """
    # Use API key authentication from .env file
    # .env 파일에서 API 키 인증 사용
    if GOOGLE_API_KEY:
        logger.info(f"Using GOOGLE_API_KEY from .env file: {mask_api_key(GOOGLE_API_KEY)}")
        logger.info(f"Full GOOGLE_API_KEY: {GOOGLE_API_KEY}")
        return genai.Client(api_key=GOOGLE_API_KEY)
    else:
        # Try default (GOOGLE_API_KEY env var)
        # 기본값 시도 (GOOGLE_API_KEY 환경 변수)
        logger.info("Using default authentication (GOOGLE_API_KEY env var)")
        return genai.Client()

def check_authentication() -> bool:
    """
    Check if authentication is properly configured
    인증이 제대로 설정되어 있는지 확인
    
    Returns:
        True if authentication is configured, False otherwise
    """
    # Check API key
    # API 키 확인
    if not GOOGLE_API_KEY:
        logger.error("API key not found. Please set GOOGLE_API_KEY in .env file.")
        logger.error("API 키를 찾을 수 없습니다. .env 파일에 GOOGLE_API_KEY를 설정하세요.")
        return False
    
    try:
        # Try to create a client with the API key
        client = genai.Client(api_key=GOOGLE_API_KEY)
        # If no exception is raised, API key is likely set
        # Note: This doesn't verify if the key is valid, just if it's configured
        logger.info(f"GOOGLE_API_KEY found and configured: {mask_api_key(GOOGLE_API_KEY)}")
        logger.info(f"Full GOOGLE_API_KEY: {GOOGLE_API_KEY}")
        return True
    except Exception as e:
        logger.error(f"API key check failed: {e}")
        logger.error("Please check your GOOGLE_API_KEY in .env file.")
        logger.error(".env 파일의 GOOGLE_API_KEY를 확인하세요.")
        return False

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
            # If date is in YYYYMMDD format (4-digit year), extract YYMMDD (last 6 digits)
            # 2025로 인식되어도 뒤의 두 자리(25)만 사용
            if date[:8].isdigit():
                # Check if it starts with 4-digit year (1900-2099)
                year_prefix = date[:4]
                if year_prefix.isdigit() and 1900 <= int(year_prefix) <= 2099:
                    # Use last 6 digits: YYMMDD format
                    parts.append(date[2:8])  # YYMMDD format (e.g., 20251209 -> 251209)
                else:
                    # If not 4-digit year format, use first 8 characters
                    parts.append(date[:8])
            else:
                parts.append(date[:8])
        elif isinstance(date, str) and len(date) >= 6:
            # If date is already in YYMMDD format (6 digits), use as is
            parts.append(date[:6])
        else:
            parts.append('NA')
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
    # Get client with appropriate authentication
    # 적절한 인증으로 클라이언트 가져오기
    logger.info(f"Calling Gemini API with GOOGLE_API_KEY: {mask_api_key(GOOGLE_API_KEY) if GOOGLE_API_KEY else 'Not set'}")
    logger.info(f"Full GOOGLE_API_KEY used for API call: {GOOGLE_API_KEY}")
    client = get_genai_client()
    
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
        error_str = str(e)
        logger.error(f"Gemini API call failed: {e}")
        
        # Check for specific API errors and provide helpful messages
        if "403" in error_str or "PERMISSION_DENIED" in error_str:
            if "suspended" in error_str.lower():
                logger.error("API Key has been SUSPENDED. Please check your Google Cloud Console and create a new API key.")
                logger.error("API 키가 정지되었습니다. Google Cloud Console에서 새 API 키를 생성하세요.")
            else:
                logger.error("API Key permission denied. Please check your API key settings.")
                logger.error("API 키 권한이 거부되었습니다. API 키 설정을 확인하세요.")
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            logger.error("API Key is invalid or missing. Please set GOOGLE_API_KEY in .env file.")
            logger.error("API 키가 유효하지 않거나 없습니다. .env 파일에 GOOGLE_API_KEY를 설정하세요.")
        elif "429" in error_str or "rate limit" in error_str.lower():
            logger.error("API rate limit exceeded. Please wait and try again later.")
            logger.error("API 호출 한도를 초과했습니다. 잠시 후 다시 시도하세요.")
        
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
        
        # Check if extraction failed
        if extracted_info is None:
            error_msg = f"Failed to extract information from {file_path}"
            logger.error(error_msg)
            # Return error information for GUI to display
            return {
                "error": error_msg,
                "file_path": str(file_path),
                "suggestion": "API 키가 정지되었거나 유효하지 않을 수 있습니다. Google Cloud Console에서 API 키 상태를 확인하세요."
            }
            
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
        logger.error(traceback.format_exc())