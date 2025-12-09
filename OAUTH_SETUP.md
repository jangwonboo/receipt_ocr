# OAuth 2.0 인증 설정 가이드

## ⚠️ 중요 참고사항

**Google Gemini API는 일반적으로 API 키를 사용합니다.** OAuth 2.0은 Vertex AI를 통한 접근이나 특별한 설정이 필요할 수 있습니다. 

OAuth 2.0 인증에 문제가 발생하면 API 키 방식을 사용하는 것을 권장합니다.

## 개요
이 프로젝트는 Google Gemini API에 OAuth 2.0 인증을 시도할 수 있지만, **API 키 방식을 권장합니다**.

## 설정 방법

### 1. credentials.json 파일 생성

프로젝트 루트 디렉토리에 `credentials.json` 파일을 생성하고 다음 내용을 붙여넣으세요:

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

**중요:** 위의 `YOUR_CLIENT_ID`와 `YOUR_CLIENT_SECRET`을 Google Cloud Console에서 발급받은 실제 값으로 교체하세요.

### 2. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- `google-genai`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`

### 3. OAuth 2.0 활성화

`.env` 파일에 다음을 추가하세요:

```bash
USE_OAUTH=true
```

또는 환경 변수로 설정:

```bash
export USE_OAUTH=true
```

### 4. OAuth 스코프 설정 (선택사항)

기본적으로 빈 스코프를 사용합니다. 특정 스코프가 필요한 경우 환경 변수로 설정할 수 있습니다:

```bash
export GOOGLE_OAUTH_SCOPES="https://www.googleapis.com/auth/cloud-platform"
```

**참고:** Google Gemini API는 일반적으로 API 키를 사용하므로, OAuth 2.0 인증에 문제가 발생할 수 있습니다.

### 5. 첫 실행 시 인증

프로그램을 처음 실행하면 브라우저가 자동으로 열리고 Google 계정 로그인을 요청합니다.

1. 브라우저에서 Google 계정 선택
2. 권한 승인 (스코프가 설정된 경우)
3. 인증 완료 후 `token.json` 파일이 자동 생성됨

**오류 발생 시:**
- "Error 400: invalid_scope" 오류가 발생하면 스코프를 빈 배열로 설정하거나 API 키 방식을 사용하세요.

### 5. 이후 실행

`token.json` 파일이 생성되면 이후 실행 시 자동으로 인증됩니다.
토큰이 만료되면 자동으로 새로고침됩니다.

## API 키 방식 (대체 방법)

OAuth 2.0을 사용하지 않으려면:

```bash
USE_OAUTH=false
GOOGLE_API_KEY=your_api_key_here
```

또는 환경 변수에서 `USE_OAUTH`를 설정하지 않으면 기본적으로 API 키 방식을 사용합니다.

## 파일 설명

- `credentials.json`: OAuth 2.0 클라이언트 자격 증명 (보안상 Git에 커밋하지 마세요)
- `token.json`: 인증 토큰 (자동 생성, 보안상 Git에 커밋하지 마세요)

## 문제 해결

### 인증 실패
- `credentials.json` 파일이 올바른 위치에 있는지 확인
- Google Cloud Console에서 OAuth 2.0 클라이언트 ID가 활성화되어 있는지 확인

### 토큰 만료
- `token.json` 파일을 삭제하고 다시 인증하세요

### 패키지 오류
```bash
pip install --upgrade google-auth google-auth-oauthlib google-auth-httplib2
```

