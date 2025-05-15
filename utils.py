#!/usr/bin/env python3
"""
Utility Functions for OCR Processing
OCR 처리를 위한 유틸리티 함수

This module provides common utility functions used by the OCR processing scripts.
It includes functions for setting up logging, file validation, and other common operations
needed across multiple OCR-related scripts.

이 모듈은 OCR 처리 스크립트에서 사용되는 공통 유틸리티 함수를 제공합니다.
로깅 설정, 파일 유효성 검사 및 여러 OCR 관련 스크립트에서 필요한 기타 공통 작업을 위한 
함수가 포함되어 있습니다.

Features:
기능:
- Configurable logging with file rotation and console output
  파일 회전 및 콘솔 출력이 포함된 구성 가능한 로깅
- File validation (extension, size, existence)
  파일 유효성 검사 (확장자, 크기, 존재)
- File format conversion for API compatibility
  API 호환성을 위한 파일 형식 변환

This module serves as a shared library for the OCR processing scripts,
ensuring consistency in logging, file handling, and common operations.

이 모듈은 OCR 처리 스크립트의 공유 라이브러리 역할을 하여 로깅, 파일 처리 및 
공통 작업의 일관성을 보장합니다.

Author: Claude
Date: May 15, 2025
"""

# Utility functions for OCR processing
# OCR 처리를 위한 유틸리티 함수들

import logging
from logging.handlers import RotatingFileHandler
import os
import os.path

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


def check_file_validity(file_path, allowed_extensions=None):
    """
    Check if file exists and has valid size and extension
    파일이 존재하고 유효한 크기와 확장자를 가지고 있는지 확인합니다
    
    Args:
        file_path (str): Path to the file
                        파일 경로
        allowed_extensions (list): List of allowed file extensions
                                  허용된 파일 확장자 목록
    
    Returns:
        tuple: (is_valid, file_format, error_message)
               (유효성 여부, 파일 형식, 오류 메시지)
    """
    # Check if file exists
    # 파일이 존재하는지 확인
    if not os.path.exists(file_path):
        return False, None, f"File {file_path} does not exist"
    
    # Check file extension
    # 파일 확장자 확인
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if allowed_extensions and file_ext not in allowed_extensions:
        return False, None, f"Unsupported file format: {file_ext}"
    
    # Determine file format for API
    # API용 파일 형식 결정
    file_format = None
    if file_ext in ['.jpg', '.jpeg']:
        file_format = 'jpg'
    elif file_ext == '.png':
        file_format = 'png'
    elif file_ext == '.pdf':
        file_format = 'pdf'
    elif file_ext in ['.tif', '.tiff']:
        file_format = 'tiff'
    
    # Check file size - API limit is 50MB
    # 파일 크기 확인 - API 제한은 50MB
    MAX_FILE_SIZE_MB = 50
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, None, f"File size ({file_size_mb:.2f}MB) exceeds the {MAX_FILE_SIZE_MB}MB limit"
    
    return True, file_format, None