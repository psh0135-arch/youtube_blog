import os
import re
import streamlit as st
from google import genai
import requests
from datetime import datetime
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="YouTube → 블로그 생성기",
    page_icon="📝",
    layout="wide",
)


def extract_video_id(url: str) -> str | None:
    pattern = r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_video_metadata(video_id: str) -> dict:
    try:
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}&format=json"
        )
        resp = requests.get(oembed_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", "제목 없음"),
            "channel": data.get("author_name", "채널 없음"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail": data.get("thumbnail_url", ""),
        }
    except requests.exceptions.RequestException as e:
        st.warning(f"영상 정보를 가져오지 못했습니다: {e}")
    except (ValueError, KeyError):
        st.warning("영상 정보 파싱에 실패했습니다.")
    return {
        "title": "제목 없음",
        "channel": "채널 없음",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": "",
    }


def get_transcript(video_id: str) -> tuple[str, str]:
    """Returns (transcript_text, language_code)"""
    api = YouTubeTranscriptApi()

    # Priority: Korean > English > any available
    for lang in ["ko", "en"]:
        try:
            fetched = api.fetch(video_id, languages=[lang])
            return " ".join(s.text for s in fetched), lang
        except Exception:
            pass

    # Fallback: take the first available transcript
    transcript_list = api.list(video_id)
    for t in transcript_list:
        fetched = t.fetch()
        return " ".join(s.text for s in fetched), t.language_code

    raise NoTranscriptFound(video_id, [], {})


def build_prompt(transcript: str, metadata: dict, lang: str) -> str:
    lang_note = "영상이 한국어가 아닐 경우 내용을 한국어로 자연스럽게 번역하여 작성하세요." if lang != "ko" else ""

    return f"""다음은 YouTube 영상의 자막입니다. 이 내용을 바탕으로 한국어 블로그 글을 작성해주세요.

영상 제목: {metadata['title']}
채널: {metadata['channel']}
URL: {metadata['url']}
{lang_note}

자막 내용:
{transcript[:14000]}

---
블로그 글 작성 규칙:
1. 독자의 흥미를 끄는 매력적인 제목 작성 (영상 제목과 달라도 됨)
2. 도입부 → 소제목 3~5개로 구성된 본문 → 결론 순서로 작성
3. 자연스럽고 읽기 쉬운 한국어 문체 사용
4. 핵심 내용, 인사이트, 실용적인 정보를 중심으로 정리
5. 글 마지막에 반드시 아래 형식의 출처 섹션 포함:

---
**출처**
- 영상 제목: {metadata['title']}
- 채널: {metadata['channel']}
- URL: {metadata['url']}
- 작성일: {datetime.now().strftime('%Y년 %m월 %d일')}

Markdown 형식으로 작성해주세요."""


def generate_blog_post(transcript: str, metadata: dict, lang: str, api_key: str):
    """Generator that streams blog post text chunks."""
    client = genai.Client(api_key=api_key)
    prompt = build_prompt(transcript, metadata, lang)

    for chunk in client.models.generate_content_stream(
        model="gemini-2.5-flash",
        contents=prompt,
    ):
        if chunk.text:
            yield chunk.text


# ── UI ──────────────────────────────────────────────────────────────────────

st.title("📝 YouTube → 블로그 생성기")
st.caption("YouTube URL을 입력하면 한국어 블로그 글을 자동으로 생성합니다.")

# API Key — .env (local) 또는 Streamlit Cloud secrets 우선
api_key = os.getenv("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
with st.sidebar:
    st.header("설정")
    if api_key:
        st.success("API 키 로드됨 (.env)")
    else:
        api_key = st.text_input(
            "Gemini API 키",
            type="password",
            placeholder="AIza...",
            help=".env 파일에 GEMINI_API_KEY를 설정하거나 여기에 직접 입력하세요.",
        )
    st.divider()
    st.markdown(
        "**API 키 발급 방법**\n\n"
        "1. [aistudio.google.com](https://aistudio.google.com) 접속\n"
        "2. 로그인 후 **Get API key** 클릭\n"
        "3. Create API key 클릭"
    )

st.divider()

url_input = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
)

generate_btn = st.button(
    "블로그 글 생성",
    type="primary",
    disabled=not (url_input and api_key),
)

if not api_key:
    st.info("왼쪽 사이드바에서 Gemini API 키를 입력해주세요.")

if generate_btn and url_input and api_key:
    video_id = extract_video_id(url_input)
    if not video_id:
        st.error("올바른 YouTube URL을 입력해주세요.")
        st.stop()

    # Metadata
    with st.spinner("영상 정보를 가져오는 중..."):
        metadata = get_video_metadata(video_id)

    col_thumb, col_info = st.columns([1, 3])
    with col_thumb:
        if metadata["thumbnail"]:
            st.image(metadata["thumbnail"])
    with col_info:
        st.markdown(f"**{metadata['title']}**")
        st.write(f"채널: {metadata['channel']}")
        st.write(f"URL: {metadata['url']}")

    # Transcript
    try:
        with st.spinner("자막을 가져오는 중..."):
            transcript, lang = get_transcript(video_id)
        st.success(f"자막 로드 완료 ({len(transcript):,}자 / 언어: {lang})")
    except TranscriptsDisabled:
        st.error("이 영상은 자막이 비활성화되어 있습니다.")
        st.stop()
    except NoTranscriptFound:
        st.error("사용 가능한 자막이 없습니다. 자막이 있는 영상을 시도해주세요.")
        st.stop()
    except Exception as e:
        st.error(f"자막 추출 오류: {e}")
        st.stop()

    # Blog generation (streaming)
    st.divider()
    st.subheader("생성된 블로그 글")

    try:
        result_placeholder = st.empty()
        blog_text = ""

        with st.spinner("블로그 글을 생성하는 중..."):
            for chunk in generate_blog_post(transcript, metadata, lang, api_key):
                blog_text += chunk
                result_placeholder.markdown(blog_text + "▌")

        result_placeholder.markdown(blog_text)

        tab_preview, tab_raw = st.tabs(["미리보기", "Markdown 원문"])
        with tab_preview:
            st.markdown(blog_text)
        with tab_raw:
            st.code(blog_text, language="markdown")

        filename = f"blog_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        st.download_button(
            label="📥 Markdown으로 다운로드",
            data=blog_text,
            file_name=filename,
            mime="text/markdown",
        )

    except Exception as e:
        st.error(f"블로그 생성 오류: {e}")
