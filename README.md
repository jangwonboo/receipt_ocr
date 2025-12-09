# Receipt OCR Processor

영수증 이미지 파일에서 OCR과 LLM을 사용하여 정보를 추출하고 파일명을 변경하는 Python 애플리케이션입니다.

## 기능

- PDF, JPG, JPEG, PNG 등 영수증 이미지 파일 처리
- Google Gemini API를 사용한 OCR 및 정보 추출:
  - 결제 날짜 (YYYYMMDD)
  - 상점명 (Place)
  - 결제 금액 (Amount)
  - 통화 (Currency)
- 추출된 정보를 기반으로 파일명 자동 변경
- GUI 인터페이스 제공 (PyQt6)
- 다국어 지원 (한국어/영어)

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

### API 키 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음을 추가하세요:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

**중요:** 등호(`=`) 앞뒤 공백 없이 작성하세요.

```bash
# 올바른 형식
GOOGLE_API_KEY=AIzaSyAamcLtA1tEiUZtaFnwZry7-98jgpLpj3Y

# 잘못된 형식 (공백 주의)
GOOGLE_API_KEY =AIzaSyAamcLtA1tEiUZtaFnwZry7-98jgpLpj3Y
```

### 문제 해결: API 키가 .env 파일에서 로드되지 않는 경우

만약 `.env` 파일에 `GOOGLE_API_KEY`를 설정했는데도 다른 키가 사용되거나 오류가 발생하는 경우:

**원인:**
- 시스템 환경 변수에 이미 `GOOGLE_API_KEY`가 설정되어 있어서 `.env` 파일의 값이 무시되는 경우
- `.env` 파일에 공백이 포함된 경우

**해결 방법:**

1. **환경 변수 확인:**
   ```bash
   echo $GOOGLE_API_KEY
   ```

2. **환경 변수 제거 (필요한 경우):**
   ```bash
   unset GOOGLE_API_KEY
   ```

3. **.env 파일 형식 확인:**
   - 등호(`=`) 앞뒤에 공백이 없는지 확인
   - 올바른 형식: `GOOGLE_API_KEY=your_key_here`
   - 잘못된 형식: `GOOGLE_API_KEY =your_key_here` (공백 있음)

4. **프로그램 재시작:**
   - 환경 변수를 변경한 경우 터미널을 재시작하거나 프로그램을 다시 실행하세요

**참고:** 
- 이 프로젝트는 `load_dotenv(override=True)`를 사용하여 `.env` 파일의 값을 환경 변수보다 우선적으로 사용합니다
- `.env` 파일의 값이 항상 우선 적용되므로, 환경 변수에 다른 값이 있어도 `.env` 파일의 값이 사용됩니다

## 사용법

### GUI 사용 (권장)

```bash
python ocr_gui.py
```

GUI에서:
1. 입력 디렉토리 선택
2. 처리 옵션 설정
3. "Start Processing" 버튼 클릭

### 명령줄 사용

```bash
# 단일 파일 처리
python gemini_ocr.py path/to/file.pdf

# 디렉토리 전체 처리
python gemini_ocr.py path/to/directory/
```

## 결과

프로세스가 완료되면 다음과 같은 파일이 생성됩니다:

1. `원본파일이름_ocr_output.txt` - OCR로 추출된 텍스트
2. `원본파일이름_extracted_info.json` - 추출된 정보 (JSON 형식):
   - `date`: 결제 날짜 (YYYYMMDD)
   - `place`: 상점명
   - `amount`: 결제 금액
   - `currency`: 통화 코드
3. `YYMMDD_상점명_금액_통화.pdf` - 원본 파일의 새 이름 (이름 변경 옵션 활성화 시)

## 문제 해결

### API 키 관련 문제

#### 문제: .env 파일의 GOOGLE_API_KEY가 사용되지 않음

**증상:**
- `.env` 파일에 올바른 API 키를 설정했는데도 다른 키가 사용됨
- 로그에 `.env` 파일과 다른 API 키가 표시됨
- 403 오류 발생 (정지된 API 키 사용)

**원인:**
1. 시스템 환경 변수에 이미 `GOOGLE_API_KEY`가 설정되어 있음
2. `.env` 파일 형식 오류 (공백 포함)

**해결 방법:**

1. **환경 변수 확인 및 제거:**
   ```bash
   # 현재 환경 변수 확인
   echo $GOOGLE_API_KEY
   
   # 환경 변수 제거 (필요한 경우)
   unset GOOGLE_API_KEY
   ```

2. **.env 파일 형식 확인:**
   ```bash
   # 올바른 형식 (공백 없음)
   GOOGLE_API_KEY=AIzaSyAamcLtA1tEiUZtaFnwZry7-98jgpLpj3Y
   
   # 잘못된 형식 (공백 있음 - 피해야 함)
   GOOGLE_API_KEY =AIzaSyAamcLtA1tEiUZtaFnwZry7-98jgpLpj3Y
   ```

3. **프로그램 재시작:**
   - 환경 변수를 변경한 경우 터미널을 재시작하거나 프로그램을 다시 실행

**기술적 설명:**
- 이 프로젝트는 `load_dotenv(override=True)`를 사용하여 `.env` 파일의 값을 환경 변수보다 우선적으로 사용합니다
- `.env` 파일의 값이 항상 우선 적용되므로, 환경 변수에 다른 값이 있어도 `.env` 파일의 값이 사용됩니다
- 코드에서 `.strip()`을 사용하여 공백 문제도 자동으로 처리합니다

### 기타 문제

#### PNG 파일이 처리되지 않는 경우
- PNG 파일은 자동으로 PDF로 변환되어 처리됩니다
- `img2pdf` 패키지가 설치되어 있는지 확인하세요: `pip install img2pdf`

#### API 호출 오류
- API 키가 정지(suspended)된 경우: Google Cloud Console에서 새 API 키를 생성하세요
- 속도 제한 오류: 잠시 기다린 후 다시 시도하세요