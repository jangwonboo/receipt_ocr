#!/usr/bin/env python3
# Code to extract business card information using Naver Cloud CLOVA OCR API
# 네이버 클라우드 CLOVA OCR API를 사용하여 명함 정보를 추출하는 코드

import argparse
import sys
import os
import json
import logging
from logging.handlers import RotatingFileHandler
import glob
import tempfile
import shutil

# Import from utils
# utils에서 가져오기
from utils import setup_logger, check_file_validity
from ocr import make_ocr_request, process_pdf_for_ocr

# Initialize logger
# 로거 초기화
logger = setup_logger()

def extract_namecard(image_path, use_alt_url=False):
    """
    Extract name card information using Naver Cloud CLOVA OCR API
    네이버 클라우드 CLOVA OCR API를 사용하여 명함 정보를 추출합니다
    
    Args:
        image_path (str): Path to name card image file (jpg, jpeg, png, pdf, tif, tiff)
                         명함 이미지 파일 경로 (jpg, jpeg, png, pdf, tif, tiff)
        use_alt_url (bool): Whether to use the alternative URL pattern from documentation
                          문서의 대체 URL 패턴을 사용할지 여부
    
    Returns:
        dict: Extracted name card information
              추출된 명함 정보
    """
    logger.info(f"Starting name card extraction for {image_path}")
    
    # Check file validity
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
    is_valid, file_format, error_msg = check_file_validity(image_path, allowed_extensions)
    
    if not is_valid:
        logger.error(error_msg)
        return {}
    
    # Make OCR API request
    # The correct endpoint for name card according to documentation
    result = make_ocr_request("name-card", image_path, file_format, use_alt_url=use_alt_url)
    
    if not result or not result.get('images'):
        logger.error("Name card extraction failed. Empty or invalid API response.")
        return {}
    
    # Extract name card fields
    try:
        namecard_data = {}
        namecard_results = result.get('images', [{}])[0].get('nameCard', {})
        
        # Get basic info
        if 'result' in namecard_results:
            namecard_data['name'] = namecard_results['result'].get('name', {}).get('text', '')
            namecard_data['company'] = namecard_results['result'].get('company', {}).get('text', '')
            namecard_data['department'] = namecard_results['result'].get('department', {}).get('text', '')
            namecard_data['position'] = namecard_results['result'].get('position', {}).get('text', '')
            
            # Get contact info
            namecard_data['mobile'] = ''
            namecard_data['tel'] = ''
            namecard_data['fax'] = ''
            namecard_data['email'] = ''
            namecard_data['homepage'] = ''
            namecard_data['address'] = ''
            
            # Process contact info
            for contact in namecard_results['result'].get('contact', []):
                if contact.get('type') == 'mobile':
                    namecard_data['mobile'] = contact.get('text', '')
                elif contact.get('type') == 'tel':
                    namecard_data['tel'] = contact.get('text', '')
                elif contact.get('type') == 'fax':
                    namecard_data['fax'] = contact.get('text', '')
                elif contact.get('type') == 'email':
                    namecard_data['email'] = contact.get('text', '')
                elif contact.get('type') == 'homepage':
                    namecard_data['homepage'] = contact.get('text', '')
                elif contact.get('type') == 'address':
                    namecard_data['address'] = contact.get('text', '')
        
        return namecard_data
    except Exception as e:
        logger.error(f"Error parsing name card data: {str(e)}")
        return {}

def convert_namecard_to_markdown(namecard_data):
    """
    Convert name card data to a well-formatted markdown document
    명함 데이터를 잘 포맷된 마크다운 문서로 변환합니다
    
    Args:
        namecard_data (dict): Extracted name card information
                             추출된 명함 정보
        
    Returns:
        str: Markdown formatted name card
             마크다운 형식의 명함
    """
    if not namecard_data:
        return "No name card data available."
    
    # Initialize markdown content
    md = []
    
    # Add name card header
    name = namecard_data.get("name", "")
    company = namecard_data.get("company", "")
    
    md.append(f"# {name}")
    if company:
        md.append(f"## {company}")
    
    md.append("")
    
    # Add position if available
    if namecard_data.get("position"):
        md.append(f"**Position:** {namecard_data['position']}")
    
    # Add Japanese-specific fields if available
    if namecard_data.get("nameFurigana"):
        md.append(f"**Name (Furigana):** {namecard_data['nameFurigana']}")
    
    md.append("")
    md.append("## Contact Information")
    
    # Add contact details
    if namecard_data.get("mobile"):
        md.append(f"**Mobile:** {namecard_data['mobile']}")
    
    if namecard_data.get("tel"):
        md.append(f"**Tel:** {namecard_data['tel']}")
    
    if namecard_data.get("fax"):
        md.append(f"**Fax:** {namecard_data['fax']}")
    
    if namecard_data.get("email"):
        md.append(f"**Email:** {namecard_data['email']}")
    
    md.append("")
    
    # Add address if available
    if namecard_data.get("address"):
        md.append("## Address")
        md.append(namecard_data["address"])
    
    # Join all lines with newlines
    return "\n".join(md)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract business card information using Naver Cloud CLOVA OCR.')
    parser.add_argument('--input', '-i', help='Path to the input file')
    parser.add_argument('--input-dir', '-id', help='Path to the input directory containing files to process')
    parser.add_argument('--output', '-o', help='Path to the output file (default: input filename with appropriate extension)')
    parser.add_argument('--output-dir', '-od', help='Path to the output directory for processed files')
    parser.add_argument('--log_level', '-l', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set logging level (default: INFO)')
    parser.add_argument('--log_file', '-f', default='namecard_ocr.log', help='Log file path (default: namecard_ocr.log)')
    parser.add_argument('--format', '-fmt', default='json', choices=['json', 'text', 'markdown'],
                        help='Output format: json, text, or markdown (default: json)')
    parser.add_argument('--all_pages', '-a', action='store_true', help='Process all pages of a PDF file (default: only first page)')
    
    args = parser.parse_args()
    
    # Configure logger
    global logger
    log_level = getattr(logging, args.log_level)
    logger = setup_logger(args.log_file, log_level)
    
    logger.info("Starting name card OCR with Naver Cloud CLOVA OCR")
    
    # Check if either input file or input directory is provided
    if not args.input and not args.input_dir:
        logger.error("Either input file or input directory is required")
        print("Error: Either input file (--input) or input directory (--input-dir) is required.")
        return 1
    
    # Check output directory if input directory is provided
    if args.input_dir and not args.output_dir:
        logger.error("Output directory is required when processing a directory of files")
        print("Error: Output directory (--output-dir) is required when processing a directory of files.")
        return 1
    
    # Create output directory if it doesn't exist
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info(f"Created output directory: {args.output_dir}")
    
    # Process a single file
    if args.input:
        # Set output path if not specified
        if not args.output:
            if args.format == 'json':
                output_path = os.path.splitext(args.input)[0] + '.json'
            elif args.format == 'markdown':
                output_path = os.path.splitext(args.input)[0] + '.md'
            else:
                output_path = os.path.splitext(args.input)[0] + '.txt'
        else:
            output_path = args.output
            
        logger.info(f"Output will be saved to: {output_path}")
        
        # Process file based on type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
        is_valid, file_format, error_msg = check_file_validity(args.input, allowed_extensions)
        
        if not is_valid:
            logger.error(error_msg)
            print(f"Error: {error_msg}")
            return 1
        
        try:
            # Check if it's a PDF file with all pages option
            if file_format == 'pdf' and args.all_pages:
                # Process all pages of the PDF
                results = process_pdf_for_ocr(args.input, 'namecard')
                if not results:
                    logger.error("Name card extraction failed. Check the log for details.")
                    print("Error: Name card extraction failed. Check the log for details.")
                    return 1
                    
                # For multiple pages, we combine the results
                combined_result = results[0] if results else {}
                if len(results) > 1:
                    # Indicate that this is a multi-page result
                    combined_result['multi_page'] = True
                    combined_result['page_count'] = len(results)
                    combined_result['pages'] = results
                
                result = combined_result
            else:
                # Process a single image or the first page of a PDF
                result = extract_namecard(args.input)
            
            if not result:
                logger.error("Name card extraction failed. Check the log for details.")
                print("Error: Name card extraction failed. Check the log for details.")
                return 1
                
            # Convert to requested format
            if args.format == 'markdown':
                result_content = convert_namecard_to_markdown(result)
            elif args.format == 'text':
                # Simple text representation of the namecard
                result_content = str(result)
            else:  # json
                result_content = result
                
            # Write output to file
            with open(output_path, 'w', encoding='utf-8') as f:
                if args.format == 'json':
                    json.dump(result_content, f, ensure_ascii=False, indent=2)
                else:
                    f.write(result_content)
            
            logger.info(f"Processing complete. Output saved to {output_path}")
            print(f"Success: Processing complete. Output saved to {output_path}")
            return 0
            
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}")
            print(f"Error: An unexpected error occurred: {str(e)}")
            return 1
    
    # Process directory
    input_dir = args.input_dir
    output_dir = args.output_dir
    
    # Find all files with supported extensions
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
    success_count = 0
    failure_count = 0
    
    for file_path in input_files:
        filename = os.path.basename(file_path)
        base_name = os.path.splitext(filename)[0]
        
        # Set output file path
        if args.format == 'json':
            output_file = f"{base_name}.json"
        elif args.format == 'markdown':
            output_file = f"{base_name}.md"
        else:
            output_file = f"{base_name}.txt"
            
        output_path = os.path.join(output_dir, output_file)
        
        logger.info(f"Processing file {success_count + failure_count + 1}/{len(input_files)}: {filename}")
        print(f"Processing file {success_count + failure_count + 1}/{len(input_files)}: {filename}")
        
        # Process the file
        try:
            # Check if it's a PDF file with all pages option
            is_valid, file_format, _ = check_file_validity(file_path, supported_extensions)
            
            if is_valid:
                if file_format == 'pdf' and args.all_pages:
                    # Process all pages of the PDF
                    results = process_pdf_for_ocr(file_path, 'namecard')
                    if results:
                        combined_result = results[0] if results else {}
                        if len(results) > 1:
                            combined_result['multi_page'] = True
                            combined_result['page_count'] = len(results)
                            combined_result['pages'] = results
                        
                        result = combined_result
                    else:
                        result = None
                else:
                    # Process a single image or the first page of a PDF
                    result = extract_namecard(file_path)
                
                if result:
                    # Convert to requested format
                    if args.format == 'markdown':
                        result_content = convert_namecard_to_markdown(result)
                    elif args.format == 'text':
                        result_content = str(result)
                    else:  # json
                        result_content = result
                        
                    # Write output to file
                    with open(output_path, 'w', encoding='utf-8') as f:
                        if args.format == 'json':
                            json.dump(result_content, f, ensure_ascii=False, indent=2)
                        else:
                            f.write(result_content)
                    
                    success_count += 1
                else:
                    logger.error(f"Failed to extract data from {filename}")
                    failure_count += 1
            else:
                logger.error(f"Invalid file: {filename}")
                failure_count += 1
                
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            print(f"Error processing {filename}: {str(e)}")
            failure_count += 1
    
    # Print summary
    logger.info(f"Processing complete: {success_count} successful, {failure_count} failed")
    print(f"Processing complete: {success_count} successful, {failure_count} failed")
    
    if failure_count > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
