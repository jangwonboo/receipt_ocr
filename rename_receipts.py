#!/usr/bin/env python3
"""
Receipt File Renamer
영수증 파일 이름 변경 도구

This script renames receipt files (PDF, PNG, JPG, JPEG, TIF, TIFF) based on data extracted
from corresponding JSON files. It's designed to be used after running the ocr.py OCR script
that extracts structured data from receipt images/documents.

이 스크립트는 해당하는 JSON 파일에서 추출된 데이터를 기반으로 영수증 파일(PDF, PNG, JPG, JPEG, TIF, TIFF)의
이름을 변경합니다. 영수증 이미지/문서에서 구조화된 데이터를 추출하는 ocr.py OCR 스크립트를 실행한 후
사용하도록 설계되었습니다.

Features:
기능:
- Batch processing of multiple receipt files
  여러 영수증 파일의 일괄 처리
- Automatic extraction of date, store name, and price data from JSON
  JSON에서 날짜, 상점 이름 및 가격 데이터 자동 추출
- Support for multiple file formats (PDF, PNG, JPG, JPEG, TIF, TIFF)
  여러 파일 형식 지원 (PDF, PNG, JPG, JPEG, TIF, TIFF)
- Intelligent handling of missing data with fallbacks
  대체 옵션으로 누락된 데이터 지능적 처리
- Structured file naming format for easy organization
  쉬운 정리를 위한 구조화된 파일 이름 형식
- Detailed logging of all operations
  모든 작업에 대한 상세 로깅

The renamed format follows: {payment_date}_{store_name}_{total_price}.<original_extension>
- payment_date: Formatted as MMDD (e.g., 0415 for April 15)
- store_name: Special characters and spaces removed
- total_price: Units and currency symbols removed, only digits kept

변경된 이름 형식: {payment_date}_{store_name}_{total_price}.<원본_확장자>
- payment_date: MMDD 형식으로 포맷됨 (예: 4월 15일의 경우 0415)
- store_name: 특수 문자 및 공백 제거됨
- total_price: 단위 및 통화 기호 제거, 숫자만 유지됨

Usage:
사용법:
    python rename_receipts.py [--json_dir DIR] [--source_dir DIR] [--debug]

Options:
옵션:
    --json_dir DIR      Directory containing JSON files (default: current directory)
                       JSON 파일이 있는 디렉토리 (기본값: 현재 디렉토리)
    --source_dir DIR    Directory containing image/PDF files (default: same as json_dir)
                       이미지/PDF 파일이 있는 디렉토리 (기본값: json_dir과 동일)
    --debug            Enable detailed debug logging
                       상세한 디버그 로깅 활성화

Example:
예시:
    python rename_receipts.py --json_dir ./receipts --source_dir ./receipts

Author: Claude
Date: May 15, 2025
"""

import os
import json
import re
import argparse
import glob
import logging
from datetime import datetime

# Set up logging
# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Supported file extensions
# 지원되는 파일 확장자
SUPPORTED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff']

def clean_filename(text):
    """
    Cleans a string to make it suitable for a filename
    파일 이름으로 사용하기 적합하도록 문자열을 정리합니다
    """
    if not text:
        return "unknown"
    
    # Replace spaces with empty string
    # 공백을 빈 문자열로 대체
    cleaned = text.replace(" ", "").replace("\t", "")
    
    # Remove illegal filename characters (Windows naming conventions)
    # 파일 이름에 사용할 수 없는 문자 제거 (Windows 이름 지정 규칙)
    illegal_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(illegal_chars, '', cleaned)
    
    # If cleaned is empty after removing special chars, return "unknown"
    # 특수 문자 제거 후 정리된 문자열이 비어 있으면 "unknown" 반환
    return cleaned if cleaned else "unknown"

def format_date(date_str):
    """
    Formats a date string to MM/DD format
    날짜 문자열을 MM/DD 형식으로 포맷팅합니다
    """
    if not date_str:
        return "unknown_date"
    
    # Try different date formats
    # 다양한 날짜 형식 시도
    date_formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", 
        "%Y.%m.%d", "%m.%d.%Y", "%d.%m.%Y"
    ]
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%m%d")  # MM/DD -> MMDD (no slash)
        except ValueError:
            continue
    
    # If no format matches, return the original
    # 일치하는 형식이 없으면 원본 반환
    return date_str.replace("/", "").replace("-", "").replace(".", "")

def format_price(price_str):
    """
    Formats price string by removing currency symbols and commas
    통화 기호와 쉼표를 제거하여 가격 문자열을 포맷팅합니다
    """
    if not price_str:
        return "0"
    
    # Remove currency symbols, commas, spaces, and other non-digit characters
    # Keep the last period (decimal point) if exists
    # 통화 기호, 쉼표, 공백 및 기타 숫자가 아닌 문자 제거
    # 마지막 마침표(소수점)가 있으면 유지
    cleaned = re.sub(r'[^\d.]', '', price_str)
    
    # Handle case with no valid digits
    # 유효한 숫자가 없는 경우 처리
    if not cleaned or cleaned == '.':
        return "0"
    
    return cleaned

def calculate_total_from_items(items):
    """
    Calculate total price from individual item prices when total price is not available
    개별 항목 가격에서 총 가격을 계산합니다 (총 가격을 사용할 수 없을 때)
    
    Args:
        items (list): List of item dictionaries with price information
                    가격 정보가 있는 항목 사전 목록
    
    Returns:
        str: Calculated total price
            계산된 총 가격
    """
    total = 0
    for item in items:
        price_str = item.get('price', '')
        if not price_str:
            continue
            
        # Clean the price string and convert to float
        cleaned_price = format_price(price_str)
        try:
            total += float(cleaned_price)
        except ValueError:
            # Skip items where price couldn't be converted to float
            continue
            
    # Return the total as a formatted string
    return str(int(total))  # Round to nearest integer

def rename_receipt_files(json_dir=None, source_dir=None):
    """
    Rename receipt files based on information in corresponding JSON files.
    해당하는 JSON 파일의 정보를 기반으로 영수증 파일 이름을 변경합니다.
    
    Args:
        json_dir (str): Directory containing JSON files (default: current directory)
                        JSON 파일이 있는 디렉토리 (기본값: 현재 디렉토리)
        source_dir (str): Directory containing receipt files (default: same as json_dir)
                         영수증 파일이 있는 디렉토리 (기본값: json_dir과 동일)
    """
    # Use current directory if not specified
    # 지정되지 않은 경우 현재 디렉토리 사용
    if not json_dir:
        json_dir = os.getcwd()
    
    # Use json_dir for source files if not specified
    # 지정되지 않은 경우 소스 파일에 json_dir 사용
    if not source_dir:
        source_dir = json_dir
    
    # Get all JSON files
    # 모든 JSON 파일 가져오기
    json_files = glob.glob(os.path.join(json_dir, "*.json"))
    logger.info(f"Found {len(json_files)} JSON files in {json_dir}")
    
    # Process each JSON file
    # 각 JSON 파일 처리
    for json_file in json_files:
        json_basename = os.path.basename(json_file)
        base_name = os.path.splitext(json_basename)[0]
        
        # Check for corresponding files in all supported formats
        # 지원되는 모든 형식의 해당 파일 확인
        source_files = []
        for ext in SUPPORTED_EXTENSIONS:
            pattern = os.path.join(source_dir, f"{base_name}{ext}")
            matching_files = glob.glob(pattern)
            source_files.extend(matching_files)
        
        if not source_files:
            logger.warning(f"No matching files found for JSON: {json_basename}")
            continue
        
        try:
            # Load JSON data
            # JSON 데이터 로드
            with open(json_file, 'r', encoding='utf-8') as f:
                receipt_data = json.load(f)
            
            logger.debug(f"Processing JSON file: {json_basename}")
            logger.debug(f"JSON data keys: {list(receipt_data.keys())}")
            
            # Extract relevant information
            # 관련 정보 추출
            payment_date = ""
            store_name = ""
            total_price = ""
            
            # Check if the data is in the expected format
            # 데이터가 예상 형식인지 확인
            if isinstance(receipt_data, dict):
                # Try to get payment date
                # 결제 날짜 가져오기 시도
                if "payment_date" in receipt_data:
                    payment_date = receipt_data["payment_date"]
                elif "payment_info" in receipt_data and "date" in receipt_data["payment_info"]:
                    payment_date = receipt_data["payment_info"]["date"]
                
                # Try to get store name
                # 상점 이름 가져오기 시도
                if "store_name" in receipt_data:
                    store_name = receipt_data["store_name"]
                elif "store_info" in receipt_data and "name" in receipt_data["store_info"]:
                    store_name = receipt_data["store_info"]["name"]
                
                # Extract filename base if no store name found
                # 상점 이름이 없으면 파일 이름에서 추출
                if not store_name:
                    # Try to extract a name from the filename itself
                    store_name = os.path.splitext(base_name)[0]
                    logger.info(f"No store name found in JSON, using filename base: {store_name}")
                
                # Try to get total price
                # 총 가격 가져오기 시도
                if "total_price" in receipt_data:
                    total_price = receipt_data["total_price"]
                elif "payment_info" in receipt_data and "totalPrice" in receipt_data["payment_info"]:
                    total_price = receipt_data["payment_info"]["totalPrice"]
                
                # If total price is still empty, try to calculate from items
                # 총 가격이 여전히 비어 있으면 항목에서 계산을 시도
                if not total_price and "items" in receipt_data and receipt_data["items"]:
                    logger.info(f"Total price not found in JSON. Calculating from individual items.")
                    total_price = calculate_total_from_items(receipt_data["items"])
                    logger.info(f"Calculated total price: {total_price}")
            
            # Format the information
            # 정보 포맷팅
            formatted_date = format_date(payment_date)
            formatted_store = clean_filename(store_name)
            formatted_price = format_price(total_price)
            
            logger.debug(f"Formatted values: date={formatted_date}, store={formatted_store}, price={formatted_price}")
            
            # Skip if we have no meaningful data to use for renaming
            # 이름 변경에 사용할 의미 있는 데이터가 없으면 건너뛰기
            if formatted_date == "unknown_date" and formatted_store == "unknown" and formatted_price == "0":
                logger.warning(f"No meaningful data extracted from {json_basename}, skipping rename")
                continue
            
            # Process each matching file
            # 각 일치하는 파일 처리
            for source_file in source_files:
                file_basename = os.path.basename(source_file)
                file_ext = os.path.splitext(file_basename)[1]
                
                # Create new filename
                # 새 파일 이름 생성
                new_filename = f"{formatted_date}_{formatted_store}_{formatted_price}{file_ext}"
                new_path = os.path.join(source_dir, new_filename)
                
                # Rename the file
                # 파일 이름 변경
                logger.info(f"Renaming: {file_basename} -> {new_filename}")
                
                # Check if destination file already exists
                # 대상 파일이 이미 존재하는지 확인
                if os.path.exists(new_path) and source_file != new_path:
                    logger.warning(f"Destination file already exists: {new_filename}")
                    new_filename = f"{formatted_date}_{formatted_store}_{formatted_price}_{os.path.splitext(file_basename)[0]}{file_ext}"
                    new_path = os.path.join(source_dir, new_filename)
                    logger.info(f"Using alternative name: {new_filename}")
                
                os.rename(source_file, new_path)
                logger.info(f"Successfully renamed to: {new_filename}")
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON file: {json_file}")
        except Exception as e:
            logger.error(f"Error processing {json_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Rename receipt files based on OCR data in JSON files")
    parser.add_argument("--json_dir", help="Directory containing JSON files (default: current directory)")
    parser.add_argument("--source_dir", help="Directory containing receipt files (default: same as json_dir)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    rename_receipt_files(args.json_dir, args.source_dir)

if __name__ == "__main__":
    main() 