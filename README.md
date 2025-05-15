# Naver CLOVA OCR Document Parser

A command-line utility for extracting structured data from documents using Naver Cloud's CLOVA OCR API.

## Features

- **Multiple OCR Modes**:
  - Text extraction (general OCR)
  - Receipt parsing (structured data extraction)
  - Business card parsing (structured data extraction)
  
- **PDF Support**:
  - Automatic conversion of PDF to images
  - Process entire multi-page documents
  - Extract data from individual pages or entire documents
  
- **Flexible Output Formats**:
  - JSON (structured data for programmatic use)
  - Text (human-readable output)
  - Markdown (formatted documentation)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/parse_docs.git
   cd parse_docs
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install system dependencies for PDF processing:
   - macOS: `brew install poppler`
   - Ubuntu/Debian: `apt-get install poppler-utils`
   - Windows: Download from [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)

4. Run the script with the `--install_deps` flag to check and install any missing dependencies:
   ```
   python ocr.py --install_deps
   ```

## Prerequisites

- Python 3.6+
- Required Python packages:
  - requests
  - pdf2image (for PDF processing)
  - pillow
  - argparse
  - logging
- Poppler utilities (for PDF processing)

## API Setup and Credentials

This tool uses Naver Cloud's CLOVA OCR API which requires proper credentials to function.

### Credentials

Two sets of credentials are configured in the system:

1. **General OCR Credentials** (for text extraction):
   ```
   Domain ID: 41840
   Invoke Key: 9c0164ae62761049733ec404292901331072c6f2b511f8fbe0e899b229de65ef
   Secret: bFRFc0lpWVNtb1NIdkxnYkJwZlZzQ216WkNkVFV2SU0=
   ```

2. **Receipt OCR Credentials** (for structured receipt data):
   ```
   Secret Key: VFJqQ21MYkJEc0VCdUVpd0hKTlRwdkx0VHhQZG1wQ2o=
   Invoke URL: https://mg6eku63fn.apigw.ntruss.com/custom/v1/42025/e24fb8bb1b9e5b931f3a1efcf9baab214899b18e2ea248dc8722d8ed0a8597bc/document/receipt
   ```

### API Endpoint Structure

The API endpoints are structured as follows:

- **General OCR**:
  ```
  https://1ca5ztdzdg.apigw.ntruss.com/custom/v1/{DomainId}/{InvokeKey}/general
  ```

- **Receipt OCR**:
  ```
  https://mg6eku63fn.apigw.ntruss.com/custom/v1/42025/e24fb8bb1b9e5b931f3a1efcf9baab214899b18e2ea248dc8722d8ed0a8597bc/document/receipt
  ```

## Key Findings from Testing

Our testing revealed some important insights about the Naver CLOVA OCR API:

1. The general OCR endpoint (`/general`) works successfully for extracting text from images and PDFs
2. The default domain ID does not have receipt OCR enabled (error code `0022` - "Request domain invalid")
3. Alternative credentials have been integrated and successfully tested for receipt OCR
4. PDF processing works by automatically converting PDF pages to images
5. The API connectivity test passes with a 400 status code (which is expected when no image data is provided)

## Usage Examples

### General Text Extraction

```bash
# Extract text from an image
python ocr.py --mode text --input document.jpg

# Extract text from a PDF (first page only)
python ocr.py --mode text --input document.pdf

# Extract text from all pages of a PDF
python ocr.py --mode text --input document.pdf --all_pages
```

### Receipt OCR (with alternative credentials)

```bash
# Process a receipt image using alternative credentials
python ocr.py --mode receipt --input receipt.jpg --alt_creds

# Process a receipt PDF using alternative credentials
python ocr.py --mode receipt --input receipt.pdf --alt_creds
```

### Business Card OCR

```bash
# Process a business card image
python ocr.py --mode namecard --input business_card.jpg

# Process a business card PDF
python ocr.py --mode namecard --input business_card.pdf
```

### Output Format Options

```bash
# Output as JSON (default for structured data)
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format json

# Output as text
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format text

# Output as markdown
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format markdown
```

### Receipt Renaming Tool

After extracting receipt data to JSON, you can use the rename tool to automatically rename receipt image and PDF files:

```bash
# Rename receipts based on extracted data (in current directory)
python rename_receipts.py

# Specify different JSON and source directories
python rename_receipts.py --json_dir ./extracted_data --source_dir ./receipts

# Enable debug mode for detailed logging
python rename_receipts.py --debug
```

The rename tool supports multiple file formats: PDF, PNG, JPG, JPEG, TIF, and TIFF. It will look for files with the same base name as the JSON file but with any of these extensions.

## PDF Processing

The script supports processing PDF files by converting them to images before sending to the OCR API:

1. For single-page extraction (default): 
```bash
python ocr.py --mode receipt --input document.pdf --alt_creds
```

2. For multi-page extraction:
```bash 
python ocr.py --mode receipt --input document.pdf --alt_creds --all_pages
```

## Sample Output

The receipt OCR successfully extracts structured data, including:
- Store name and business number
- Store address and telephone numbers
- Payment date and time
- Itemized list with product names, quantities, and prices
- Total amount and payment method

Example output is saved in JSON format by default.

## Common Issues and Solutions

1. **Error Code 0022 "Request domain invalid"**: 
   - The specific OCR feature (receipt, name-card, etc.) is not enabled for your domain
   - You need to enable this feature in the Naver Cloud Platform Console or use alternative credentials

2. **Error Code 0011 "Request invalid"**:
   - Missing required fields in the request
   - Incorrect format or empty image data

3. **PDF Processing Errors**:
   - Make sure pdf2image and Poppler are installed:
     - `pip install pdf2image`
     - macOS: `brew install poppler`
     - Ubuntu: `apt-get install poppler-utils`
   - Use `--install_deps` flag to check and install dependencies

## Request Format

The request should be formatted as follows:

```json
{
    "version": "V2",
    "requestId": "4567",
    "timestamp": 1746836831864,
    "images": [
        {
            "format": "jpg",
            "name": "receipt_test",
            "data": "{Base64 encoded image data}"
        }
    ]
}
```

## Documentation Resources

- [CLOVA OCR Receipt Documentation](https://api.ncloud-docs.com/docs/ai-application-service-ocr-ocrdocumentocr-receipt)
- [CLOVA OCR Overview](https://api.ncloud-docs.com/docs/en/ai-application-service-ocr)
- [Common Response Status Codes](https://api.ncloud-docs.com/docs/common-ncpapi)

## Command Line Options

For full command-line options, run:
```
python ocr.py -h
```

---

# 네이버 CLOVA OCR 문서 파서

네이버 클라우드의 CLOVA OCR API를 사용하여 문서에서 구조화된 데이터를 추출하는 명령줄 유틸리티입니다.

## 기능

- **다양한 OCR 모드**:
  - 텍스트 추출 (일반 OCR)
  - 영수증 파싱 (구조화된 데이터 추출)
  - 명함 파싱 (구조화된 데이터 추출)
  
- **PDF 지원**:
  - PDF를 이미지로 자동 변환
  - 전체 다중 페이지 문서 처리
  - 개별 페이지 또는 전체 문서에서 데이터 추출
  
- **유연한 출력 형식**:
  - JSON (프로그래밍 용도의 구조화된 데이터)
  - 텍스트 (사람이 읽을 수 있는 출력)
  - 마크다운 (형식화된 문서)

## 설치

1. 리포지토리 복제:
   ```
   git clone https://github.com/yourusername/parse_docs.git
   cd parse_docs
   ```

2. 종속성 설치:
   ```
   pip install -r requirements.txt
   ```

3. PDF 처리를 위한 시스템 종속성 설치:
   - macOS: `brew install poppler`
   - Ubuntu/Debian: `apt-get install poppler-utils`
   - Windows: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)에서 다운로드

4. `--install_deps` 플래그를 사용하여 스크립트를 실행하여 누락된 종속성을 확인하고 설치:
   ```
   python ocr.py --install_deps
   ```

## 선행 조건

- Python 3.6+
- 필요한 Python 패키지:
  - requests
  - pdf2image (PDF 처리용)
  - pillow
  - argparse
  - logging
- Poppler 유틸리티 (PDF 처리용)

## API 설정 및 자격 증명

이 도구는 네이버 클라우드의 CLOVA OCR API를 사용하며, 기능하기 위해 적절한 자격 증명이 필요합니다.

### 자격 증명

시스템에는 두 세트의 자격 증명이 구성되어 있습니다:

1. **일반 OCR 자격 증명** (텍스트 추출용):
   ```
   Domain ID: 41840
   Invoke Key: 9c0164ae62761049733ec404292901331072c6f2b511f8fbe0e899b229de65ef
   Secret: bFRFc0lpWVNtb1NIdkxnYkJwZlZzQ216WkNkVFV2SU0=
   ```

2. **영수증 OCR 자격 증명** (구조화된 영수증 데이터용):
   ```
   Secret Key: VFJqQ21MYkJEc0VCdUVpd0hKTlRwdkx0VHhQZG1wQ2o=
   Invoke URL: https://mg6eku63fn.apigw.ntruss.com/custom/v1/42025/e24fb8bb1b9e5b931f3a1efcf9baab214899b18e2ea248dc8722d8ed0a8597bc/document/receipt
   ```

## 테스트에서 발견된 주요 내용

테스트를 통해 네이버 CLOVA OCR API에 대한 몇 가지 중요한 인사이트를 발견했습니다:

1. 일반 OCR 엔드포인트(`/general`)는 이미지와 PDF에서 텍스트를 추출하는 데 성공적으로 작동합니다
2. 기본 도메인 ID는 영수증 OCR이 활성화되어 있지 않습니다 (오류 코드 `0022` - "Request domain invalid")
3. 대체 자격 증명이 통합되었으며 영수증 OCR용으로 성공적으로 테스트되었습니다
4. PDF 처리는 PDF 페이지를 이미지로 자동 변환하여 작동합니다
5. API 연결 테스트는 400 상태 코드로 통과합니다(이미지 데이터가 제공되지 않을 때 예상되는 응답)

## 사용 예시

### 일반 텍스트 추출

```bash
# 이미지에서 텍스트 추출
python ocr.py --mode text --input document.jpg

# PDF에서 텍스트 추출 (첫 페이지만)
python ocr.py --mode text --input document.pdf

# PDF의 모든 페이지에서 텍스트 추출
python ocr.py --mode text --input document.pdf --all_pages
```

### 영수증 OCR (대체 자격 증명 사용)

```bash
# 대체 자격 증명을 사용하여 영수증 이미지 처리
python ocr.py --mode receipt --input receipt.jpg --alt_creds

# 대체 자격 증명을 사용하여 영수증 PDF 처리
python ocr.py --mode receipt --input receipt.pdf --alt_creds
```

### 명함 OCR

```bash
# 명함 이미지 처리
python ocr.py --mode namecard --input business_card.jpg

# 명함 PDF 처리
python ocr.py --mode namecard --input business_card.pdf
```

### 출력 형식 옵션

```bash
# JSON으로 출력 (구조화된 데이터의 기본값)
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format json

# 텍스트로 출력
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format text

# 마크다운으로 출력
python ocr.py --mode receipt --input receipt.jpg --alt_creds --format markdown
```

### 영수증 이름 변경 도구

JSON으로 영수증 데이터를 추출한 후, 이름 변경 도구를 사용하여 영수증 이미지 및 PDF 파일 이름을 자동으로 바꿀 수 있습니다:

```bash
# 추출된 데이터를 기반으로 영수증 이름 변경 (현재 디렉토리)
python rename_receipts.py

# 다른 JSON 및 소스 디렉토리 지정
python rename_receipts.py --json_dir ./extracted_data --source_dir ./receipts

# 상세 로깅을 위한 디버그 모드 활성화
python rename_receipts.py --debug
```

이름 변경 도구는 여러 파일 형식을 지원합니다: PDF, PNG, JPG, JPEG, TIF, TIFF. JSON 파일과 동일한 기본 이름을 가진 파일을 이러한 확장자 중 하나로 찾습니다.

## 일반적인 문제 및 해결책

1. **오류 코드 0022 "Request domain invalid"**: 
   - 특정 OCR 기능(영수증, 명함 등)이 도메인에 활성화되어 있지 않습니다
   - 네이버 클라우드 플랫폼 콘솔에서 이 기능을 활성화하거나 대체 자격 증명을 사용해야 합니다

2. **오류 코드 0011 "Request invalid"**:
   - 요청에 필수 필드가 누락됨
   - 잘못된 형식 또는 빈 이미지 데이터

3. **PDF 처리 오류**:
   - pdf2image와 Poppler가 설치되어 있는지 확인:
     - `pip install pdf2image`
     - macOS: `brew install poppler`
     - Ubuntu: `apt-get install poppler-utils`
   - `--install_deps` 플래그를 사용하여 종속성 확인 및 설치

## 명령줄 옵션

전체 명령줄 옵션을 보려면 다음을 실행하세요:
```
python ocr.py -h
``` 