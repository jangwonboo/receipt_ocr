#!/usr/bin/env python3
"""
OCR Processing Tool for Receipts and Documents
영수증 및 문서용 OCR 처리 도구

This script provides functionality to perform OCR (Optical Character Recognition) on receipts
and general documents using Naver Cloud OCR API. It can extract text and structured data from
images and PDF files. Supported operations include general text extraction and specialized
receipt data extraction.

이 스크립트는 네이버 클라우드 OCR API를 사용하여 영수증 및 일반 문서에 대한 OCR(광학 문자 인식)을
수행하는 기능을 제공합니다. 이미지와 PDF 파일에서 텍스트 및 구조화된 데이터를 추출할 수 있습니다.
지원되는 작업에는 일반 텍스트 추출 및 특수한 영수증 데이터 추출이 포함됩니다.

Features:
기능:
- Process single files or entire directories
  단일 파일 또는 전체 디렉토리 처리
- Support for multiple file formats (PDF, JPG, PNG, TIFF)
  여러 파일 형식 지원 (PDF, JPG, PNG, TIFF)
- General OCR for text extraction from documents
  문서에서 텍스트 추출을 위한 일반 OCR
- Receipt OCR for structured data extraction from receipts
  영수증에서 구조화된 데이터 추출을 위한 영수증 OCR
- Support for Korean and English languages
  한국어 및 영어 언어 지원
- Conversion of multi-page PDFs
  여러 페이지 PDF 변환
- Output in JSON format for easy post-processing
  쉬운 후처리를 위한 JSON 형식 출력

Usage:
사용법:
    python ocr.py --file path/to/receipt.jpg --mode receipt
    python ocr.py --dir path/to/documents/ --mode general --lang ko
    python ocr.py --file path/to/document.pdf --output path/to/output/

Author: Claude
Date: May 15, 2025
"""

# Code to load pdf or docx file and convert it to text
# PDF 또는 DOCX 파일을 로드하고 텍스트로 변환하는 코드

import argparse
import sys
import os
import requests
import json
import base64
import time
import logging
from logging.handlers import RotatingFileHandler
import glob
from pdf2image import convert_from_path
from PIL import Image
import tempfile
import shutil

# Import from utils.py
# utils.py에서 가져오기
from utils import setup_logger

# Initialize logger
# 로거 초기화
logger = setup_logger()

# Dependencies are assumed to be installed
# 종속성이 이미 설치되어 있다고 가정

# General OCR API credentials and configuration
# 일반 OCR API 자격 증명 및 구성
GENERAL_SECRET = "bFRFc0lpWVNtb1NIdkxnYkJwZlZzQ216WkNkVFV2SU0="  # X-OCR-SECRET 값
GENERAL_DOMAIN_ID = "41840"
GENERAL_INVOKE_KEY = "9c0164ae62761049733ec404292901331072c6f2b511f8fbe0e899b229de65ef"
GENERAL_API_GATEWAY = "https://1ca5ztdzdg.apigw.ntruss.com"

# Receipt OCR API credentials and configuration
# 영수증 OCR API 자격 증명 및 구성
RECEIPT_SECRET = "VFJqQ21MYkJEc0VCdUVpd0hKTlRwdkx0VHhQZG1wQ2o="
RECEIPT_DOMAIN_ID = "42025"
RECEIPT_INVOKE_KEY = "e24fb8bb1b9e5b931f3a1efcf9baab214899b18e2ea248dc8722d8ed0a8597bc"
RECEIPT_API_GATEWAY = "https://mg6eku63fn.apigw.ntruss.com"

# Pre-defined URL patterns
# 미리 정의된 URL 패턴
# Pattern for general OCR endpoints (no document/ prefix)
GENERAL_URL_PATTERN = "{api_gateway}/custom/v1/{domain_id}/{invoke_key}/{endpoint}"
# Pattern for document-type OCR endpoints (with document/ prefix)
DOCUMENT_URL_PATTERN = "{api_gateway}/custom/v1/{domain_id}/{invoke_key}/document/{endpoint}"

MAX_FILE_SIZE_MB = 50

# Import check_file_validity from utils.py
from utils import check_file_validity

def make_ocr_request(api_endpoint, file_path, file_format, request_id=None, additional_params=None):
    """
    Make OCR API request to Naver Cloud
    네이버 클라우드에 OCR API 요청을 합니다
    
    Args:
        api_endpoint (str): API endpoint path (receipt, general, etc.)
                            API 엔드포인트 경로 (receipt, general 등)
        file_path (str): Path to the file
                         파일 경로
        file_format (str): Format of the file (jpg, png, pdf, tiff)
                          파일 형식 (jpg, png, pdf, tiff)
        request_id (str): Request ID (default: generated based on timestamp)
                         요청 ID (기본값: 타임스탬프 기반으로 생성)
        additional_params (dict): Additional parameters to include in the request
                                 요청에 포함할 추가 매개변수
    
    Returns:
        dict: API response or empty dict if request failed
              API 응답 또는 요청이 실패한 경우 빈 딕셔너리
    """
    # Get filename without extension for the name field
    # name 필드에 사용할 확장자 없는 파일 이름 가져오기
    file_name = os.path.basename(file_path).split('.')[0]
    
    # Generate timestamp and request ID
    # 타임스탬프 및 요청 ID 생성
    timestamp = int(time.time() * 1000)
    if not request_id:
        request_id = f"req_{timestamp}"
    
    # Base request data
    # 기본 요청 데이터
    base_request = {
        "images": [
            {
                "format": file_format,
                "name": file_name
            }
        ],
        "requestId": request_id,
        "version": "V2",
        "timestamp": timestamp
    }
    
    # Add additional parameters if provided
    # 추가 매개변수가 제공된 경우 추가
    if additional_params:
        for key, value in additional_params.items():
            base_request[key] = value
    
    # Log the original api_endpoint
    # 원래 api_endpoint 로깅
    logger.debug(f"Original api_endpoint: '{api_endpoint}'")
    
    # Make sure the api_endpoint has no leading or trailing slash
    # api_endpoint에 선행 또는 후행 슬래시가 없는지 확인
    if api_endpoint.startswith('/'):
        api_endpoint = api_endpoint[1:]
    if api_endpoint.endswith('/'):
        api_endpoint = api_endpoint[:-1]
    
    # Check for direct URL in environment (for testing)
    # 환경에서 직접 URL 확인 (테스트용)
    if os.environ.get('GENERAL_OCR_DIRECT_URL'):
        full_api_url = os.environ.get('GENERAL_OCR_DIRECT_URL')
        logger.debug(f"Using direct URL from environment: {full_api_url}")
        secret_key = GENERAL_SECRET  # Default to general secret
    
    # Determine which credentials to use based on endpoint
    # 엔드포인트에 따라 사용할 자격 증명 결정
    elif api_endpoint == 'document/receipt' or api_endpoint == 'receipt':
        # For receipt OCR, use receipt credentials
        # 영수증 OCR에는 영수증 자격 증명 사용
        api_gateway = RECEIPT_API_GATEWAY
        domain_id = RECEIPT_DOMAIN_ID
        invoke_key = RECEIPT_INVOKE_KEY
        secret_key = RECEIPT_SECRET
        
        # Use document pattern with 'receipt' endpoint
        # 'receipt' 엔드포인트에 문서 패턴 사용
        endpoint = 'receipt' if api_endpoint == 'receipt' else api_endpoint.replace('document/', '')
        full_api_url = DOCUMENT_URL_PATTERN.format(
            api_gateway=api_gateway,
            domain_id=domain_id,
            invoke_key=invoke_key,
            endpoint=endpoint
        )
        logger.debug(f"Using receipt OCR URL: {full_api_url}")
    else:
        # For all other endpoints, use general credentials
        # 다른 모든 엔드포인트에는 일반 자격 증명 사용
        api_gateway = GENERAL_API_GATEWAY
        domain_id = GENERAL_DOMAIN_ID
        invoke_key = GENERAL_INVOKE_KEY
        secret_key = GENERAL_SECRET
        
        # Choose the correct URL pattern based on endpoint type
        # 엔드포인트 유형에 따라 올바른 URL 패턴 선택
        if api_endpoint in ['receipt'] or api_endpoint.startswith('document/'):
            # Document-type endpoints
            # 문서 유형 엔드포인트
            endpoint = api_endpoint if not api_endpoint.startswith('document/') else api_endpoint[len('document/'):]            
            full_api_url = DOCUMENT_URL_PATTERN.format(
                api_gateway=api_gateway,
                domain_id=domain_id,
                invoke_key=invoke_key,
                endpoint=endpoint
            )
            logger.debug(f"Using document endpoint URL: {full_api_url}")
        else:
            # General OCR endpoints
            # 일반 OCR 엔드포인트
            full_api_url = GENERAL_URL_PATTERN.format(
                api_gateway=api_gateway,
                domain_id=domain_id,
                invoke_key=invoke_key,
                endpoint=api_endpoint
            )
            logger.debug(f"Using general endpoint URL: {full_api_url}")
    
    logger.debug(f"Making OCR request to: {full_api_url}")
    logger.debug(f"Request data: {json.dumps(base_request, ensure_ascii=False)}")
    
    try:
        headers = {
            "X-OCR-SECRET": secret_key,
            "Content-Type": "application/json"
        }
        
        # Initialize result container
        result = {"images": []}
        
        # For PDF files, extract and process the first page as an image
        if file_format == 'pdf':
            # Create a temporary image file path
            temp_img_path = f"{file_path}_page_1.jpg"
            
            try:
                logger.debug(f"Converting PDF to image: {file_path}")
                
                pages = convert_from_path(file_path, 300, first_page=1, last_page=1)  # Only first page
                if pages:
                    pages[0].save(temp_img_path, 'JPEG')
                else:
                    logger.error("Failed to convert PDF: No pages returned")
                    return {}
            except Exception as pdf_error:
                logger.error(f"PDF conversion failed: {str(pdf_error)}")
                return {}
                
            # Read the temporary image file
            try:
                with open(temp_img_path, 'rb') as f:
                    file_data = f.read()
                
                # Clean up temp file
                os.remove(temp_img_path)
                
                # Update request for the image
                base_request["images"][0]["format"] = "jpg"
            except Exception as file_error:
                logger.error(f"Failed to read temporary image file: {str(file_error)}")
                return {}
                
        else:  # For image files (jpg, png)
            # Read the file as binary
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
            except Exception as file_error:
                logger.error(f"Failed to read image file: {str(file_error)}")
                return {}
        
        # Convert to base64 for API request
        file_data_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # Add base64 data to the request
        base_request["images"][0]["data"] = file_data_base64
        
        logger.debug(f"Sending OCR request to {api_endpoint}")
        request_body = json.dumps(base_request, ensure_ascii=False)
        logger.debug(f"Request body preview: {request_body[:100]}...")
        
        # Make the API request
        logger.debug(f"Sending POST request to URL: {full_api_url}")
        response = requests.post(full_api_url, headers=headers, data=request_body)
        
        # Process response
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"OCR API response received successfully")
            return result
        else:
            logger.error(f"OCR API request failed: {response.status_code}, {response.text}")
            return {}
            
    except Exception as e:
        logger.error(f"Exception during API request: {str(e)}")
        return {}

def extract_receipt(image_path):
    """
    Extract receipt information using Naver Cloud CLOVA OCR API
    
    Args:
        image_path (str): Path to receipt image file (jpg, jpeg, png, pdf, tif, tiff)
    
    Returns:
        dict: Extracted receipt information
    """
    logger.info(f"Starting receipt extraction for {image_path}")
    
    # Check file validity
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
    is_valid, file_format, error_msg = check_file_validity(image_path, allowed_extensions)
    
    if not is_valid:
        logger.error(error_msg)
        return {}
    
    # Make OCR API request
    result = make_ocr_request("document/receipt", image_path, file_format)
    
    if not result or not result.get('images'):
        logger.error("Receipt extraction failed. Empty or invalid API response.")
        return {}
    
    # Extract receipt fields
    try:
        receipt_data = {}
        receipt_results = result.get('images', [{}])[0].get('receipt', {})
        
        if 'result' not in receipt_results:
            return {}
            
        # Extract store info
        store_info = receipt_results['result'].get('storeInfo', {})
        receipt_data['store_name'] = store_info.get('name', {}).get('text', '')
        receipt_data['store_biznum'] = store_info.get('bizNum', {}).get('text', '')
        
        # Extract addresses
        receipt_data['store_address'] = []
        for addr in store_info.get("addresses", []):
            if isinstance(addr, dict) and addr.get('text'):
                receipt_data['store_address'].append(addr.get('text', ''))
        
        # Extract phone numbers
        receipt_data['store_tel'] = []
        for tel in store_info.get("tel", []):
            if isinstance(tel, dict) and tel.get('text'):
                receipt_data['store_tel'].append(tel.get('text', ''))
        
        # Extract payment info
        payment_info = receipt_results['result'].get('paymentInfo', {})
        receipt_data['total_price'] = ''
        if payment_info.get('totalPrice') and payment_info['totalPrice'].get('price'):
            receipt_data['total_price'] = payment_info['totalPrice']['price'].get('text', '')
        
        receipt_data['payment_date'] = payment_info.get('date', {}).get('text', '')
        receipt_data['payment_time'] = payment_info.get('time', {}).get('text', '')
        
        # Extract items
        receipt_data['items'] = []
        for subresult in receipt_results['result'].get('subResults', []):
            if 'items' in subresult:
                for item in subresult.get('items', []):
                    item_data = {
                        'name': item.get('name', {}).get('text', ''),
                        'count': item.get('count', {}).get('text', ''),
                        'price': item.get('price', {}).get('price', {}).get('text', '') if item.get('price') else '',
                        'unit_price': item.get('price', {}).get('unitPrice', {}).get('text', '') if item.get('price') else ''
                    }
                    receipt_data['items'].append(item_data)
        
        # Create combined data structures for compatibility
        receipt_data['store_info'] = {
            'name': receipt_data['store_name'],
            'bizNum': receipt_data['store_biznum'],
            'address': receipt_data['store_address'],
            'tel': receipt_data['store_tel']
        }
        
        receipt_data['payment_info'] = {
            'date': receipt_data['payment_date'],
            'time': receipt_data['payment_time'],
            'totalPrice': receipt_data['total_price']
        }
        
        return receipt_data
    except Exception as e:
        logger.error(f"Error parsing receipt data: {str(e)}")
        return {}

# These functions have been moved to their respective files:
# - convert_to_markdown(receipt_data) -> moved to receipt.py
# - extract_namecard(image_path, use_alt_url=False) -> moved to namecard.py
# - convert_namecard_to_markdown(namecard_data) -> moved to namecard.py

def test_ocr_connectivity():
    """
    Test connectivity to the Naver Cloud OCR API
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    logger.info("Testing OCR API connectivity")
    
    # Create a simple test request
    headers = {
        "X-OCR-SECRET": GENERAL_SECRET,
        "Content-Type": "application/json"
    }
    
    # Create a minimal test request body with required fields
    test_data = {
        "version": "V2",
        "requestId": f"test_{int(time.time() * 1000)}",
        "timestamp": int(time.time() * 1000),
        "images": [
            {
                "format": "jpg",
                "name": "connectivity_test"
            }
        ]
    }
    
    try:
        # Use document/receipt endpoint for testing
        test_url = f"{GENERAL_API_GATEWAY}/custom/v1/{GENERAL_DOMAIN_ID}/{GENERAL_INVOKE_KEY}/document/receipt"
        
        # Make the API request
        logger.debug(f"Testing connectivity to: {test_url}")
        response = requests.post(test_url, headers=headers, data=json.dumps(test_data))
        
        # Check response
        logger.info(f"API connectivity test response: {response.status_code}")
        
        if response.status_code in [400, 401]:
            # If we get a 400 status, it might be due to missing image data
            # For connectivity testing, we just need to verify the API responds
            logger.debug(f"Received expected error response (missing image data): {response.text}")
            return True
        elif response.status_code == 200:
            logger.info("API connectivity test successful")
            return True
        else:
            logger.error(f"API connectivity test failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API connectivity test failed with exception: {str(e)}")
        return False

def process_pdf_for_ocr(pdf_path, mode='receipt'):
    """
    Process a PDF file by converting each page to an image and running OCR on it
    PDF 파일을 이미지로 변환하여 OCR 처리합니다
    
    Args:
        pdf_path (str): Path to the PDF file
                       PDF 파일 경로
        mode (str): OCR mode ('receipt' or 'general')
                   OCR 모드 ('receipt' 또는 'general')
        
    Returns:
        list: List of OCR results for each page
             각 페이지에 대한 OCR 결과 목록
    """
    logger.info(f"Processing PDF file: {pdf_path}")
    
    # Create a temporary directory for the converted images
    # 변환된 이미지를 위한 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    logger.debug(f"Created temporary directory: {temp_dir}")
    
    try:
        # Convert PDF to images
        # PDF를 이미지로 변환
        logger.info(f"Converting PDF to images")
        try:
            images = convert_from_path(pdf_path, 300)
            logger.info(f"Converted {len(images)} pages from PDF")
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            return []
        
        results = []
        
        # Process each page
        # 각 페이지 처리
        for i, image in enumerate(images):
            logger.info(f"Processing page {i+1}/{len(images)}")
            
            # Save image to temporary file
            # 이미지를 임시 파일로 저장
            temp_img_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
            image.save(temp_img_path, "JPEG")
            
            # Process the image based on the mode
            # 모드에 따라 이미지 처리
            if mode == 'receipt':
                page_result = extract_receipt(temp_img_path)
            else:  # general OCR
                # For general OCR, use the general endpoint
                # 일반 OCR의 경우 일반 엔드포인트 사용
                allowed_extensions = ['.jpg', '.jpeg', '.png']
                is_valid, file_format, _ = check_file_validity(temp_img_path, allowed_extensions)
                if is_valid:
                    page_result = make_ocr_request("general", temp_img_path, file_format)
                else:
                    page_result = {}
            
            # Add page information to the result
            # 결과에 페이지 정보 추가
            if page_result:
                page_result['page_number'] = i + 1
                results.append(page_result)
            
            # Clean up the temporary image
            # 임시 이미지 정리
            os.remove(temp_img_path)
        
        return results
    
    finally:
        # Clean up the temporary directory
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug("Cleaned up temporary directory")

def perform_general_ocr(image_path, lang="ko"):
    """
    Perform general OCR on an image file
    이미지 파일에 일반 OCR 수행
    
    Args:
        image_path (str): Path to the image file
                          이미지 파일 경로
        lang (str): Language for OCR
                    OCR용 언어
    
    Returns:
        dict: OCR result
              OCR 결과
    """
    logger.info(f"Performing general OCR on {image_path}")
    
    # Check file validity
    # 파일 유효성 확인
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
    is_valid, file_format, error_msg = check_file_validity(image_path, allowed_extensions)
    
    if not is_valid:
        logger.error(error_msg)
        return {}
    
    # For PDF files, use the PDF processing function
    # PDF 파일의 경우 PDF 처리 함수 사용
    if file_format == 'pdf':
        results = process_pdf_for_ocr(image_path, mode='general')
        if not results:
            return {}
        
        # Combine results from all pages
        # 모든 페이지의 결과 결합
        combined_result = results[0] if results else {}
        if len(results) > 1:
            combined_result['multi_page'] = True
            combined_result['page_count'] = len(results)
            combined_result['pages'] = results
        
        return combined_result
    
    # For image files, make a direct OCR request
    # 이미지 파일의 경우 직접 OCR 요청
    additional_params = {"lang": lang}
    result = make_ocr_request("general", image_path, file_format, additional_params=additional_params)
    
    return result

def extract_text_from_ocr_result(ocr_result):
    """
    Extract plain text from OCR result
    OCR 결과에서 일반 텍스트 추출
    
    Args:
        ocr_result (dict): OCR result from general OCR
                          일반 OCR의 OCR 결과
    
    Returns:
        str: Extracted text
             추출된 텍스트
    """
    if not ocr_result or not ocr_result.get('images'):
        return ""
    
    text_lines = []
    
    # Handle multi-page results
    # 다중 페이지 결과 처리
    if ocr_result.get('multi_page') and ocr_result.get('pages'):
        for page in ocr_result.get('pages', []):
            page_num = page.get('page_number', 0)
            text_lines.append(f"--- Page {page_num} ---\n")
            
            # Extract text from this page
            # 이 페이지에서 텍스트 추출
            for image in page.get('images', []):
                for field in image.get('fields', []):
                    text_lines.append(field.get('inferText', ''))
            
            text_lines.append("\n")
    else:
        # Single page result
        # 단일 페이지 결과
        for image in ocr_result.get('images', []):
            for field in image.get('fields', []):
                text_lines.append(field.get('inferText', ''))
    
    return "\n".join(text_lines)

def main():
    # Set up argument parser
    # 인수 파서 설정
    parser = argparse.ArgumentParser(description='Process documents using Naver Cloud CLOVA OCR.')
    parser.add_argument('--input', '-i', help='Path to the input file')
    parser.add_argument('--input-dir', '-id', help='Path to the input directory containing files to process')
    parser.add_argument('--output', '-o', help='Path to the output file (default: input filename with .txt, .json, or .md extension)')
    parser.add_argument('--output-dir', '-od', help='Path to the output directory for processed files')
    parser.add_argument('--page_range', '-p', help='Page range to process for PDF files (e.g. 1-3 for pages 1, 2, and 3)')
    parser.add_argument('--log_level', '-l', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level (default: INFO)')
    parser.add_argument('--log_file', '-f', default='pdf_ocr.log', help='Log file path (default: pdf_ocr.log)')
    parser.add_argument('--lang', '-la', default='ko', 
                        help='Language for OCR: ko (Korean), ja (Japanese), zh-TW (Chinese Traditional). Separate multiple languages with comma: ko,ja')
    parser.add_argument('--mode', '-m', default='text', choices=['text', 'receipt'],
                        help='OCR mode: text (general OCR) or receipt (receipt extraction)')
    parser.add_argument('--format', '-fmt', default='auto', choices=['auto', 'json', 'text'],
                        help='Output format: json, text, or markdown (default: auto - based on mode)')
    parser.add_argument('--all_pages', '-a', action='store_true', help='Process all pages of a PDF file (default: only first page)')
    args = parser.parse_args()
    
    # Configure logger with user-specified level
    # 사용자가 지정한 레벨로 로거 구성
    global logger
    log_level = getattr(logging, args.log_level)
    logger = setup_logger(args.log_file, log_level)
    
    logger.info(f"Starting OCR with Naver Cloud CLOVA OCR")
    
    # Check if either input file or input directory is provided
    # 입력 파일 또는 입력 디렉토리가 제공되었는지 확인
    if not args.input and not args.input_dir:
        logger.error("Either input file or input directory is required")
        print("Error: Either input file (--input) or input directory (--input-dir) is required.")
        return 1
    
    # Check output directory if input directory is provided
    # 입력 디렉토리가 제공된 경우 출력 디렉토리 확인
    if args.input_dir and not args.output_dir:
        logger.error("Output directory is required when processing a directory of files")
        print("Error: Output directory (--output-dir) is required when processing a directory of files.")
        return 1
    
    # Create output directory if it doesn't exist
    # 출력 디렉토리가 존재하지 않는 경우 생성
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info(f"Created output directory: {args.output_dir}")
    
    # Process a single file
    # 단일 파일 처리
    if args.input:
        return process_single_file(args)
    
    # Process all files in the input directory
    # 입력 디렉토리의 모든 파일 처리
    return process_directory(args)

def process_single_file(args):
    """
    Process a single file with OCR
    단일 파일 OCR 처리
    
    Args:
        args: Command line arguments
              명령줄 인수
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
             종료 코드 (0: 성공, 1: 실패)
    """
    input_path = args.input
    logger.info(f"Processing single file: {input_path}")
    
    # Check file extension and determine if it's a valid file
    # 파일 확장자 확인하고 유효한 파일인지 판단
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
    is_valid, file_format, error_msg = check_file_validity(input_path, allowed_extensions)
    
    if not is_valid:
        logger.error(error_msg)
        print(f"Error: {error_msg}")
        return 1
    
    # Determine output format
    # 출력 형식 결정
    output_format = args.format
    if output_format == 'auto':
        if args.mode == 'receipt':
            output_format = 'json'  # Default for structured data
        else:
            output_format = 'text'  # Default for general OCR
    
    # Set output path
    # 출력 경로 설정
    if args.output:
        output_path = args.output
    else:
        if output_format == 'json':
            output_path = os.path.splitext(input_path)[0] + '.json'
        elif output_format == 'markdown':
            output_path = os.path.splitext(input_path)[0] + '.md'
        else:
            output_path = os.path.splitext(input_path)[0] + '.txt'
    
    logger.info(f"Output will be saved to: {output_path}")
    
    # Process file based on mode
    # 모드에 따라 파일 처리
    try:
        if args.mode == 'receipt':
            # Process receipt
            # 영수증 처리
            if file_format == 'pdf' and args.all_pages:
                # Process all pages of the PDF
                # PDF의 모든 페이지 처리
                results = process_pdf_for_ocr(input_path, 'receipt')
                if not results:
                    logger.error("Receipt extraction failed. Check the log for details.")
                    print("Error: Receipt extraction failed. Check the log for details.")
                    return 1
                    
                # For multiple pages, we combine the results
                # 여러 페이지의 경우 결과 결합
                combined_result = results[0] if results else {}
                if len(results) > 1:
                    # Indicate that this is a multi-page result
                    # 이것이 다중 페이지 결과임을 표시
                    combined_result['multi_page'] = True
                    combined_result['page_count'] = len(results)
                    combined_result['pages'] = results
                
                result = combined_result
            else:
                # Process a single image or the first page of a PDF
                # 단일 이미지 또는 PDF의 첫 페이지 처리
                result = extract_receipt(input_path)
            
            if not result:
                logger.error("Receipt extraction failed. Check the log for details.")
                print("Error: Receipt extraction failed. Check the log for details.")
                return 1
                
            # Convert to the requested format
            # 요청된 형식으로 변환
            if output_format == 'text':
                # Simple text representation of the receipt
                # 영수증의 간단한 텍스트 표현
                result_content = str(result)
            else:  # json
                result_content = result
                
        else:  # text mode
            # General OCR
            # 일반 OCR
            ocr_result = perform_general_ocr(input_path, args.lang)
            
            if not ocr_result:
                logger.error("Text extraction failed. Check the log for details.")
                print("Error: Text extraction failed. Check the log for details.")
                return 1
            
            # Extract text from OCR result
            # OCR 결과에서 텍스트 추출
            if output_format == 'json':
                result_content = ocr_result
            else:  # text or markdown
                result_content = extract_text_from_ocr_result(ocr_result)
        
        # Write output to file
        # 파일에 출력 쓰기
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if output_format == 'json':
                    json.dump(result_content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(result_content)
            logger.info(f"Processing complete. Output saved to {output_path}")
            print(f"Success: Processing complete. Output saved to {output_path}")
            return 0
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")
            print(f"Error: Failed to write output file: {e}")
            return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        print(f"Error: An unexpected error occurred: {str(e)}")
        return 1

def process_directory(args):
    """
    Process all files in a directory
    디렉토리의 모든 파일 처리
    
    Args:
        args: Command line arguments
              명령줄 인수
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
             종료 코드 (0: 성공, 0이 아닌 값: 실패)
    """
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    logger.info(f"Processing all files in directory: {input_dir}")
    
    # Find all files with supported extensions
    # 지원되는 확장자를 가진 모든 파일 찾기
    supported_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
    input_files = []
    
    for ext in supported_extensions:
        input_files.extend(glob.glob(os.path.join(input_dir, f"*{ext}")))
        input_files.extend(glob.glob(os.path.join(input_dir, f"*{ext.upper()}")))
    
    if not input_files:
        logger.warning(f"No supported files found in {input_dir}")
        print(f"Warning: No supported files found in {input_dir}")
        return 0
    
    logger.info(f"Found {len(input_files)} files to process")
    print(f"Found {len(input_files)} files to process")
    
    # Process each file
    # 각 파일 처리
    success_count = 0
    failure_count = 0
    
    for file_path in input_files:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        
        # Determine output format
        # 출력 형식 결정
        output_format = args.format
        if output_format == 'auto':
            if args.mode == 'receipt':
                output_format = 'json'
            else:
                output_format = 'text'
        
        # Set output file path
        # 출력 파일 경로 설정
        if output_format == 'json':
            output_file = f"{base_name}.json"
        else:
            output_file = f"{base_name}.txt"
            
        output_path = os.path.join(output_dir, output_file)
        
        # Create a temporary args object with the current file
        # 현재 파일로 임시 args 객체 생성
        file_args = argparse.Namespace(
            input=file_path,
            output=output_path,
            mode=args.mode,
            format=output_format,
            lang=args.lang,
            all_pages=args.all_pages,
            page_range=args.page_range
        )
        
        logger.info(f"Processing file {success_count + failure_count + 1}/{len(input_files)}: {filename}")
        print(f"Processing file {success_count + failure_count + 1}/{len(input_files)}: {filename}")
        
        # Process the file
        # 파일 처리
        try:
            result = process_single_file(file_args)
            if result == 0:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            print(f"Error processing {filename}: {str(e)}")
            failure_count += 1
    
    # Print summary
    # 요약 출력
    logger.info(f"Processing complete: {success_count} successful, {failure_count} failed")
    print(f"Processing complete: {success_count} successful, {failure_count} failed")
    
    if failure_count > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
