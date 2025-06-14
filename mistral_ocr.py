#!/usr/bin/env python3
"""
Mistral OCR Module
Mistral OCR 모듈

This module handles document OCR and information extraction using Mistral AI's OCR and LLM capabilities.
이 모듈은 Mistral AI의 OCR 및 LLM 기능을 사용하여 문서 OCR 및 정보 추출을 처리합니다.

It processes various document formats (PDF, JPG, PNG, etc.) and extracts key receipt information 
including date, place, amount, and currency.
다양한 문서 형식(PDF, JPG, PNG 등)을 처리하고 날짜, 장소, 금액, 통화 등 영수증 주요 정보를 추출합니다.
"""

import os
import sys
import json
import requests
import base64
import time
import shutil
import traceback
import tempfile
import img2pdf
from pathlib import Path
import logging
from dotenv import load_dotenv
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from mistralai import Mistral
import img2pdf

# Load environment variables from .env file
# .env 파일에서 환경 변수 로드
load_dotenv()

# Configure logging
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s-\t%(asctime)s\t-%(filename)s:%(lineno)d-%(funcName)s(): \t%(message)s'
)
logger = logging.getLogger(__name__)

# Disable requests logging
# requests 로깅 비활성화
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Mistral API Configuration
# Mistral API 설정
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_LLM_MODEL = os.getenv("MISTRAL_LLM_MODEL", "mistral-small-latest")
MD_OUTPUT = os.getenv("MD_OUTPUT", "True").lower() == "true"

# Exchange rate API configurations
# 환율 API 설정
EXCHANGE_RATE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

# Supported file extensions
# 지원되는 파일 확장자
SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']

# Max retry attempts
# 최대 재시도 횟수
MAX_RETRIES = 3

def generate_filename_from_info(extracted_info: Dict[str, Any], original_path: Path) -> str:
    """
    Generate a filename based on extracted receipt information
    추출된 영수증 정보를 기반으로 파일 이름 생성
    
    Args:
        extracted_info: Dictionary containing extracted receipt information
        original_path: Original file path for fallback
        
    Returns:
        Generated filename string
    """
    try:
        # Extract relevant fields with fallbacks
        date = extracted_info.get('date', '')
        place = extracted_info.get('place', '')
        amount = extracted_info.get('amount', '')
        currency = extracted_info.get('currency', '')
        
        # Clean up place name for filename
        if place:
            # Remove special characters and limit length
            place = re.sub(r'[^\w\s]', '', place)
            place = place.replace(' ', '_')[:30]
        
        # Format parts of the filename
        parts = []
        
        # Add date if available (format: YYMMDD for filename)
        if date:
            if isinstance(date, str) and len(date) >= 8:
                # If date starts with 19 or 20, use only last 6 digits (YYMMDD)
                if date[:2] in ["19", "20"] and date[:8].isdigit():
                    parts.append(date[2:8])
                else:
                    parts.append(date[:8])
        
        # Add place if available
        if place:
            parts.append(place)
        
        # Add amount and currency if available
        if amount is not None and currency:
            parts.append(f"{amount}_{currency}")
        elif amount is not None:
            parts.append(str(amount))
        
        # If we have meaningful parts, create a filename
        if parts:
            return "_".join(parts) + ".pdf"
        else:
            # Fallback to original filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{original_path.stem}_{timestamp}.pdf"
    except Exception as e:
        logger.error(f"Error generating filename from info: {e}")
        # Fallback to original filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{original_path.stem}_{timestamp}.pdf"

def convert_image_to_pdf(image_path: Union[str, Path]) -> Optional[Path]:
    """
    Convert an image file to PDF format for Mistral OCR processing
    이미지 파일을 Mistral OCR 처리를 위해 PDF 형식으로 변환합니다
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Path to the temporary PDF file or None if conversion failed
    """
    try:
        image_path = Path(image_path) if not isinstance(image_path, Path) else image_path
        
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return None
            
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            logger.error(f"Not an image file: {image_path}")
            return None
            
        # Create a temporary file for the PDF
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf_path = Path(temp_pdf.name)
        
        # Convert image to PDF using img2pdf
        with open(temp_pdf_path, "wb") as f:
            f.write(img2pdf.convert(str(image_path)))
            
        logger.info(f"Converted {image_path} to PDF: {temp_pdf_path}")
        return temp_pdf_path
        
    except Exception as e:
        logger.error(f"Error converting image to PDF: {e}")
        return None

def setup_directory(input_dir, output_dir=None):
    """
    Ensure input directory exists and create output directory if provided.
    Also creates a temp directory under the input directory for intermediate files.
    입력 디렉토리가 존재하는지 확인하고 출력 디렉토리가 제공된 경우 생성합니다.
    또한 중간 파일을 위한 입력 디렉토리 아래에 temp 디렉토리를 생성합니다.
    
    Args:
        input_dir: Path to the input directory
                  입력 디렉토리 경로
        output_dir: Optional path for output directory
                   선택적 출력 디렉토리 경로
    
    Returns:
        Tuple of Path objects for input, output, and temp directories
        입력, 출력 및 임시 디렉토리에 대한 Path 객체 튜플
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    
    # Create temp directory under input directory
    temp_path = input_path / "temp"
    temp_path.mkdir(exist_ok=True)
    logger.info(f"Created temp directory: {temp_path}")
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        return input_path, output_path, temp_path
    
    return input_path, input_path, temp_path

def encode_file(file_path):
    """
    Encode file to base64
    파일을 base64로 인코딩
    
    Args:
        file_path: Path to the file to encode
                  인코딩할 파일 경로
    
    Returns:
        Base64 encoded string of the file or None if error occurs
        파일의 Base64 인코딩 문자열 또는 오류 발생 시 None
    """
    try:
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding file {file_path}: {e}")
        return None

def process_file(file_path: Union[str, Path], temp_dir: Path, output_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Process a file and extract information using Mistral
    파일을 처리하고 Mistral을 사용하여 정보 추출
    
    Args:
        file_path: Path to the file to process
                  처리할 파일 경로
        temp_dir: Directory to store intermediate files
                 중간 파일을 저장할 디렉토리
        output_dir: Directory to store final output files
                   최종 출력 파일을 저장할 디렉토리
    
    Returns:
        Dictionary with extracted receipt information and missing fields info, or None if error occurs
        추출된 영수증 정보와 누락된 필드 정보를 포함한 딕셔너리 또는 오류 발생 시 None
    """
    temp_pdf_path = None
    final_pdf_path = None
    info_path = None
    missing_fields = []
    try:
        file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file extension: {file_path.suffix}")
            return None
        
        # If the file is an image, convert it to PDF first
        is_image = file_path.suffix.lower() in IMAGE_EXTENSIONS
        if is_image:
            logger.info(f"Converting image to PDF: {file_path}")
            temp_pdf_path = convert_image_to_pdf(file_path)
            if temp_pdf_path is None:
                logger.error(f"Failed to convert image to PDF: {file_path}")
                return None
            # Use the temporary PDF path for processing
            process_path = temp_pdf_path
        else:
            # Use the original file path for PDFs
            process_path = file_path
            
        # Extract information using Mistral directly from the file
        extracted_info = extract_info_with_mistral(process_path)

        # Fill missing fields with 'NA' for date, place, amount, currency
        for field in ["date", "place", "amount", "currency"]:
            value = extracted_info.get(field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                extracted_info[field] = "NA"

        if not extracted_info:
            logger.error(f"Failed to extract information from OCR text for {file_path}")
            return None
        
        # Generate a filename based on the extracted information
        new_filename = generate_filename_from_info(extracted_info, file_path)
        logger.info(f"Generated filename: {new_filename}")
        
        # Save intermediate files to temp directory
        # Save OCR text to temp directory
        text_path = temp_dir / f"{file_path.stem}_ocr_output.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            if 'text' in extracted_info:
                f.write(extracted_info['text'])
            else:
                f.write(json.dumps(extracted_info, ensure_ascii=False, indent=2))
        logger.info(f"OCR text saved to: {text_path}")
        
        # Save extracted info to temp directory
        info_path = temp_dir / f"{file_path.stem}_extracted_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_info, f, ensure_ascii=False, indent=2)
        logger.info(f"Extracted information saved to: {info_path}")
        
        # Copy the PDF to the output directory with the new filename
        if temp_pdf_path:
            source_pdf = temp_pdf_path
        else:
            source_pdf = file_path
        
        final_pdf_path = output_dir / new_filename
        shutil.copy2(source_pdf, final_pdf_path)
        logger.info(f"Renamed PDF saved to: {final_pdf_path}")
        
        # Move original image file to temp directory (if image)
        if is_image:
            moved_path = temp_dir / file_path.name
            try:
                shutil.move(str(file_path), str(moved_path))
                logger.info(f"Moved original image to temp: {moved_path}")
            except Exception as e:
                logger.warning(f"Failed to move original image {file_path} to temp: {e}")
        
        # Add the final PDF path to the extracted info
        extracted_info['final_pdf_path'] = str(final_pdf_path)

        # Identify missing fields
        for field in ["date", "place", "amount", "currency"]:
            if not extracted_info.get(field):
                missing_fields.append(field)
        extracted_info['missing_fields'] = missing_fields
        
        return extracted_info
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return None
    finally:
        # Clean up temporary PDF file if created
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
                logger.debug(f"Removed temporary PDF file: {temp_pdf_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary PDF file {temp_pdf_path}: {e}")
        # Remove temp JSON file
        if info_path and os.path.exists(info_path):
            try:
                os.remove(info_path)
                logger.debug(f"Removed temp JSON file: {info_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp JSON file {info_path}: {e}")


def extract_info_with_mistral(file_path: Union[str, Path], ocr_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Use Mistral to extract receipt information
    Mistral을 사용하여 영수증 정보 추출
    
    Args:
        file_path: Path to the original file
                  원본 파일 경로
        ocr_text: OCR extracted text to analyze
                 분석할 OCR 추출 텍스트
    
    Returns:
        Dictionary with extracted receipt information or None if error occurs
        추출된 영수증 정보가 포함된 딕셔너리 또는 오류 발생 시 None
    """
    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY not set")
        return None
    
    try:
        # We use the document understanding capability to extract information
        # 문서 이해 기능을 사용하여 정보 추출
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
    
        # Initialize Mistral client
        client = Mistral(api_key=MISTRAL_API_KEY)
        
        # If local document, upload and retrieve the signed url
        # Convert Path to string for file_name parameter
        file_path_str = str(file_path)
        uploaded_file = client.files.upload(
            file={
                "file_name": os.path.basename(file_path_str),
                "content": open(file_path, "rb"),
            },
            purpose="ocr"
        )
        signed_url = client.files.get_signed_url(file_id=uploaded_file.id)

        # Define the messages for the chat
        
        messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "document_url",
                    "document_url": signed_url.url
                }
            ]
        }]

        # Use Mistral chat API to extract structured information from OCR text
        chat_response = client.chat.complete(
            model=MISTRAL_LLM_MODEL,
            messages=messages
        )
        
        logger.info(chat_response.choices[0].message.content)

        if chat_response and hasattr(chat_response, 'choices') and chat_response.choices:
            # Extract content from chat response
            content = chat_response.choices[0].message.content
            
            # Extract JSON from response
            try:
                # Try to find JSON-like content in the response
                json_match = re.search(r'{.*}', content, re.DOTALL)
                if json_match:
                    extracted_json = json.loads(json_match.group(0))
                else:
                    # If no JSON found, use a default structure
                    extracted_json = {
                        "date": None,
                        "place": None,
                        "amount": None,
                        "currency": None
                    }
                
                # Format date if available
                if extracted_json.get('date'):
                    try:
                        # Try to normalize various date formats to YYYYMMDD
                        date_str = str(extracted_json['date']).strip()
                        
                        if not date_str or date_str.lower() == "null" or date_str.lower() == "none":
                            logger.warning("Date is null or empty")
                            extracted_json['date'] = None
                        else:
                            # Handle various separators
                            date_str = re.sub(r'[-./]', '', date_str)
                            
                            # Remove any non-digit characters
                            date_str = re.sub(r'[^\d]', '', date_str)
                            
                            # Check if we have a valid date format after cleaning
                            if not date_str.isdigit():
                                logger.warning(f"Invalid date format after cleaning: {date_str}")
                                extracted_json['date'] = None
                            elif len(date_str) == 6:  # YYMMDD format
                                # Add century if only 2-digit year
                                year = int(date_str[:2])
                                current_century = datetime.now().year // 100
                                if year > (datetime.now().year % 100):
                                    year_prefix = current_century - 1
                                else:
                                    year_prefix = current_century
                                date_str = f"{year_prefix}{date_str}"
                                extracted_json['date'] = date_str
                            elif len(date_str) == 8:  # YYYYMMDD format
                                extracted_json['date'] = date_str
                            else:
                                logger.warning(f"Unusual date length after cleaning: {len(date_str)}")
                                if len(date_str) >= 8:  # If longer than 8, try to extract YYYYMMDD
                                    extracted_json['date'] = date_str[:8]
                                else:
                                    extracted_json['date'] = None
                    except Exception as e:
                        logger.warning(f"Failed to format date: {e}")
                        extracted_json['date'] = None
                
                # Convert amount to a number if available
                if extracted_json.get('amount'):
                    try:
                        # Remove any currency symbols and commas
                        amount_str = str(extracted_json['amount'])
                        amount_str = re.sub(r'[^\d.]', '', amount_str)
                        extracted_json['amount'] = float(amount_str)
                    except Exception as e:
                        logger.warning(f"Failed to convert amount to number: {e}")
                
                # Handle currency
                if extracted_json.get('currency'):
                    currency = extracted_json['currency'].upper()
                    # Normalize common currency names
                    if re.search(r'KRW|KOR|원화|₩|KR', currency):
                        currency = 'KRW'
                    elif re.search(r'USD|US|미국|달러|\$', currency):
                        currency = 'USD'
                    elif re.search(r'EUR|EU|유로|€', currency):
                        currency = 'EUR'
                    elif re.search(r'GBP|UK|영국|파운드|£', currency):
                        currency = 'GBP'
                    
                    extracted_json['currency'] = currency
                else:
                    # Default to KRW if no currency found
                    extracted_json['currency'] = 'KRW'
                
                return extracted_json
            except Exception as e:
                logger.error(f"Error parsing response JSON: {e}")
                return None
        else:
            logger.error("No response from Mistral chat API")
            return None
    except Exception as e:
        logger.error(f"Error extracting info with Mistral: {e}")
        return None

def process_directory(input_dir: Union[str, Path], output_dir: Optional[Path] = None) -> None:
    """
    Process all files in a directory
    디렉토리의 모든 파일 처리
    
    Args:
        input_dir: Path to the input directory
                  입력 디렉토리 경로
        output_dir: Optional path for output directory
                   선택적 출력 디렉토리 경로
    """
    try:
        # Setup directories (input, output, and temp)
        input_path, output_path, temp_path = setup_directory(input_dir, output_dir)
        
        processed_files = []
        failed_files = []
        missing_info_files = []  # (file_path, missing_fields)
        missing_field_stats = {"date": 0, "place": 0, "amount": 0, "currency": 0}
        
        for file_path in input_path.iterdir():
            # Skip the temp directory itself
            if file_path == temp_path:
                continue
                
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                logger.info(f"Processing file: {file_path}")
                
                # Process file with temp and output directories
                extracted_info = process_file(file_path, temp_path, output_path)
                
                if extracted_info:
                    processed_files.append((file_path, extracted_info.get('final_pdf_path', '')))
                    # Track missing fields
                    missing_fields = extracted_info.get('missing_fields', [])
                    if missing_fields:
                        missing_info_files.append((file_path, missing_fields))
                        for f in missing_fields:
                            if f in missing_field_stats:
                                missing_field_stats[f] += 1
                else:
                    failed_files.append(file_path)
        
        logger.info(f"Successfully processed {len(processed_files)} files")
        logger.info(f"Failed to process {len(failed_files)} files")
        
        if processed_files:
            logger.info("Successfully processed files:")
            for original_file, final_path in processed_files:
                logger.info(f" - {original_file} -> {final_path}")
        
        if failed_files:
            logger.info("Files that failed to process:")
            for file in failed_files:
                logger.info(f" - {file}")
        
        # Show missing info statistics
        if missing_info_files:
            logger.info(f"Files with missing extracted information: {len(missing_info_files)} / {len(processed_files)}")
            logger.info("Missing field counts:")
            for k, v in missing_field_stats.items():
                logger.info(f"  {k}: {v}")
            logger.info("Files missing fields:")
            for file_path, fields in missing_info_files:
                logger.info(f" - {file_path}: missing {fields}")
        else:
            logger.info("All processed files have all key information extracted.")
    except Exception as e:
        logger.error(f"Error processing directory {input_dir}: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract information from receipts using Mistral API")
    parser.add_argument("input", help="Path to input file or directory")
    parser.add_argument("--output", "-o", help="Output directory (optional)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    try:
        # Setup directories (input, output, and temp)
        if input_path.is_file():
            # For single file processing, create temp directory in the parent directory
            parent_dir = input_path.parent
            _, output_dir, temp_dir = setup_directory(parent_dir, output_path)
            
            if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                logger.info(f"Processing file: {input_path}")
                result = process_file(input_path, temp_dir, output_dir)
                if result:
                    logger.info(f"Extracted information: {json.dumps(result, ensure_ascii=False, indent=2)}")
                    logger.info(f"Final PDF saved to: {result.get('final_pdf_path', 'Unknown')}")
                else:
                    logger.error(f"Failed to extract information from {input_path}")
            else:
                logger.error(f"Unsupported file extension: {input_path.suffix}")
        elif input_path.is_dir():
            logger.info(f"Processing directory: {input_path}")
            process_directory(input_path, output_path)
        else:
            logger.error(f"Input path does not exist: {input_path}")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())