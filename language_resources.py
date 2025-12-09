#!/usr/bin/env python3
"""
Language Resources for OCR GUI
OCR GUI용 언어 리소스

This module provides multilingual support for the OCR GUI application.
이 모듈은 OCR GUI 애플리케이션에 다국어 지원을 제공합니다.
"""

# Available languages
LANGUAGES = {
    "en": "English",
    "ko": "한국어"
}

# Text resources for different languages
RESOURCES = {
    "en": {
        # Window title
        "window_title": "OCR Document Processor",
        
        # Input directory section
        "input_group": "Input Directory",
        "input_label": "Select directory containing images/PDFs:",
        "browse_btn": "Browse...",
        
        # Temp directory section
        "temp_group": "Temp Directory",
        "temp_label": "Select directory for JSON output:",
        "temp_browse_btn": "Browse...",
        
        # OCR Options section
        "options_group": "OCR Options",
        "rate_limit_warning": "⚠️ Google Gemini API has rate limits. Processing will pause automatically if limits are reached.",
        
        # Rename options section
        "rename_group": "Rename Options",
        "rename_check": "Rename files after OCR processing",
        
        # Progress section
        "progress_group": "Progress",
        
        # Log section
        "log_group": "Log",
        
        # Control buttons
        "process_btn": "Start Processing",
        "stop_btn": "Stop",
        "quit_btn": "Quit",
        
        # Messages
        "app_started": "Application started. Select an input directory to begin.",
        "rate_limit_note": "Note: This application uses Google Gemini API which has rate limits.",
        "rate_limit_pause": "If rate limits are reached, processing will pause automatically.",
        "checking_api": "Checking Google Gemini API configuration...",
        "api_key_missing": "❌ GOOGLE_API_KEY not set. Please set it in the .env file.",
        "api_key_found": "✓ Google Gemini API key found! Ready to process documents.",
        "api_check_error": "❌ Error checking Google Gemini API configuration: {0}",
        "input_dir_set": "Input directory set to: {0}",
        "base_dir_set": "Base directory set to: {0}",
        "base_dir_created": "Created base directory: {0}",
        "error_no_input": "Please select an input directory.",
        "error_no_temp_dir": "Please select a temp directory.",
        "starting_ocr": "Starting OCR processing...",
        "stopping_ocr": "Stopping OCR processing...",
        "ocr_complete": "OCR processing completed successfully!",
        "ocr_failed": "OCR processing did not complete successfully.",
        "starting_rename": "Starting file renaming process...",
        "rename_complete": "File renaming completed successfully!",
        "rename_failed": "File renaming did not complete successfully.",
        "no_json_files": "No JSON files found to process for renaming.",
        "file_renamed": "File {0} renamed to {1} and saved to output directory.",
        "rename_error": "Error renaming file {0}: {1}",
        
        # Processing messages
        "no_files_found": "No supported files found in the selected directory.",
        "found_files": "Found {0} files to process.",
        "processing_stopped": "Processing stopped by user.",
        "processing_file": "Processing: {0}",
        "unsupported_format": "Error: Unsupported file format {0}",
        "extraction_failed": "Failed to extract data from {0}",
        "structured_data_failed": "Failed to extract structured data from {0}",
        "rate_limit_max": "Maximum retries reached. Rate limit exceeded.",
        "rate_limit_wait": "Rate limit reached. Waiting {0} seconds before retry {1}/{2}...",
        "rate_limit_extract": "Rate limit reached during info extraction. Using OCR text only.",
        "extract_error": "Error extracting info: {0}",
        "process_success": "Successfully processed {0}. Saved to {1}",
        "waiting_next": "Waiting 1 second before processing next file to avoid rate limiting...",
        "process_error": "Error processing {0}: {1}",
        "ocr_complete_count": "OCR processing complete. Processed {0} files.",
        "ocr_error": "Error in OCR processing: {0}",
        "skipping_file": "Skipping {0} - OCR output already exists"
    },
    
    "ko": {
        # Window title
        "window_title": "OCR 문서 처리기",
        
        # Input directory section
        "input_group": "입력 디렉토리",
        "input_label": "이미지/PDF가 포함된 디렉토리 선택:",
        "browse_btn": "찾아보기...",
        
        # Temp directory section
        "temp_group": "임시 디렉토리",
        "temp_label": "JSON 출력을 위한 디렉토리 선택:",
        "temp_browse_btn": "찾아보기...",
        
        # OCR Options section
        "options_group": "OCR 옵션",
        "rate_limit_warning": "⚠️ Google Gemini API에는 속도 제한이 있습니다. 제한에 도달하면 처리가 자동으로 일시 중지됩니다.",
        
        # Rename options section
        "rename_group": "이름 변경 옵션",
        "rename_check": "OCR 처리 후 파일 이름 변경",
        
        # Progress section
        "progress_group": "진행 상황",
        
        # Log section
        "log_group": "로그",
        
        # Control buttons
        "process_btn": "처리 시작",
        "stop_btn": "중지",
        "quit_btn": "종료",
        
        # Messages
        "app_started": "애플리케이션이 시작되었습니다. 시작하려면 입력 디렉토리를 선택하세요.",
        "rate_limit_note": "참고: 이 애플리케이션은 속도 제한이 있는 Google Gemini API를 사용합니다.",
        "rate_limit_pause": "속도 제한에 도달하면 처리가 자동으로 일시 중지됩니다.",
        "checking_api": "Google Gemini API 구성을 확인 중...",
        "api_key_missing": "❌ GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일에서 설정하세요.",
        "api_key_found": "✓ Google Gemini API 키를 찾았습니다! 문서 처리 준비 완료.",
        "api_check_error": "❌ Google Gemini API 구성 확인 중 오류: {0}",
        "input_dir_set": "입력 디렉토리 설정: {0}",
        "base_dir_set": "기본 디렉토리 설정: {0}",
        "base_dir_created": "기본 디렉토리 생성: {0}",
        "error_no_input": "입력 디렉토리를 선택하세요.",
        "error_no_temp_dir": "임시 디렉토리를 선택하세요.",
        "starting_ocr": "OCR 처리 시작...",
        "stopping_ocr": "OCR 처리 중지 중...",
        "ocr_complete": "OCR 처리가 성공적으로 완료되었습니다!",
        "ocr_failed": "OCR 처리가 성공적으로 완료되지 않았습니다.",
        "starting_rename": "파일 이름 변경 프로세스 시작 중...",
        "rename_complete": "파일 이름 변경이 성공적으로 완료되었습니다!",
        "rename_failed": "파일 이름 변경이 성공적으로 완료되지 않았습니다.",
        "no_json_files": "이름 변경을 위한 JSON 파일을 찾을 수 없습니다.",
        "file_renamed": "파일 {0}이(가) {1}(으)로 이름 변경되어 출력 디렉토리에 저장되었습니다.",
        "rename_error": "파일 {0} 이름 변경 오류: {1}",
        
        # Processing messages
        "no_files_found": "선택한 디렉토리에서 지원되는 파일을 찾을 수 없습니다.",
        "found_files": "{0}개의 처리할 파일을 찾았습니다.",
        "processing_stopped": "사용자에 의해 처리가 중지되었습니다.",
        "processing_file": "처리 중: {0}",
        "unsupported_format": "오류: 지원되지 않는 파일 형식 {0}",
        "extraction_failed": "{0}에서 데이터를 추출하지 못했습니다",
        "structured_data_failed": "{0}에서 구조화된 데이터를 추출하지 못했습니다",
        "rate_limit_max": "최대 재시도 횟수에 도달했습니다. 속도 제한 초과.",
        "rate_limit_wait": "속도 제한에 도달했습니다. {0}초 후 재시도 {1}/{2}...",
        "rate_limit_extract": "정보 추출 중 속도 제한에 도달했습니다. OCR 텍스트만 사용합니다.",
        "extract_error": "정보 추출 오류: {0}",
        "process_success": "{0} 처리 성공. {1}에 저장됨",
        "waiting_next": "속도 제한을 피하기 위해 다음 파일 처리 전 1초 대기 중...",
        "process_error": "{0} 처리 오류: {1}",
        "ocr_complete_count": "OCR 처리 완료. {0}개 파일 처리됨.",
        "ocr_error": "OCR 처리 중 오류: {0}"
    }
}

class LanguageManager:
    """
    Manages language resources for the application
    애플리케이션의 언어 리소스를 관리합니다
    """
    def __init__(self, default_language="en"):
        self.current_language = default_language
        if self.current_language not in RESOURCES:
            self.current_language = "en"  # Fallback to English
    
    def set_language(self, language_code):
        """Set the current language"""
        if language_code in RESOURCES:
            self.current_language = language_code
            return True
        return False
    
    def get_text(self, key, *args):
        """
        Get text for the specified key in the current language
        If args are provided, format the text with the arguments
        """
        if key in RESOURCES[self.current_language]:
            text = RESOURCES[self.current_language][key]
            if args:
                try:
                    return text.format(*args)
                except:
                    return text
            return text
        
        # Fallback to English if key not found in current language
        if key in RESOURCES["en"]:
            text = RESOURCES["en"][key]
            if args:
                try:
                    return text.format(*args)
                except:
                    return text
            return text
        
        # Return the key itself if not found in any language
        return key
    
    def get_languages(self):
        """Get available languages"""
        return LANGUAGES 