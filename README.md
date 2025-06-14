# Receipt OCR Processor

영수증 이미지 파일에서 OCR과 LLM을 사용하여 정보를 추출하고 파일명을 변경하는 Python 스크립트입니다.

## 기능

- PDF, JPG, JPEG, PNG, TIFF 등 영수증 이미지 파일 처리
- PDF 파일을 이미지로 변환
- Naver Clova OCR API를 사용한 텍스트 추출
- OpenAI Mini-O4 모델을 사용한 필수 정보 추출:
  - 결제 날짜 (YYYYMMDD)
  - 승인 번호
  - 상점명
  - 결제 금액
- 외화 금액을 원화로 변환
- 원본 파일명을 `{MMDD}_{place}_{auth_number}_{amount}.확장자` 형식으로 변경

## 설치

```bash
pip install -r requirements.txt
```

### 추가 요구 사항

- PDF 처리를 위해서는 Poppler가 필요합니다.
  - macOS: `brew install poppler`
  - Ubuntu: `apt-get install poppler-utils`
  - Windows: [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)를 다운로드하여 설치

## 설정

`receipt_processor.py` 파일에서 다음 API 키를 설정해야 합니다:

```python
CLOVA_OCR_SECRET_KEY = "YOUR_CLOVA_OCR_SECRET_KEY"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
```

## 사용법

```bash
python receipt_processor.py --input_dir/-i 입력_디렉토리 [--output_dir/-o 출력_디렉토리]
```

### 예시

모든 영수증 이미지를 처리하고 같은 디렉토리에 결과 저장:
```bash
python receipt_processor.py --input_dir receipts/
# 또는 짧은 옵션 사용
python receipt_processor.py -i receipts/
```

모든 영수증 이미지를 처리하고 다른 디렉토리에 결과 저장:
```bash
python receipt_processor.py --input_dir receipts/ --output_dir processed/
# 또는 짧은 옵션 사용
python receipt_processor.py -i receipts/ -o processed/
```

## 결과

프로세스가 완료되면 다음과 같은 파일이 생성됩니다:

1. `원본파일이름.txt` - OCR로 추출된 텍스트
2. `원본파일이름.json` - LLM으로 추출된 정보 (JSON 형식)
3. `MMDD_상점명_승인번호_금액.확장자` - 원본 파일의 새 이름