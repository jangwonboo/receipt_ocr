# Receipt OCR Tools
# 영수증 OCR 도구

A collection of Python tools for OCR processing of receipts and documents using Naver Cloud OCR API.  
네이버 클라우드 OCR API를 사용한 영수증 및 문서 OCR 처리를 위한 Python 도구 모음입니다.

## Overview / 개요

This project consists of three main Python scripts:  
이 프로젝트는 세 가지 주요 Python 스크립트로 구성되어 있습니다:

1. **ocr.py** - Extract text and structured data from receipts and documents  
   **ocr.py** - 영수증 및 문서에서 텍스트 및 구조화된 데이터 추출
   
2. **rename_receipts.py** - Rename receipt files based on extracted OCR data  
   **rename_receipts.py** - 추출된 OCR 데이터를 기반으로 영수증 파일 이름 변경
   
3. **utils.py** - Utility functions used by the other scripts  
   **utils.py** - 다른 스크립트에서 사용하는 유틸리티 함수

## Prerequisites / 필수 조건

- Python 3.6+
- Naver Cloud OCR API credentials (for general and receipt OCR)  
  네이버 클라우드 OCR API 자격 증명 (일반 및 영수증 OCR용)
- Required Python packages (install via `pip install -r requirements.txt`):  
  필요한 Python 패키지 (다음을 통해 설치: `pip install -r requirements.txt`):
  - requests
  - pdf2image
  - pillow

## Features / 기능

### ocr.py

- Extract text from PDF documents and images  
  PDF 문서 및 이미지에서 텍스트 추출
- Special receipt OCR processing with structured data extraction  
  구조화된 데이터 추출이 포함된 특수 영수증 OCR 처리
- Support for multiple file formats (PDF, JPG, PNG, TIFF)  
  여러 파일 형식 지원 (PDF, JPG, PNG, TIFF)
- Language selection (Korean, English)  
  언어 선택 (한국어, 영어)
- Batch processing for directories of files  
  파일 디렉토리에 대한 일괄 처리
- Error handling and detailed logging  
  오류 처리 및 상세 로깅

### rename_receipts.py

- Automatically rename receipt files based on data extracted by ocr.py  
  ocr.py에 의해 추출된 데이터를 기반으로 영수증 파일 자동 이름 변경
- Structured naming format: `{payment_date}_{store_name}_{total_price}.{ext}`  
  구조화된 이름 형식: `{결제일}_{상점명}_{총액}.{확장자}`
- Clean filename formatting with special character removal  
  특수 문자 제거로 깔끔한 파일 이름 포맷팅
- Handles missing data with fallback options  
  대체 옵션으로 누락된 데이터 처리
- Batch processing for all files in a directory  
  디렉토리 내 모든 파일에 대한 일괄 처리

### utils.py

- Common utility functions shared between scripts  
  스크립트 간에 공유되는 공통 유틸리티 함수
- Logging setup with console and file output  
  콘솔 및 파일 출력으로 로깅 설정
- File validation (extension, size, existence)  
  파일 유효성 검사 (확장자, 크기, 존재)

## Usage / 사용법

### OCR Processing / OCR 처리

```bash
# Process a single file (receipt OCR mode)
# 단일 파일 처리 (영수증 OCR 모드)
python ocr.py --file path/to/receipt.jpg --mode receipt

# Process a directory of files (general OCR mode)
# 파일 디렉토리 처리 (일반 OCR 모드)
python ocr.py --dir path/to/documents/ --mode general

# Process with specific language
# 특정 언어로 처리
python ocr.py --file path/to/document.pdf --lang en
```

### Receipt Renaming / 영수증 이름 변경

```bash
# Rename receipt files using JSON data from OCR processing
# OCR 처리에서 얻은 JSON 데이터로 영수증 파일 이름 변경
python rename_receipts.py --json_dir path/to/json/ --source_dir path/to/receipts/

# Debug mode with detailed logging
# 자세한 로깅과 함께 디버그 모드
python rename_receipts.py --debug
```

## Output Format / 출력 형식

### OCR Results / OCR 결과

OCR results are saved as JSON files with structured data and extracted text.  
OCR 결과는 구조화된 데이터와 추출된 텍스트가 포함된 JSON 파일로 저장됩니다.

For receipts, the JSON structure includes:  
영수증의 경우, JSON 구조에는 다음이 포함됩니다:

- Store information (name, address, business number)  
  상점 정보 (이름, 주소, 사업자번호)
- Payment information (date, time, total price)  
  결제 정보 (날짜, 시간, 총액)
- Item details (name, price, quantity)  
  항목 세부 정보 (이름, 가격, 수량)

### Renamed Files / 이름 변경된 파일

Files are renamed in the format: `MMDD_StoreName_TotalPrice.ext`  
파일은 다음 형식으로 이름이 변경됩니다: `MMDD_상점명_총액.확장자`

Example: `0415_StarbucksCoffee_5000.jpg`  
예시: `0415_스타벅스커피_5000.jpg`

## Error Handling / 오류 처리

The scripts include comprehensive error handling and logging:  
스크립트에는 포괄적인 오류 처리 및 로깅이 포함되어 있습니다:

- API connection errors  
  API 연결 오류
- File format and size validation  
  파일 형식 및 크기 유효성 검사
- Missing data handling  
  누락된 데이터 처리
- Error logging to console and file  
  콘솔 및 파일에 오류 로깅

## License / 라이선스

[MIT License](LICENSE) 