#!/usr/bin/env python3
# Code to load pdf or docx file and convert it to text
# PDF 또는 DOCX 파일을 로드하고 텍스트로 변환하는 코드

import argparse
import sys
import os
import requests
import json
import base64
import time
import os
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
# 로깅 설정
def setup_logger(log_file='pdf_ocr.log', log_level=logging.DEBUG):
    """
    Set up logger with console and file handlers
    콘솔 및 파일 핸들러로 로거를 설정합니다
    """
    # Create logger
    # 로거 생성
    logger = logging.getLogger('pdf_ocr')
    logger.setLevel(log_level)
    logger.propagate = False  # Don't propagate to root logger
                             # 루트 로거로 전파하지 않음
    
    # Clear existing handlers if any
    # 기존 핸들러가 있으면 제거
    if logger.handlers:
        logger.handlers = []
    
    # Create formatters
    # 포맷터 생성
    file_formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(filename)s:%(lineno)d - %(message)s')
    
    # Create file handler (with rotation)
    # 파일 핸들러 생성 (로테이션 포함)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    
    # Create console handler
    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    
    # Add handlers to logger
    # 로거에 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
# 로거 초기화
logger = setup_logger()
    
def convert_pdf_to_text(pdf_path, page_range=None, lang="ko"):
    """
    Convert PDF to text using Naver Cloud CLOVA OCR API
    네이버 클라우드 CLOVA OCR API를 사용하여 PDF를 텍스트로 변환합니다
    
    Args:
        pdf_path (str): Path to PDF file
                        PDF 파일 경로
        page_range (str or tuple): Range of pages to process (e.g., "1-5" or (1, 5))
                                  처리할 페이지 범위 (예: "1-5" 또는 (1, 5))
        lang (str): Language for OCR - "ko" (Korean), "ja" (Japanese), "zh-TW" (Chinese Traditional)
                   Can specify multiple languages with comma: "ko,ja,zh-TW"
                   OCR용 언어 - "ko" (한국어), "ja" (일본어), "zh-TW" (중국어 번체)
                   쉼표로 여러 언어 지정 가능: "ko,ja,zh-TW"
    
    Returns:
        str: Extracted text from the PDF
             PDF에서 추출된 텍스트
    """
    logger.info(f"Starting OCR conversion for {pdf_path} with language: {lang}")
    
    # Naver Cloud OCR API credentials - Replace with your actual credentials
    # ===== IMPORTANT: REPLACE THESE VALUES =====
    # 네이버 클라우드 OCR API 자격 증명 - 실제 자격 증명으로 대체하세요
    # ===== 중요: 이 값들을 대체하세요 =====
    ocr_secret = "aFhWUlJBVER6ZUtkc0dmWWdpTUtJeHBjY2RrcVl3UlE="  # X-OCR-SECRET 값
    # 형식: https://{APIGW_URL}/custom/v1/{SERVICE_ID}/general
    api_url = "https://1ca5ztdzdg.apigw.ntruss.com/custom/v1/41840/9c0164ae62761049733ec404292901331072c6f2b511f8fbe0e899b229de65ef/general"
    # ==========================================
    
    # Read the PDF file as binary
    # Import PyPDF2 for PDF processing and PyMuPDF for image conversion
    # PDF 파일을 바이너리로 읽기
    # PDF 처리용 PyPDF2 및 이미지 변환용 PyMuPDF 가져오기
    import PyPDF2
    import fitz  # PyMuPDF, better for PDF to image conversion
    import io
    
    # Check if file exists
    # 파일이 존재하는지 확인
    if not os.path.exists(pdf_path):
        logger.error(f"Error: File {pdf_path} does not exist")
        return ""
    
    # Open the PDF file
    # PDF 파일 열기
    try:
        pdf_file = open(pdf_path, 'rb')
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        logger.debug(f"Successfully opened PDF file: {pdf_path}")
    except Exception as e:
        logger.error(f"Failed to open PDF file: {e}")
        return ""
    
    # Check file size - API limit is 50MB
    # 파일 크기 확인 - API 제한은 50MB
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    logger.debug(f"File size: {file_size_mb:.2f}MB")
    if file_size_mb > 50:
        logger.error(f"Error: File size ({file_size_mb:.2f}MB) exceeds the 50MB limit")
        pdf_file.close()
        return ""
    
    # Get total number of pages
    # 총 페이지 수 가져오기
    num_pages = len(pdf_reader.pages)
    logger.info(f"PDF has {num_pages} pages")
    
    # Prepare headers with Naver API credentials
    # 네이버 API 자격 증명으로 헤더 준비
    headers = {
        "X-OCR-SECRET": ocr_secret,
        "Content-Type": "application/json"
    }
    
    # Get filename without extension for the name field
    # name 필드에 사용할 확장자 없는 파일 이름 가져오기
    file_name = os.path.basename(pdf_path).split('.')[0]
    
    # Process each page and collect text
    # 각 페이지를 처리하고 텍스트 수집
    all_text = ""
    
    # Parse page_range if it's a string
    # page_range가 문자열인 경우 파싱
    if isinstance(page_range, str) and page_range:
        try:
            parts = page_range.split('-')
            if len(parts) == 2:
                start_page = max(0, int(parts[0]) - 1)  # Convert from 1-indexed to 0-indexed
                end_page = min(num_pages, int(parts[1]))
                pages_to_process = range(start_page, end_page)
                logger.info(f"Processing pages {start_page+1} to {end_page} (user requested {page_range})")
            else:
                logger.warning(f"Invalid page range format: {page_range}. Using all pages.")
                pages_to_process = range(num_pages)
        except ValueError:
            logger.warning(f"Invalid page range format: {page_range}. Using all pages.")
            pages_to_process = range(num_pages)
    # If it's already a tuple of integers, use it directly
    # 이미 정수 튜플인 경우 직접 사용
    elif isinstance(page_range, tuple) and len(page_range) == 2:
        start_page = max(0, page_range[0] - 1)  # Convert from 1-indexed to 0-indexed
        end_page = min(num_pages, page_range[1])
        pages_to_process = range(start_page, end_page)
        logger.info(f"Processing pages {start_page+1} to {end_page}")
    # Default: process all pages
    # 기본값: 모든 페이지 처리
    else:
        pages_to_process = range(num_pages)
        logger.info(f"No page range specified, processing all {num_pages} pages")
    
    # Open PDF with PyMuPDF
    # PyMuPDF로 PDF 열기
    try:
        doc = fitz.open(pdf_path)
        logger.debug("Successfully opened PDF with PyMuPDF")
    except Exception as e:
        logger.error(f"Failed to open PDF with PyMuPDF: {e}")
        pdf_file.close()
        return ""
    
    processed_pages = 0
    failed_pages = 0
    
    for page_num in pages_to_process:
        logger.info(f"Processing page {page_num+1}/{num_pages}")
        try:
            # Get page and render to image
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 dpi
            logger.debug(f"Rendered page {page_num+1} to image ({pix.width}x{pix.height})")
            
            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")
            
            # Convert to base64 for API request
            file_data_base64 = base64.b64encode(img_bytes).decode('utf-8')
            logger.debug(f"Converted page {page_num+1} to base64 (length: {len(file_data_base64)})")
            
            # Prepare request data
            timestamp = int(time.time() * 1000)
            
            data = {
                "version": "V2",  # 권장: V2 엔진 사용
                "requestId": f"page_{page_num}_{timestamp}",
                "timestamp": timestamp,
                "lang": lang,  # 언어 설정
                "images": [
                    {
                        "format": "png",
                        "name": f"{file_name}_page_{page_num}",
                        "data": file_data_base64
                    }
                ],
                "enableTableDetection": True  # 표 감지 활성화 (도메인에서 설정 필요)
            }
            
            # Make API request
            logger.debug(f"Sending OCR request for page {page_num+1}")
            response = requests.post(api_url, headers=headers, data=json.dumps(data))
            
            # Process response
            if response.status_code == 200:
                result = response.json()
                page_text = ""
                
                # Extract text from OCR results
                fields_count = 0
                for image in result.get("images", []):
                    fields_count += len(image.get("fields", []))
                    for field in image.get("fields", []):
                        page_text += field.get("inferText", "") + " "
                        
                    # Process table if present (V2 엔진에서만 사용 가능)
                    if "tables" in image:
                        for table_idx, table in enumerate(image.get("tables", [])):
                            page_text += f"\n\n[Table {table_idx+1}]\n"
                            
                            # Process cells in the table
                            for cell in table.get("cells", []):
                                row_idx = cell.get("rowIndex", 0)
                                col_idx = cell.get("columnIndex", 0)
                                text = cell.get("inferText", "")
                                page_text += f"({row_idx},{col_idx}): {text}\n"
                
                logger.info(f"OCR successful for page {page_num+1}: extracted {fields_count} text fields")
                all_text += f"Page {page_num+1}\n\n{page_text}\n\n"
                
                # Write partial results to a temporary file for debugging
                tmp_file_path = f"{os.path.splitext(pdf_path)[0]}_partial_page_{page_num+1}.txt"
                with open(tmp_file_path, 'w', encoding='utf-8') as tmp_file:
                    tmp_file.write(f"Page {page_num+1}\n\n{page_text}")
                logger.debug(f"Saved partial text for page {page_num+1} to {tmp_file_path}")
                
                processed_pages += 1
            else:
                logger.error(f"Error on page {page_num+1}: {response.status_code}, {response.text}")
                failed_pages += 1
        
        except Exception as e:
            logger.error(f"Error processing page {page_num+1}: {str(e)}")
            failed_pages += 1
    
    # Close the PDF file
    pdf_file.close()
    doc.close()
    
    logger.info(f"OCR conversion completed: {processed_pages} pages processed, {failed_pages} pages failed")
    return all_text

def main():
    # Set up argument parser
    # 인수 파서 설정
    parser = argparse.ArgumentParser(description='Convert PDF or DOCX files to text using Naver Cloud CLOVA OCR.')
    parser.add_argument('--input', '-i', required=True, help='Path to the input file (PDF or DOCX)')
    parser.add_argument('--page_range', '-p', help='Page range to process (e.g. 1-3 for pages 1, 2, and 3)')
    parser.add_argument('--output', '-o', help='Path to the output text file (default: input filename with .txt extension)')
    parser.add_argument('--log_level', '-l', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level (default: INFO)')
    parser.add_argument('--log_file', '-f', default='pdf_ocr.log', help='Log file path (default: pdf_ocr.log)')
    parser.add_argument('--lang', '-la', default='ko', 
                        help='Language for OCR: ko (Korean), ja (Japanese), zh-TW (Chinese Traditional). Separate multiple languages with comma: ko,ja')
    
    args = parser.parse_args()
    
    # Configure logger with user-specified level
    # 사용자가 지정한 레벨로 로거 구성
    global logger
    log_level = getattr(logging, args.log_level)
    logger = setup_logger(args.log_file, log_level)
    
    # Determine input and output paths
    # 입력 및 출력 경로 결정
    input_path = args.input
    
    # Default output path if not specified
    # 지정되지 않은 경우 기본 출력 경로
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.splitext(input_path)[0] + '.txt'
        
    logger.info(f"Input file: {input_path}")
    logger.info(f"Output file: {output_path}")
    
    # Check file extension
    # 파일 확장자 확인
    file_ext = os.path.splitext(input_path)[1].lower()
    
    if file_ext == '.pdf':
        # Process PDF file
        # PDF 파일 처리
        logger.info("Processing PDF file")
        extracted_text = convert_pdf_to_text(input_path, args.page_range, args.lang)
        
        if extracted_text:
            # Write output to file
            # 파일에 출력 쓰기
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                logger.info(f"Successfully extracted text to {output_path}")
                print(f"Success: Text extracted to {output_path}")
                return 0
            except Exception as e:
                logger.error(f"Failed to write output file: {e}")
                print(f"Error: Failed to write output file: {e}")
                return 1
        else:
            logger.error("Text extraction failed")
            print("Error: Text extraction failed. Check the log for details.")
            return 1
    
    elif file_ext == '.docx':
        logger.error("DOCX support not implemented yet")
        print("Error: DOCX support not implemented yet")
        return 1
    
    else:
        logger.error(f"Unsupported file format: {file_ext}")
        print(f"Error: Unsupported file format: {file_ext}")
        print("Supported formats: .pdf, .docx")
        return 1

if __name__ == "__main__":
    sys.exit(main())
