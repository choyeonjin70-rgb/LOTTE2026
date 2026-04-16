from pathlib import Path

app_code = r'''
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

STATUS_LABELS = {
    "idle": "초안 작성 전",
    "generated": "생성 완료",
    "editing": "수정 중",
    "finalized": "확정 완료",
}

STATUS_META = {
    "idle": {"bg": "#f5f5f7", "fg": "#6e6e73"},
    "generated": {"bg": "#e8f2ff", "fg": "#0066cc"},
    "editing": {"bg": "#fff4d6", "fg": "#8a5d00"},
    "finalized": {"bg": "#e8f7ec", "fg": "#1d7a35"},
}


def init_state() -> None:
    defaults = {
        "status": "idle",
        "drafts": [],
        "saved_versions": [],
        "generation_log": [],
        "last_input_payload": {},
        "show_export_text": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def normalize_points(raw: str) -> List[str]:
    if not raw.strip():
        return []
    parts = re.split(r"[\n,;/]+", raw)
    return [p.strip() for p in parts if p.strip()]


def build_input_payload() -> Dict:
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


def fallback_generate_drafts(payload: Dict, target_count: int) -> List[Dict]:
    event_name = payload["행사명"] or "이번 행사"
    period = payload["행사 기간"] or "이번 주"
    place = payload["행사 장소"] or "현장"
    tone = payload["톤앤매너"]
    style = payload["스타일"]

    promo_points = payload["홍보 포인트"] or ["놓치면 아쉬운 핵심 혜택"]
    products = payload["주력 상품"] or ["인기 상품"]
    benefits = payload["이벤트/혜택"] or ["특별 혜택"]
    required = payload["필수 포함 문구"]

    tone_map = {
        "밝고 경쾌함": "리듬감 있게",
        "신뢰감/정보형": "명확하고 또렷하게",
        "세일즈/강조형": "임팩트 있게",
        "트렌디/숏폼형": "짧고 감각적으로",
    }
    tone_prefix = tone_map.get(tone, "자연스럽게")

    caption_templates = [
        f"{period}, {event_name} 꼭 체크하세요",
        f"{products[0]} 중심으로 지금 가장 반응 좋은 포인트만 담았어요",
        f"{benefits[0]} 혜택으로 체감되는 매력을 강조해보세요",
        f"{promo_points[0]} 포인트를 한눈에 전달하는 핵심 설명 컷",
        "지금 바로 확인하고 원하는 혜택을 챙겨보세요",
    ]

    description_templates = [
        f"{place} 전경과 행사 타이틀을 보여주는 오프닝 컷",
        f"{products[0]} 클로즈업과 핵심 특징을 보여주는 컷",
        "혜택 문구와 가격/혜택 강조 그래픽이 함께 나오는 컷",
        "현장 분위기 또는 사용 장면을 보여주는 설명 컷",
        "CTA 중심으로 마무리하는 엔딩 컷",
    ]

    drafts = []
    for idx in range(target_count):
        caption = f"{tone_prefix} {caption_templates[idx % len(caption_templates)]}"
        description = f"{style} 스타일로 {description_templates[idx % len(description_templates)]}"

        if required and idx < len(required):
            caption = f"{caption} | {required[idx]}"
        elif required and idx == target_count - 1:
            caption = f"{caption} | {' / '.join(required[:2])}"

        drafts.append(
            {
                "id": idx + 1,
                "caption": caption,
                "description": description,
            }
        )
    return drafts


def regenerate_single_cut(index: int) -> None:
    payload = st.session_state.last_input_payload or build_input_payload()
    regenerated = fallback_generate_drafts(payload, len(st.session_state.drafts))
    st.session_state.drafts[index]["caption"] = regenerated[index]["caption"]
    st.session_state.drafts[index]["description"] = regenerated[index]["description"]
    st.session_state.status = "editing"


def move_cut(index: int, direction: int) -> None:
    new_index = index + direction
    if 0 <= new_index < len(st.session_state.drafts):
        st.session_state.drafts[index], st.session_state.drafts[new_index] = (
            st.session_state.drafts[new_index],
            st.session_state.drafts[index],
        )
        for i, draft in enumerate(st.session_state.drafts, start=1):
            draft["id"] = i
        st.session_state.status = "editing"


def add_cut(after_index: int) -> None:
    st.session_state.drafts.insert(
        after_index + 1,
        {
            "id": after_index + 2,
            "caption": "새 컷 자막을 입력하세요",
            "description": "새 컷 설명을 입력하세요",
        },
    )
    for i, draft in enumerate(st.session_state.drafts, start=1):
        draft["id"] = i
    st.session_state.status = "editing"


def remove_cut(index: int) -> None:
    if len(st.session_state.drafts) <= 1:
        st.warning("최소 1개 컷은 유지되어야 합니다.")
        return
    st.session_state.drafts.pop(index)
    for i, draft in enumerate(st.session_state.drafts, start=1):
        draft["id"] = i
    st.session_state.status = "editing"


def export_text(drafts: List[Dict]) -> str:
    lines = []
    for item in drafts:
        lines.append(f"[컷 {item['id']}]")
        lines.append(f"자막: {item['caption']}")
        lines.append(f"컷 설명: {item['description']}")
        lines.append("")
    return "\n".join(lines).strip()


def save_current_version() -> None:
    st.session_state.saved_versions.append(
        {
            "saved_at": str(date.today()),
            "status": st.session_state.status,
            "payload": deepcopy(st.session_state.last_input_payload),
            "drafts": deepcopy(st.session_state.drafts),
        }
    )


def run_generation() -> None:
    payload = build_input_payload()
    st.session_state.last_input_payload = payload
    st.session_state.generation_log = [
        "행사 포인트 정리 중...",
        "메시지 흐름 구성 중...",
        "컷별 자막 초안 생성 중...",
    ]
    with st.spinner("무료 데모 모드로 초안을 생성하고 있습니다..."):
        st.session_state.drafts = fallback_generate_drafts(payload, payload["예상 컷 수"])
    st.session_state.status = "generated"


init_state()

meta = STATUS_META.get(st.session_state.status, STATUS_META["idle"])

st.markdown(
    """
    <style>
    :root {
        --apple-bg: #fbfbfd;
        --apple-card: rgba(255,255,255,0.82);
        --apple-border: rgba(0,0,0,0.08);
        --apple-text: #1d1d1f;
        --apple-sub: #6e6e73;
        --apple-blue: #0071e3;
        --apple-blue-hover: #0077ed;
        --apple-line: #d2d2d7;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                     "Apple SD Gothic Neo", "Noto Sans KR", "Segoe UI", sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(circle at top, rgba(0,113,227,0.06), transparent 30%),
            linear-gradient(180deg, #f7f7f8 0%, #fbfbfd 22%, #ffffff 100%);
        color: var(--apple-text);
    }

    .block-container {
        max-width: 1420px;
        padding-top: 1.25rem;
        padding-bottom: 2.5rem;
    }

    h1, h2, h3, h4 {
        letter-spacing: -0.02em;
        color: var(--apple-text);
    }

    .hero {
        background: var(--apple-card);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
        border: 1px solid var(--apple-border);
        border-radius: 28px;
        padding: 28px 32px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.06);
        margin-bottom: 18px;
    }

    .eyebrow {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #86868b;
        margin-bottom: 8px;
    }

    .hero-title {
        font-size: 40px;
        line-height: 1.08;
        font-weight: 700;
        margin: 0;
    }

    .hero-sub {
        margin-top: 10px;
        margin-bottom: 0;
        font-size: 16px;
        color: var(--apple-sub);
        line-height: 1.5;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 10px 14px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
    }

    .free-note {
        display: inline-block;
        margin-top: 14px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(0,113,227,0.08);
        color: var(--apple-blue);
        font-size: 12px;
        font-weight: 600;
    }

    .panel {
        background: rgba(255,255,255,0.78);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--apple-border);
        border-radius: 24px;
        padding: 22px 22px 18px 22px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.05);
        margin-bottom: 18px;
    }

    .panel-desc {
        font-size: 13px;
        color: var(--apple-sub);
        margin-top: -4px;
        margin-bottom: 14px;
    }

    .cut-card {
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(0,0,0,0.07);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.04);
    }

    .cut-title {
        font-size: 21px;
        font-weight: 700;
        margin-bottom: 3px;
        letter-spacing: -0.02em;
    }

    .cut-sub {
        font-size: 12px;
        color: var(--apple-sub);
        margin-bottom: 12px;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--apple-border);
        border-radius: 20px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.03);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--apple-sub);
        font-weight: 500;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: var(--apple-text);
        letter-spacing: -0.03em;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        border-radius: 14px !important;
        border: 1px solid var(--apple-line) !important;
        background: rgba(255,255,255,0.94) !important;
        box-shadow: none !important;
    }

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within,
    div[data-baseweb="select"] > div:focus-within {
        border-color: rgba(0,113,227,0.45) !important;
        box-shadow: 0 0 0 4px rgba(0,113,227,0.10) !important;
    }

    label, .stRadio label, .stSelectbox label, .stTextInput label, .stTextArea label {
        color: var(--apple-text) !important;
        font-weight: 600 !important;
    }

    .stButton > button, .stDownloadButton > button {
        border-radius: 999px !important;
        min-height: 42px;
        border: 1px solid rgba(0,0,0,0.08) !important;
        background: rgba(255,255,255,0.94) !important;
        color: var(--apple-text) !important;
        font-weight: 600 !important;
        transition: all 0.18s ease;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-1px);
        border-color: rgba(0,0,0,0.12) !important;
        background: white !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--apple-blue) !important;
        color: white !important;
        border-color: var(--apple-blue) !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--apple-blue-hover) !important;
        border-color: var(--apple-blue-hover) !important;
    }

    div[data-testid="stInfo"] {
        border-radius: 18px;
        border: 1px solid rgba(0,113,227,0.16);
        background: rgba(0,113,227,0.06);
    }

    div[data-testid="stSuccess"] {
        border-radius: 18px;
    }

    .saved-empty {
        color: var(--apple-sub);
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="hero">
        <div style="display:flex; justify-content:space-between; gap:20px; align-items:flex-start; flex-wrap:wrap;">
            <div>
                <div class="eyebrow">REELS CAPTION WORKBENCH</div>
                <h1 class="hero-title">릴스 자막 초안 생성기</h1>
                <p class="hero-sub">입력 → 생성 → 검수/수정 → 확정 흐름에 맞춘 내부 업무용 초안 생성 화면</p>
                <div class="free-note">무료 데모 모드 · API Key 없이 동작</div>
            </div>
            <div class="pill" style="background:{meta['bg']}; color:{meta['fg']};">
                {STATUS_LABELS[st.session_state.status]}
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("예상 컷 수", st.session_state.get("cut_count", 5))
with m2:
    st.metric("생성된 컷", len(st.session_state.drafts))
with m3:
    st.metric("저장 버전", len(st.session_state.saved_versions))
with m4:
    st.metric("실행 모드", "FREE")

left, right = st.columns([0.94, 1.36], gap="large")

with left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("입력 영역")
    st.markdown('<div class="panel-desc">행사 정보와 홍보 포인트를 입력하면 규칙 기반으로 컷별 자막 초안을 생성합니다.</div>', unsafe_allow_html=True)

    st.text_input("행사명", key="event_name", placeholder="예: 여름 바캉스 특가전")
    st.text_input("행사 기간", key="event_period", placeholder="예: 2026.07.10 - 2026.07.14")
    st.text_input("행사 장소", key="event_place", placeholder="예: 스타필드 코엑스점")

    st.text_area(
        "홍보 포인트",
        key="promo_points",
        height=110,
        placeholder="쉼표, 줄바꿈으로 여러 개 입력\n예: 여름 한정 특가, 인기 브랜드 참여, 현장 체험존 운영",
    )
    st.text_area(
        "주력 상품",
        key="main_products",
        height=90,
        placeholder="예: 냉감 의류, 여행용 캐리어, 선케어 세트",
    )
    st.text_area(
        "이벤트/혜택",
        key="benefits",
        height=90,
        placeholder="예: 최대 30% 할인, 사은품 증정, 1+1",
    )
    st.text_area(
        "필수 포함 문구",
        key="required_lines",
        height=90,
        placeholder="예: 한정 수량 / 조기 품절 가능",
    )

    st.radio(
        "톤앤매너 선택",
        ["밝고 경쾌함", "신뢰감/정보형", "세일즈/강조형", "트렌디/숏폼형"],
        horizontal=True,
        key="tone",
    )
    st.selectbox(
        "스타일 템플릿",
        ["기본형", "혜택 강조형", "정보 전달형", "숏폼 몰입형"],
        key="style_template",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("영상 길이", ["15초", "20초", "30초", "45초"], key="video_length")
    with c2:
        st.number_input("예상 컷 수", min_value=3, max_value=10, value=5, step=1, key="cut_count")

    a1, a2 = st.columns(2)
    with a1:
        if st.button("초안 생성", type="primary", use_container_width=True):
            run_generation()
            st.rerun()
    with a2:
        if st.button("다시 생성", use_container_width=True):
            run_generation()
            st.rerun()

    st.divider()
    st.markdown("**생성 로그**")
    if st.session_state.generation_log:
        for msg in st.session_state.generation_log:
            st.write(f"- {msg}")
    else:
        st.caption("생성 전에는 로그가 표시되지 않습니다.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("결과 / 편집 영역")
    st.markdown('<div class="panel-desc">부분 수정과 부분 재생성을 중심으로 빠르게 최종안을 다듬을 수 있습니다.</div>', unsafe_allow_html=True)

    if not st.session_state.drafts:
        st.info("좌측 입력값을 채운 뒤 초안 생성을 누르면 컷별 자막 카드가 표시됩니다.")
    else:
        for idx, item in enumerate(st.session_state.drafts):
            st.markdown('<div class="cut-card">', unsafe_allow_html=True)
            st.markdown(f"<div class='cut-title'>컷 {item['id']}</div>", unsafe_allow_html=True)
            st.markdown("<div class='cut-sub'>부분 수정 / 부분 재생성 중심</div>", unsafe_allow_html=True)

            new_caption = st.text_area(
                "자막",
                value=item["caption"],
                key=f"caption_{idx}",
                height=95,
            )
            new_desc = st.text_area(
                "컷 설명",
                value=item["description"],
                key=f"desc_{idx}",
                height=85,
            )

            if new_caption != item["caption"] or new_desc != item["description"]:
                st.session_state.drafts[idx]["caption"] = new_caption
                st.session_state.drafts[idx]["description"] = new_desc
                st.session_state.status = "editing"

            b1, b2, b3, b4, b5 = st.columns(5)
            with b1:
                if st.button("↑ 이동", key=f"up_{idx}", use_container_width=True):
                    move_cut(idx, -1)
                    st.rerun()
            with b2:
                if st.button("↓ 이동", key=f"down_{idx}", use_container_width=True):
                    move_cut(idx, 1)
                    st.rerun()
            with b3:
                if st.button("재생성", key=f"regen_{idx}", use_container_width=True):
                    regenerate_single_cut(idx)
                    st.rerun()
            with b4:
                if st.button("+ 추가", key=f"add_{idx}", use_container_width=True):
                    add_cut(idx)
                    st.rerun()
            with b5:
                if st.button("삭제", key=f"del_{idx}", use_container_width=True):
                    remove_cut(idx)
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        st.divider()
        full_text = export_text(st.session_state.drafts)

        x1, x2, x3, x4 = st.columns(4)
        with x1:
            st.download_button(
                "텍스트 다운로드",
                data=full_text,
                file_name="reels_caption_draft.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with x2:
            if st.button("전체 복사", use_container_width=True):
                st.session_state.show_export_text = True
        with x3:
            if st.button("저장", use_container_width=True):
                save_current_version()
                st.success("현재 초안이 저장되었습니다.")
        with x4:
            if st.button("최종 확정", type="primary", use_container_width=True):
                st.session_state.status = "finalized"
                st.success("최종 자막안이 확정되었습니다.")

        st.markdown("### 최종 결과 미리보기")
        st.text_area("export_text", value=full_text, height=220, label_visibility="collapsed")

        if st.session_state.show_export_text:
            st.code(full_text, language="text")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("저장된 결과")

if st.session_state.saved_versions:
    for i, version in enumerate(reversed(st.session_state.saved_versions), start=1):
        with st.expander(f"저장본 {i} · {version['saved_at']}"):
            st.write(f"상태: {STATUS_LABELS.get(version['status'], version['status'])}")
            st.json(version["payload"], expanded=False)
            st.text(export_text(version["drafts"]))
else:
    st.markdown('<div class="saved-empty">저장된 결과가 없습니다.</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
'''

requirements = """streamlit>=1.44.0
"""

base = Path("/mnt/data")
(base / "app.py").write_text(app_code, encoding="utf-8")
(base / "requirements.txt").write_text(requirements, encoding="utf-8")

print("Created:", base / "app.py")
print("Created:", base / "requirements.txt")

