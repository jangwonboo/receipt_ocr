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
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QProgressBar, QTextEdit,
    QFileDialog, QCheckBox, QGroupBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot

# Import OCR functionality
import ocr
# Import renaming functionality
from rename_receipts import rename_receipt_files

# Configure Logger
logger = ocr.setup_logger()

class OcrWorker(QThread):
    """
    Worker thread for OCR processing
    OCR 처리를 위한 작업자 스레드
    """
    progress_signal = pyqtSignal(int, int)  # Current, Total
    result_signal = pyqtSignal(str)         # Status message
    complete_signal = pyqtSignal(bool)      # Success status

    def __init__(self, input_dir, output_dir, mode='receipt', process_all_pages=False):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.mode = mode
        self.process_all_pages = process_all_pages
        self.is_running = True
        
    def run(self):
        try:
            # Define supported file types
            supported_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
            input_files = []
            
            # Find all files with supported extensions
            for ext in supported_extensions:
                input_files.extend(glob.glob(os.path.join(self.input_dir, f"*{ext}")))
                input_files.extend(glob.glob(os.path.join(self.input_dir, f"*{ext.upper()}")))
            
            if not input_files:
                self.result_signal.emit("No supported files found in the selected directory.")
                self.complete_signal.emit(False)
                return
                
            self.result_signal.emit(f"Found {len(input_files)} files to process.")
            total_files = len(input_files)
            processed = 0
            
            # Process each file
            for file_path in input_files:
                if not self.is_running:
                    self.result_signal.emit("Processing stopped by user.")
                    self.complete_signal.emit(False)
                    return
                    
                filename = os.path.basename(file_path)
                base_name = os.path.splitext(filename)[0]
                
                # Set output file path
                output_path = os.path.join(self.output_dir, f"{base_name}.json")
                
                self.result_signal.emit(f"Processing: {filename}")
                
                # Check file validity
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.tif', '.tiff']
                is_valid, file_format, error_msg = ocr.check_file_validity(file_path, allowed_extensions)
                
                if not is_valid:
                    self.result_signal.emit(f"Error: {error_msg}")
                    processed += 1
                    self.progress_signal.emit(processed, total_files)
                    continue
                
                try:
                    # Process based on file type and mode
                    if file_format == 'pdf' and self.process_all_pages:
                        # Process all pages
                        if self.mode == 'receipt':
                            results = ocr.process_pdf_for_ocr(file_path, 'receipt')
                            if results:
                                # Combine results if needed
                                combined_result = results[0] if results else {}
                                if len(results) > 1:
                                    combined_result['multi_page'] = True
                                    combined_result['page_count'] = len(results)
                                    combined_result['pages'] = results
                                
                                result = combined_result
                            else:
                                result = {}
                        else:  # General OCR
                            results = ocr.process_pdf_for_ocr(file_path, 'general')
                            result = {"pages": results, "multi_page": True, "page_count": len(results)}
                            
                    else:
                        # Process single image or first page
                        if self.mode == 'receipt':
                            result = ocr.extract_receipt(file_path)
                        else:  # General OCR
                            result = ocr.perform_general_ocr(file_path)
                    
                    # Save result to JSON file
                    if result:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        self.result_signal.emit(f"Successfully processed {filename}. Saved to {os.path.basename(output_path)}")
                    else:
                        self.result_signal.emit(f"Failed to extract data from {filename}")
                
                except Exception as e:
                    self.result_signal.emit(f"Error processing {filename}: {str(e)}")
                
                # Update progress
                processed += 1
                self.progress_signal.emit(processed, total_files)
            
            self.result_signal.emit(f"OCR processing complete. Processed {processed} files.")
            self.complete_signal.emit(True)
            
        except Exception as e:
            self.result_signal.emit(f"Error in OCR processing: {str(e)}")
            self.complete_signal.emit(False)
    
    def stop(self):
        self.is_running = False


class RenameWorker(QThread):
    """
    Worker thread for renaming files
    파일 이름 변경을 위한 작업자 스레드
    """
    progress_signal = pyqtSignal(str)      # Status message
    complete_signal = pyqtSignal(bool)     # Success status

    def __init__(self, json_dir, source_dir=None):
        super().__init__()
        self.json_dir = json_dir
        self.source_dir = source_dir if source_dir else json_dir
        
    def run(self):
        try:
            self.progress_signal.emit("Starting file renaming process...")
            rename_receipt_files(self.json_dir, self.source_dir)
            self.progress_signal.emit("File renaming complete!")
            self.complete_signal.emit(True)
        except Exception as e:
            self.progress_signal.emit(f"Error in renaming process: {str(e)}")
            self.complete_signal.emit(False)


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
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("OCR Document Processor")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Input directory selection
        input_group = QGroupBox("Input Directory")
        input_layout = QHBoxLayout()
        
        self.input_label = QLabel("Select directory containing images/PDFs:")
        self.input_path = QLineEdit()
        self.input_path.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browseInputDir)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.browse_btn)
        input_group.setLayout(input_layout)
        
        # Output directory selection
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        
        self.output_label = QLabel("Select directory for JSON output:")
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self.browseOutputDir)
        
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.output_browse_btn)
        output_group.setLayout(output_layout)
        
        # OCR Options
        options_group = QGroupBox("OCR Options")
        options_layout = QHBoxLayout()
        
        self.mode_label = QLabel("OCR Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Receipt", "Text (General)"])
        
        self.all_pages_check = QCheckBox("Process all pages in PDFs")
        self.all_pages_check.setChecked(True)
        
        options_layout.addWidget(self.mode_label)
        options_layout.addWidget(self.mode_combo)
        options_layout.addWidget(self.all_pages_check)
        options_group.setLayout(options_layout)
        
        # Rename Option
        rename_group = QGroupBox("Rename Options")
        rename_layout = QHBoxLayout()
        
        self.rename_check = QCheckBox("Rename files after OCR processing")
        self.rename_check.setChecked(True)
        
        rename_layout.addWidget(self.rename_check)
        rename_group.setLayout(rename_layout)
        
        # Progress bar
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        
        # Log output
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.clicked.connect(self.startProcessing)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stopProcessing)
        self.stop_btn.setEnabled(False)
        
        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.quit_btn)
        
        # Add all widgets to main layout
        main_layout.addWidget(input_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(rename_group)
        main_layout.addWidget(progress_group)
        main_layout.addWidget(log_group)
        main_layout.addLayout(button_layout)
        
        # Set the main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Initial log message
        self.logMessage("Application started. Select an input directory to begin.")
        
        # Check connectivity
        self.checkOcrConnectivity()
    
    def checkOcrConnectivity(self):
        """
        Check connectivity to the OCR API on startup
        시작 시 OCR API에 대한 연결 확인
        """
        self.logMessage("Checking OCR API connectivity...")
        
        # Run the connectivity test in a separate thread to avoid freezing the UI
        def check_thread():
            try:
                is_connected = ocr.test_ocr_connectivity()
                if is_connected:
                    self.logMessage("✓ OCR API connection successful! Ready to process documents.")
                else:
                    self.logMessage("❌ OCR API connection failed. Check your internet connection.")
            except Exception as e:
                self.logMessage(f"❌ Error checking OCR API connectivity: {str(e)}")
        
        threading.Thread(target=check_thread).start()
    
    def browseInputDir(self):
        """
        Open file dialog to select input directory
        입력 디렉토리를 선택하는 파일 대화 상자 열기
        """
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if dir_path:
            self.input_dir = dir_path
            self.input_path.setText(dir_path)
            self.logMessage(f"Input directory set to: {dir_path}")
            
            # If output directory not set, default to same as input
            if not self.output_dir:
                self.output_dir = dir_path
                self.output_path.setText(dir_path)
                self.logMessage(f"Output directory set to: {dir_path}")
    
    def browseOutputDir(self):
        """
        Open file dialog to select output directory
        출력 디렉토리를 선택하는 파일 대화 상자 열기
        """
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.output_path.setText(dir_path)
            self.logMessage(f"Output directory set to: {dir_path}")
    
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
            QMessageBox.warning(self, "Error", "Please select an input directory.")
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logMessage(f"Created output directory: {self.output_dir}")
        
        # Determine OCR mode
        mode = 'receipt' if self.mode_combo.currentText() == "Receipt" else 'text'
        
        # Disable controls during processing
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.output_browse_btn.setEnabled(False)
        
        self.logMessage(f"Starting OCR processing in {mode} mode...")
        self.logMessage(f"Processing {'all pages' if self.all_pages_check.isChecked() else 'first page only'} in PDF files.")
        
        # Create and start worker thread
        self.worker = OcrWorker(
            self.input_dir, 
            self.output_dir,
            mode=mode,
            process_all_pages=self.all_pages_check.isChecked()
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
            self.logMessage("Stopping OCR processing...")
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
            self.logMessage("OCR processing completed successfully!")
            
            # Start file renaming if option is checked
            if self.rename_check.isChecked():
                self.logMessage("Starting file renaming process...")
                
                # Create and start rename worker thread
                self.rename_worker = RenameWorker(self.output_dir, self.input_dir)
                self.rename_worker.progress_signal.connect(self.logMessage)
                self.rename_worker.complete_signal.connect(self.renamingComplete)
                
                self.rename_worker.start()
        else:
            self.logMessage("OCR processing did not complete successfully.")
    
    @pyqtSlot(bool)
    def renamingComplete(self, success):
        """
        Handle renaming completion
        이름 변경 완료 처리
        """
        if success:
            self.logMessage("File renaming completed successfully!")
        else:
            self.logMessage("File renaming did not complete successfully.")


def main():
    app = QApplication(sys.argv)
    
    # Create and show the app
    window = OcrApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()