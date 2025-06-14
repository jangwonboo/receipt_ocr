#!/usr/bin/env python3
"""
OCR Document Processing GUI
OCR 문서 처리 GUI

A PyQt6 application for processing images and PDFs with OCR and renaming files
based on the extracted information.
OCR로 이미지 및 PDF를 처리하고 추출된 정보를 기반으로 파일 이름을 변경하는 PyQt6 애플리케이션입니다.

This application provides a user-friendly interface to:
1. Select an input directory containing receipt/document images
2. Process all supported files with OCR
3. Save results as JSON files
4. Optionally rename the processed files based on OCR data

Usage:
사용법:
    python ocr_gui.py

Author: Claude
"""

import sys
import os
import glob
import json
import threading
import queue
import shutil
import time
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
import logging

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QProgressBar, QTextEdit,
    QFileDialog, QCheckBox, QGroupBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QScreen
from PyQt6 import uic

# Import Gemini OCR functionality
import gemini_ocr
# Import language resources
from language_resources import LanguageManager
import glob
from pathlib import Path

# Configure Logger
import gemini_ocr
logger = gemini_ocr.logger

class OcrWorker(QThread):
    """
    Worker thread for OCR processing
    OCR 처리를 위한 작업자 스레드
    """
    progress_signal = pyqtSignal(int, int)  # Current, Total
    result_signal = pyqtSignal(str)         # Status message
    complete_signal = pyqtSignal(bool)      # Success status

    def __init__(self, input_dir, output_dir, rename_files=True, force_process=False, lang_manager=None):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.rename_files = rename_files
        self.force_process = force_process
        self.is_running = True
        self.retry_delay = 2  # Initial retry delay in seconds
        self.lang = lang_manager or LanguageManager()
        
    def perform_ocr_with_retry(self, file_path, max_retries=5):
        """
        Perform OCR with retry logic for rate limiting
        속도 제한에 대한 재시도 로직으로 OCR 수행
        
        Args:
            file_path: Path object or string path to the file to process
            max_retries: Maximum number of retry attempts
            
        Returns:
            dict: Dictionary containing OCR results or None if processing failed
        """
        retries = 0
        file_path_obj = Path(file_path) if not isinstance(file_path, Path) else file_path
        
        while retries < max_retries and self.is_running:
            try:
                # Create a temporary directory for processing
                temp_dir = Path(tempfile.mkdtemp())
                try:
                    # Process the file using Gemini OCR
                    ocr_result = gemini_ocr.process_file(file_path_obj, temp_dir)
                    
                    # If we have a result, ensure it has the expected structure
                    if ocr_result and isinstance(ocr_result, dict):
                        # Ensure required fields are present
                        for field in ["date", "place", "amount", "currency"]:
                            if field not in ocr_result:
                                ocr_result[field] = None
                        
                        # Add OCR text to the result
                        ocr_result["ocr_text"] = json.dumps(ocr_result, ensure_ascii=False, indent=2)
                        
                        # Add missing fields list
                        missing_fields = [field for field in ["date", "place", "amount", "currency"] 
                                       if not ocr_result.get(field)]
                        ocr_result["missing_fields"] = missing_fields
                        
                        return ocr_result
                    return None
                finally:
                    # Clean up temporary directory
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
            except Exception as e:
                error_str = str(e)
                file_name = str(file_path_obj.name) if hasattr(file_path_obj, 'name') else str(file_path_obj)
                
                # Check if it's a rate limit error
                if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                    retries += 1
                    if retries >= max_retries:
                        self.result_signal.emit(self.lang.get_text("rate_limit_max"))
                        return None
                    
                    wait_time = self.retry_delay * (2 ** (retries - 1))  # Exponential backoff
                    self.result_signal.emit(self.lang.get_text("rate_limit_wait", wait_time, retries, max_retries))
                    
                    # Wait with checking for stop signal
                    for _ in range(wait_time * 10):  # Check 10 times per second
                        if not self.is_running:
                            return None
                        time.sleep(0.1)
                else:
                    # For other errors, log and return None
                    error_msg = f"{self.lang.get_text('error_processing')} {file_name}: {error_str}"
                    self.result_signal.emit(error_msg)
                    logger.error(f"Error processing {file_path_obj}: {error_str}")
                    logger.error(traceback.format_exc())
                    return None
                    return None
        
    def run(self):
        try:
            # Define supported file types
            supported_extensions = gemini_ocr.SUPPORTED_EXTENSIONS
            input_files = []
            
            # Find all files with supported extensions
            for ext in supported_extensions:
                # Search for both lowercase and uppercase extensions
                pattern_lower = os.path.join(self.input_dir, f"*{ext.lower()}")
                pattern_upper = os.path.join(self.input_dir, f"*{ext.upper()}")
                input_files.extend(glob.glob(pattern_lower))
                input_files.extend(glob.glob(pattern_upper))
            
            # Remove any duplicates while preserving order
            input_files = list(dict.fromkeys(input_files))
            
            if not input_files:
                self.result_signal.emit(self.lang.get_text("no_files_found"))
                self.complete_signal.emit(False)
                return
                
            self.result_signal.emit(self.lang.get_text("found_files", len(input_files)))
            total_files = len(input_files)
            processed = 0
            
            # Process each file
            for file_path in input_files:
                if not self.is_running:
                    self.result_signal.emit(self.lang.get_text("processing_stopped"))
                    self.complete_signal.emit(False)
                    return
                    
                filename = os.path.basename(file_path)
                base_name = os.path.splitext(filename)[0]
                
                # Set output file path
                output_path = os.path.join(self.output_dir, f"{base_name}.json")
                self.result_signal.emit(self.lang.get_text("processing_file", filename))
                
                # Check if output files already exist
                file_path_obj = Path(file_path)
                json_path = Path(self.output_dir) / f"{file_path_obj.stem}_extracted_info.json"
                if json_path.exists() and not self.force_process:
                    self.result_signal.emit(self.lang.get_text("skipping_file", filename))
                    processed += 1
                    self.progress_signal.emit(processed, total_files)
                    continue
                
                # Perform OCR using Gemini with retry logic
                result = self.perform_ocr_with_retry(file_path_obj)
                
                if not result:
                    self.result_signal.emit(
                        self.lang.get_text("extraction_failed", filename))
                    processed += 1
                    self.progress_signal.emit(processed, total_files)
                    continue
                
                # Save results to files
                try:
                    os.makedirs(self.output_dir, exist_ok=True)
                    
                    # Save OCR text
                    text_path = Path(self.output_dir) / f"{file_path_obj.stem}_ocr_output.txt"
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(result.get("ocr_text", ""))
                    
                    # Save extracted information
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    self.result_signal.emit(
                        self.lang.get_text("process_success", filename, text_path))
                except Exception as e:
                    self.result_signal.emit(
                        f"Error saving results for {filename}: {str(e)}")
                
                # Rename the file if requested
                if self.rename_files and result:
                    try:
                        # Generate new filename
                        new_filename = gemini_ocr.generate_filename_from_info(result, file_path_obj)
                        new_file_path = Path(self.output_dir) / new_filename
                        
                        # Check if destination exists and append a number if it does
                        counter = 1
                        original_stem = new_file_path.stem
                        while new_file_path.exists():
                            new_filename = f"{original_stem}_{counter}{new_file_path.suffix}"
                            new_file_path = new_file_path.with_name(new_filename)
                            counter += 1
                        
                        # Create output directory if it doesn't exist
                        os.makedirs(self.output_dir, exist_ok=True)
                        
                        # Copy the file to the output directory with the new name
                        shutil.copy2(file_path, new_file_path)
                        self.result_signal.emit(
                            self.lang.get_text("file_renamed", filename, new_file_path.name))
                    except Exception as e:
                        self.result_signal.emit(
                            self.lang.get_text("rename_error", filename, str(e)))
                
                processed += 1
                self.progress_signal.emit(processed, total_files)
                
                # Add a small delay between files to avoid rate limiting
                self.result_signal.emit(self.lang.get_text("waiting_next"))
                time.sleep(1)
                
            # Final status update
            if self.is_running:
                self.result_signal.emit(
                    self.lang.get_text("ocr_complete_count", processed))
                self.complete_signal.emit(True)
            
        except Exception as e:
            self.result_signal.emit(self.lang.get_text("ocr_error", str(e)))
            self.complete_signal.emit(False)
    
    def stop(self):
        self.is_running = False





class OcrApp(QMainWindow):
    """
    Main OCR application window
    OCR 애플리케이션 메인 창
    """
    def __init__(self):
        super().__init__()
        
        self.input_dir = ""
        self.output_dir = ""
        self.worker = None
        self.rename_worker = None
        
        # Initialize language manager with default language (English)
        self.lang_manager = LanguageManager("en")
        
        # Load UI from file
        self.loadUI()
        self.connectSignals()
        
        # Set window size to 1/5 of screen width and 1/3 of screen height
        self.adjustWindowSize()
        
        # Initial log message
        self.logMessage(self.lang_manager.get_text("app_started"))
        self.logMessage(self.lang_manager.get_text("rate_limit_note"))
        self.logMessage(self.lang_manager.get_text("rate_limit_pause"))
    
    def adjustWindowSize(self):
        """
        Adjust window size to 1/5 of screen width and 1/3 of screen height
        화면 너비의 1/5, 높이의 1/3로 창 크기 조정
        """
        # Get the available screen geometry
        screen_rect = QApplication.primaryScreen().availableGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        
        # Calculate target size: 1/5 of width, 1/3 of height
        target_width = int(screen_width / 3)
        target_height = int(screen_height / 2)
        
        # Set minimum size to ensure UI elements fit
        min_width = min(700, target_width)
        min_height = min(500, target_height)
        self.setMinimumSize(min_width, min_height)
        
        # Resize the window
        self.resize(target_width, target_height)
        
        # Center the window on the screen
        frame_geometry = self.frameGeometry()
        center_point = screen_rect.center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def loadUI(self):
        """
        Load UI from .ui file
        .ui 파일에서 UI 로드
        """
        # Load the UI file
        uic.loadUi('ocr_gui.ui', self)
        
        # Populate language combo box
        self.lang_combo.clear()
        for lang_code, lang_name in self.lang_manager.get_languages().items():
            self.lang_combo.addItem(lang_name, lang_code)
    
    def connectSignals(self):
        """
        Connect signals to slots
        시그널을 슬롯에 연결
        """
        # Connect UI elements to their functions
        self.browse_btn.clicked.connect(self.browseInputDir)
        self.output_browse_btn.clicked.connect(self.browseOutputDir)
        self.process_btn.clicked.connect(self.startProcessing)
        self.stop_btn.clicked.connect(self.stopProcessing)
        self.quit_btn.clicked.connect(self.close)
        self.lang_combo.currentIndexChanged.connect(self.changeLanguage)
    
    def changeLanguage(self):
        """
        Change the application language
        애플리케이션 언어 변경
        """
        lang_code = self.lang_combo.currentData()
        if self.lang_manager.set_language(lang_code):
            # Update UI text
            self.setWindowTitle(self.lang_manager.get_text("window_title"))
            
            # Update input group
            self.input_group.setTitle(self.lang_manager.get_text("input_group"))
            self.input_label.setText(self.lang_manager.get_text("input_label"))
            self.browse_btn.setText(self.lang_manager.get_text("browse_btn"))
            
            # Update output group
            self.output_group.setTitle(self.lang_manager.get_text("output_group"))
            self.output_label.setText(self.lang_manager.get_text("output_label"))
            self.output_browse_btn.setText(self.lang_manager.get_text("output_browse_btn"))
            
            # Update OCR options
            self.options_group.setTitle(self.lang_manager.get_text("options_group"))
            self.rate_limit_label.setText(self.lang_manager.get_text("rate_limit_warning"))
            
            # Update rename option
            self.rename_group.setTitle(self.lang_manager.get_text("rename_group"))
            self.rename_check.setText(self.lang_manager.get_text("rename_check"))
            
            # Update progress group
            self.progress_group.setTitle(self.lang_manager.get_text("progress_group"))
            
            # Update log group
            self.log_group.setTitle(self.lang_manager.get_text("log_group"))
            
            # Update control buttons
            self.process_btn.setText(self.lang_manager.get_text("process_btn"))
            self.stop_btn.setText(self.lang_manager.get_text("stop_btn"))
            self.quit_btn.setText(self.lang_manager.get_text("quit_btn"))
            
            # Log the language change
            self.logMessage(f"Language changed to {self.lang_combo.currentText()}")
    
    def browseInputDir(self):
        """
        Open file dialog to select input directory
        입력 디렉토리를 선택하는 파일 대화 상자 열기
        """
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if dir_path:
            self.input_dir = dir_path
            self.input_path.setText(dir_path)
            self.logMessage(self.lang_manager.get_text("input_dir_set", dir_path))
            
            # If output directory not set, default to same as input
            if not self.output_dir:
                self.output_dir = dir_path
                self.output_path.setText(dir_path)
                self.logMessage(self.lang_manager.get_text("output_dir_set", dir_path))
    
    def browseOutputDir(self):
        """
        Open file dialog to select output directory
        출력 디렉토리를 선택하는 파일 대화 상자 열기
        """
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.output_path.setText(dir_path)
            self.logMessage(self.lang_manager.get_text("output_dir_set", dir_path))
    
    def logMessage(self, message):
        """
        Add a message to the log display
        로그 표시에 메시지 추가
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to the bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def startProcessing(self):
        """
        Start the OCR processing
        OCR 처리 시작
        """
        if not self.input_dir:
            QMessageBox.warning(self, "Error", self.lang_manager.get_text("error_no_input"))
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "Error", self.lang_manager.get_text("error_no_output"))
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logMessage(self.lang_manager.get_text("output_dir_created", self.output_dir))
            
        # Disable controls during processing
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        
        self.logMessage(self.lang_manager.get_text("starting_ocr"))
        
        # Create and start worker thread
        self.worker = OcrWorker(
            self.input_dir, 
            self.output_dir,
            rename_files=self.rename_check.isChecked(),
            force_process=not self.skip_existing_check.isChecked(),
            lang_manager=self.lang_manager
        )
        
        self.worker.progress_signal.connect(self.updateProgress)
        self.worker.result_signal.connect(self.logMessage)
        self.worker.complete_signal.connect(self.processingComplete)
        
        self.worker.start()
    
    def stopProcessing(self):
        """
        Stop the OCR processing
        OCR 처리 중지
        """
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.logMessage(self.lang_manager.get_text("stopping_ocr"))
            self.stop_btn.setEnabled(False)
    
    @pyqtSlot(int, int)
    def updateProgress(self, current, total):
        """
        Update progress bar
        진행 표시줄 업데이트
        """
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)
    
    @pyqtSlot(bool)
    def processingComplete(self, success):
        """
        Handle OCR processing completion
        OCR 처리 완료 처리
        """
        self.progress_bar.setValue(100 if success else 0)
        
        # Re-enable controls
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.output_browse_btn.setEnabled(True)
        
        if success:
            self.logMessage(self.lang_manager.get_text("ocr_complete"))
            # 각 파일이 처리될 때마다 이름 변경이 이미 수행되므로 여기서는 추가 작업이 필요 없음
        else:
            self.logMessage(self.lang_manager.get_text("ocr_failed"))
    



def main():
    # Fix for macOS NSOpenPanel warning
    if sys.platform == 'darwin':
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
        # Additional macOS specific environment variables
        os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
        # Suppress NSOpenPanel warning
        import logging
        logging.getLogger("objc").setLevel(logging.ERROR)
        
    # Handle Qt deprecated methods
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    app = QApplication(sys.argv)
    
    # Create and show the app
    window = OcrApp()
    window.show()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("Application terminated by user")
        sys.exit(0)


if __name__ == "__main__":
    main()