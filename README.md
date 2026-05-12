# YouTube → 블로그 생성기

YouTube URL을 입력하면 영상 자막을 추출하고, Google Gemini AI가 한국어 블로그 글을 자동으로 생성합니다.

## 주요 기능

- YouTube 자막 자동 추출 (한국어 → 영어 → 기타 언어 순)
- 영어 영상도 한국어 블로그로 변환
- 실시간 스트리밍 출력
- 출처(제목·채널·URL·작성일) 자동 포함
- Markdown 파일 다운로드

## 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. API 키 설정

`.env.example`을 `.env`로 복사 후 Gemini API 키 입력:

```
GEMINI_API_KEY=AIza여기에_API_키_입력
```

> API 키 발급: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key in new project

### 3. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| 웹 UI | Streamlit |
| AI 생성 | Google Gemini 2.0 Flash (`google-genai`) |
| 자막 추출 | youtube-transcript-api |
