import re
from copy import deepcopy
from datetime import date
from typing import Dict, List

import streamlit as st

st.set_page_config(
    page_title="릴스 자막 초안 생성기",
    page_icon="🎬",
    layout="wide",
)

# ---------------- 상태 ----------------
STATUS_LABELS = {
    "idle": "초안 작성 전",
    "generated": "생성 완료",
    "editing": "수정 중",
    "finalized": "확정 완료",
}

# ---------------- 초기화 ----------------
def init_state():
    defaults = {
        "status": "idle",
        "drafts": [],
        "saved_versions": [],
        "generation_log": [],
        "last_input_payload": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ---------------- 유틸 ----------------
def normalize_points(raw: str) -> List[str]:
    if not raw.strip():
        return []
    return [x.strip() for x in re.split(r"[,\n;/]+", raw) if x.strip()]

def build_payload():
    return {
        "행사명": st.session_state.event_name,
        "행사 기간": st.session_state.event_period,
        "행사 장소": st.session_state.event_place,
        "홍보 포인트": normalize_points(st.session_state.promo_points),
        "주력 상품": normalize_points(st.session_state.main_products),
        "이벤트/혜택": normalize_points(st.session_state.benefits),
        "필수 포함 문구": normalize_points(st.session_state.required_lines),
        "톤앤매너": st.session_state.tone,
        "스타일": st.session_state.style_template,
        "영상 길이": st.session_state.video_length,
        "예상 컷 수": int(st.session_state.cut_count),
    }

# ---------------- 무료 생성기 ----------------
def generate_drafts(payload, n):
    tone_map = {
        "밝고 경쾌함": "리듬감 있게",
        "신뢰감/정보형": "명확하게",
        "세일즈/강조형": "임팩트 있게",
        "트렌디/숏폼형": "짧고 감각적으로",
    }

    tone = tone_map.get(payload["톤앤매너"], "")

    templates = [
        "이번 주, 놓치면 아쉬운 혜택",
        "인기 상품 최대 할인 진행 중",
        "지금 가장 반응 좋은 아이템",
        "현장에서만 누릴 수 있는 혜택",
        "지금 바로 확인해보세요",
    ]

    drafts = []
    for i in range(n):
        drafts.append({
            "id": i+1,
            "caption": f"{tone} {templates[i % len(templates)]}",
            "description": "컷 설명을 입력하세요",
        })
    return drafts

# ---------------- 실행 ----------------
def run_generation():
    payload = build_payload()
    st.session_state.last_input_payload = payload

    st.session_state.generation_log = [
        "행사 정보 분석 중...",
        "자막 구조 생성 중...",
    ]

    with st.spinner("초안 생성 중..."):
        drafts = generate_drafts(payload, payload["예상 컷 수"])

    st.session_state.drafts = drafts
    st.session_state.status = "generated"

# ---------------- 시작 ----------------
init_state()

# ---------------- UI ----------------
st.title("🎬 릴스 자막 초안 생성기")
st.caption("무료 데모 모드 (API 없이 동작)")

left, right = st.columns([1, 1.3])

# ---------------- 입력 ----------------
with left:
    st.subheader("입력")

    st.text_input("행사명", key="event_name")
    st.text_input("행사 기간", key="event_period")
    st.text_input("행사 장소", key="event_place")

    st.text_area("홍보 포인트", key="promo_points")
    st.text_area("주력 상품", key="main_products")
    st.text_area("이벤트/혜택", key="benefits")
    st.text_area("필수 포함 문구", key="required_lines")

    st.radio(
        "톤앤매너",
        ["밝고 경쾌함", "신뢰감/정보형", "세일즈/강조형", "트렌디/숏폼형"],
        key="tone",
        horizontal=True
    )

    st.selectbox(
        "스타일",
        ["기본형", "혜택 강조형", "정보 전달형", "숏폼 몰입형"],
        key="style_template"
    )

    st.selectbox("영상 길이", ["15초", "30초"], key="video_length")
    st.number_input("컷 수", 3, 10, 5, key="cut_count")

    if st.button("초안 생성", type="primary"):
        run_generation()
        st.rerun()

# ---------------- 결과 ----------------
with right:
    st.subheader("결과")

    if not st.session_state.drafts:
        st.info("초안을 생성해주세요")
    else:
        for i, d in enumerate(st.session_state.drafts):
            with st.container(border=True):
                st.markdown(f"### 컷 {d['id']}")

                d["caption"] = st.text_area(
                    "자막", value=d["caption"], key=f"c{i}"
                )
                d["description"] = st.text_area(
                    "설명", value=d["description"], key=f"d{i}"
                )

        if st.button("최종 확정"):
            st.success("완료!")
