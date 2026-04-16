import streamlit as st
import anthropic
import json
import re
from copy import deepcopy

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="릴스 자막 초안 생성기",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    /* ── 전체 배경: 따뜻한 오프화이트 ── */
    .stApp {
        background: #f5f4f0 !important;
        color: #1a1a1a !important;
        font-family: 'Noto Sans KR', sans-serif;
    }
    .stApp > header { background: transparent !important; }

    /* Streamlit 기본 배경 오버라이드 */
    .main .block-container {
        background: transparent !important;
        padding-top: 1.5rem !important;
    }

    /* ── 헤더 ── */
    .header-bar {
        background: #ffffff;
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1.5px solid #e8e6e0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }
    .header-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 800;
        color: #111;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .header-sub {
        font-size: 0.78rem;
        color: #888;
        margin-top: 3px;
        letter-spacing: 0.03em;
    }

    /* ── 상태 배지 ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    .status-ready   { background: #f0f0ee; color: #999; border: 1.5px solid #ddd; }
    .status-done    { background: #edfaf3; color: #1a9e5c; border: 1.5px solid #a8e6c3; }
    .status-editing { background: #eef4ff; color: #2563eb; border: 1.5px solid #bfcfff; }
    .status-final   { background: #fdf0ff; color: #7c3aed; border: 1.5px solid #d8b4fe; }

    /* ── 섹션 레이블 ── */
    .section-label {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        color: #aaa;
        text-transform: uppercase;
        margin-bottom: 12px;
        margin-top: 4px;
    }

    /* ── 입력 패널 래퍼 ── */
    .input-panel {
        background: #ffffff;
        border-radius: 14px;
        padding: 22px 20px;
        border: 1.5px solid #e8e6e0;
        box-shadow: 0 1px 6px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }

    /* ── Streamlit 입력 필드 ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #fafaf8 !important;
        border: 1.5px solid #e2e0da !important;
        border-radius: 8px !important;
        color: #1a1a1a !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        font-size: 0.88rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
    }
    .stTextInput label, .stTextArea label {
        color: #555 !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }

    /* selectbox */
    .stSelectbox > div > div {
        background: #fafaf8 !important;
        border: 1.5px solid #e2e0da !important;
        border-radius: 8px !important;
        color: #1a1a1a !important;
    }
    .stSelectbox label { color: #555 !important; font-size: 0.82rem !important; font-weight: 600 !important; }

    /* radio */
    .stRadio label { color: #444 !important; font-size: 0.83rem !important; }
    .stRadio > div { gap: 6px !important; }

    /* ── 버튼 ── */
    .stButton > button {
        border-radius: 9px !important;
        font-weight: 700 !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        font-size: 0.84rem !important;
        transition: all 0.18s !important;
        border: 1.5px solid transparent !important;
    }
    /* primary 버튼 */
    .stButton > button[kind="primary"] {
        background: #111 !important;
        color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #333 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.18) !important;
    }
    /* secondary 버튼 */
    .stButton > button[kind="secondary"] {
        background: #fff !important;
        color: #333 !important;
        border-color: #ddd !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #aaa !important;
        background: #f5f4f0 !important;
    }

    /* ── 구분선 ── */
    hr { border-color: #e8e6e0 !important; margin: 18px 0 !important; }

    /* ── expander (컷 카드) ── */
    .stExpander {
        background: #ffffff !important;
        border: 1.5px solid #e8e6e0 !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
        overflow: hidden !important;
    }
    .stExpander:hover {
        border-color: #6366f1 !important;
        box-shadow: 0 2px 10px rgba(99,102,241,0.10) !important;
    }
    .stExpander summary {
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #222 !important;
        padding: 14px 18px !important;
        background: #ffffff !important;
    }
    .stExpander > div > div {
        background: #fafaf8 !important;
        padding: 14px 18px !important;
    }

    /* ── 진행 메시지 ── */
    .progress-msg {
        background: #eef4ff;
        border: 1.5px solid #c3d4ff;
        border-radius: 10px;
        padding: 14px 18px;
        color: #2563eb;
        font-size: 0.88rem;
        font-weight: 600;
        margin: 12px 0;
    }

    /* ── 빈 상태 ── */
    .empty-state {
        text-align: center;
        padding: 70px 20px;
        color: #bbb;
        background: #fff;
        border-radius: 14px;
        border: 1.5px dashed #ddd;
    }
    .empty-icon { font-size: 2.8rem; margin-bottom: 14px; }
    .empty-text { font-size: 0.88rem; line-height: 1.7; color: #aaa; }

    /* ── success/warning/error 메시지 ── */
    .stAlert { border-radius: 10px !important; font-size: 0.86rem !important; }

    /* ── download button ── */
    .stDownloadButton > button {
        background: #fff !important;
        color: #333 !important;
        border: 1.5px solid #ddd !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }
    .stDownloadButton > button:hover {
        border-color: #6366f1 !important;
        color: #6366f1 !important;
        background: #eef4ff !important;
    }

    /* ── 코드 블록 ── */
    .stCodeBlock { border-radius: 10px !important; }

    /* 히스토리 뱃지 */
    .history-ver {
        display: inline-block;
        background: #f0f0ee;
        color: #666;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ─────────────────────────────────────────
def init_state():
    defaults = {
        "cuts": [],           # [{caption, desc, confirmed}]
        "status": "ready",    # ready | done | editing | final
        "history": [],        # 버전 히스토리
        "regen_idx": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── 상태 배지 ────────────────────────────────────────────────
STATUS_LABEL = {
    "ready":   ("초안 작성 전", "status-ready"),
    "done":    ("생성 완료",    "status-done"),
    "editing": ("수정 중",      "status-editing"),
    "final":   ("확정 완료",    "status-final"),
}

# ── 헤더 ─────────────────────────────────────────────────────
label, cls = STATUS_LABEL[st.session_state.status]
st.markdown(f"""
<div class="header-bar">
  <div>
    <div class="header-title">🎬 릴스 자막 초안 생성기</div>
    <div class="header-sub">입력 → 생성 → 검수 → 확정</div>
  </div>
  <span class="status-badge {cls}">{label}</span>
</div>
""", unsafe_allow_html=True)

# ── AI 생성 함수 ──────────────────────────────────────────────
def build_prompt(info: dict, cut_count: int) -> str:
    return f"""당신은 숏폼 영상(릴스/쇼츠) 자막 전문 카피라이터입니다.
아래 행사 정보를 바탕으로 정확히 {cut_count}개의 컷 자막과 컷 설명을 작성하세요.

[행사 정보]
- 행사명: {info['event_name']}
- 기간: {info['period']}
- 장소: {info['place']}
- 홍보 포인트: {info['points']}
- 주력 상품: {info['products']}
- 이벤트/혜택: {info['benefits']}
- 필수 포함 문구: {info['must_include']}
- 톤앤매너: {info['tone']}
- 영상 길이: {info['duration']}초

[규칙]
1. 자막은 짧고 강렬하게 (최대 20자)
2. 첫 컷은 시선을 끄는 후킹 문장
3. 마지막 컷은 CTA (행동 유도)
4. 중간 컷은 혜택·상품 소개 순서로
5. 컷 설명은 촬영 가이드 (어떤 장면인지)
6. 반드시 필수 포함 문구를 어느 컷에 넣을 것

반드시 아래 JSON 형식만 출력하세요. 다른 텍스트 없이:
{{
  "cuts": [
    {{"caption": "자막 텍스트", "desc": "컷 설명"}},
    ...
  ]
}}"""

def call_ai(prompt: str) -> list[dict]:
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    # JSON 파싱
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        data = json.loads(match.group())
        return [{"caption": c["caption"], "desc": c["desc"], "confirmed": False}
                for c in data["cuts"]]
    raise ValueError("JSON 파싱 실패: " + raw[:200])

def call_ai_single(caption: str, desc: str, info: dict) -> dict:
    """단일 컷 재생성"""
    client = anthropic.Anthropic()
    prompt = f"""릴스 자막 1개를 재작성하세요.

행사: {info['event_name']} / 톤: {info['tone']}
기존 자막: {caption}
기존 설명: {desc}

더 임팩트 있게 바꿔주세요. 반드시 아래 JSON만 출력:
{{"caption": "새 자막", "desc": "새 컷 설명"}}"""
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"caption": caption, "desc": desc}

# ── 레이아웃 ─────────────────────────────────────────────────
left, right = st.columns([1, 1.4], gap="large")

# ═══════════════════════════════════════════════════════════════
# 좌측: 입력 패널
# ═══════════════════════════════════════════════════════════════
with left:
    st.markdown('<div class="section-label">📋 행사 정보 입력</div>', unsafe_allow_html=True)

    with st.container():
        event_name = st.text_input("행사명 *", placeholder="예: 2025 봄 페스티벌 세일")
        col1, col2 = st.columns(2)
        with col1:
            period = st.text_input("행사 기간 *", placeholder="예: 4/18~4/20")
        with col2:
            place = st.text_input("행사 장소", placeholder="예: 강남 본점")

        points = st.text_area(
            "홍보 포인트 *",
            placeholder="예: 역대 최대 할인, 봄 신상품 출시, 한정 수량",
            height=80,
        )
        products = st.text_input("주력 상품", placeholder="예: 봄 재킷, 린넨 셔츠")
        benefits = st.text_area(
            "이벤트 / 혜택",
            placeholder="예: 3만원 이상 구매 시 5천원 쿠폰, 선착순 100명 사은품",
            height=70,
        )
        must_include = st.text_input(
            "필수 포함 문구",
            placeholder="예: 지금 바로 확인하세요!",
        )

    st.markdown("---")
    st.markdown('<div class="section-label">⚙️ 생성 옵션</div>', unsafe_allow_html=True)

    tone = st.radio(
        "톤앤매너",
        ["트렌디·캐주얼", "신뢰·정보형", "감성·스토리", "유머·B급"],
        horizontal=True,
    )
    col3, col4 = st.columns(2)
    with col3:
        duration = st.selectbox("영상 길이", ["15초", "30초", "60초"])
    with col4:
        cut_count = st.selectbox("예상 컷 수", [5, 6, 7, 8, 9, 10], index=1)

    st.markdown("---")

    # ── 액션 버튼 ──
    b1, b2 = st.columns(2)
    generate_clicked = b1.button("✨ 초안 생성", use_container_width=True, type="primary")
    regen_all_clicked = b2.button("🔄 다시 생성", use_container_width=True,
                                  disabled=len(st.session_state.cuts) == 0)

    info = {
        "event_name": event_name, "period": period, "place": place,
        "points": points, "products": products, "benefits": benefits,
        "must_include": must_include, "tone": tone,
        "duration": duration.replace("초", ""),
    }

    # 생성 실행
    if generate_clicked or regen_all_clicked:
        if not event_name or not period or not points:
            st.warning("⚠️ 행사명, 기간, 홍보 포인트는 필수 입력 항목입니다.")
        else:
            msgs = ["행사 포인트 정리 중 ✦", "자막 흐름 구성 중 ✦", "컷 순서 최적화 중 ✦"]
            progress_box = st.empty()
            try:
                for m in msgs:
                    progress_box.markdown(f'<div class="progress-msg">⏳ {m}</div>',
                                          unsafe_allow_html=True)
                prompt = build_prompt(info, cut_count)
                cuts = call_ai(prompt)
                # 히스토리 저장
                if st.session_state.cuts:
                    st.session_state.history.append(deepcopy(st.session_state.cuts))
                st.session_state.cuts = cuts
                st.session_state.status = "done"
                progress_box.empty()
                st.success("✅ 자막 초안이 생성되었습니다!")
            except Exception as e:
                progress_box.empty()
                st.error(f"❌ 입력 정보를 확인 후 다시 시도해주세요.\n({e})")

    # 전체 복사 / 다운로드
    if st.session_state.cuts:
        st.markdown("---")
        st.markdown('<div class="section-label">📤 내보내기</div>', unsafe_allow_html=True)
        all_text = "\n\n".join(
            f"[컷 {i+1}]\n자막: {c['caption']}\n설명: {c['desc']}"
            for i, c in enumerate(st.session_state.cuts)
        )
        ec1, ec2 = st.columns(2)
        ec1.download_button(
            "⬇️ 텍스트 다운로드",
            data=all_text,
            file_name="reels_captions.txt",
            mime="text/plain",
            use_container_width=True,
        )
        if ec2.button("📋 전체 복사용 보기", use_container_width=True):
            st.code(all_text, language=None)

        if st.button("✅ 최종 확정", use_container_width=True, type="primary"):
            st.session_state.status = "final"
            st.success("🎉 자막이 최종 확정되었습니다!")

# ═══════════════════════════════════════════════════════════════
# 우측: 결과 패널
# ═══════════════════════════════════════════════════════════════
with right:
    st.markdown('<div class="section-label">🎞️ 컷별 자막 초안</div>', unsafe_allow_html=True)

    cuts = st.session_state.cuts

    if not cuts:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">🎬</div>
          <div class="empty-text">좌측에 행사 정보를 입력하고<br><b>초안 생성</b>을 눌러주세요</div>
        </div>""", unsafe_allow_html=True)
    else:
        if st.session_state.status != "final":
            st.session_state.status = "editing"

        for i, cut in enumerate(cuts):
            with st.expander(f"✦ 컷 {i+1}  —  {cut['caption']}", expanded=True):
                new_caption = st.text_input(
                    "자막",
                    value=cut["caption"],
                    key=f"cap_{i}",
                    label_visibility="collapsed",
                )
                new_desc = st.text_input(
                    "컷 설명",
                    value=cut["desc"],
                    key=f"desc_{i}",
                    label_visibility="collapsed",
                )

                # 변경 반영
                if new_caption != cut["caption"] or new_desc != cut["desc"]:
                    st.session_state.cuts[i]["caption"] = new_caption
                    st.session_state.cuts[i]["desc"] = new_desc

                col_a, col_b, col_c = st.columns(3)

                # 부분 재생성
                if col_a.button("🔁 재생성", key=f"regen_{i}", use_container_width=True):
                    with st.spinner("재생성 중..."):
                        try:
                            result = call_ai_single(cut["caption"], cut["desc"], info)
                            st.session_state.cuts[i]["caption"] = result["caption"]
                            st.session_state.cuts[i]["desc"] = result["desc"]
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                # 컷 삭제
                if col_b.button("🗑️ 삭제", key=f"del_{i}", use_container_width=True):
                    st.session_state.cuts.pop(i)
                    st.rerun()

                # 위로 이동
                if col_c.button("⬆️ 위로", key=f"up_{i}",
                                 use_container_width=True, disabled=(i == 0)):
                    cuts[i], cuts[i-1] = cuts[i-1], cuts[i]
                    st.rerun()

        # 컷 추가
        st.markdown("---")
        if st.button("＋ 컷 추가", use_container_width=True):
            st.session_state.cuts.append({
                "caption": "새 자막을 입력하세요",
                "desc": "컷 설명을 입력하세요",
                "confirmed": False,
            })
            st.rerun()

        # 히스토리
        if st.session_state.history:
            with st.expander(f"🕓 버전 히스토리 ({len(st.session_state.history)}개)"):
                for vi, version in enumerate(reversed(st.session_state.history)):
                    st.markdown(f"**버전 {len(st.session_state.history) - vi}**")
                    for ci, c in enumerate(version):
                        st.markdown(f"- 컷{ci+1}: {c['caption']}")
                    if st.button(f"이 버전으로 되돌리기", key=f"restore_{vi}"):
                        st.session_state.cuts = deepcopy(version)
                        st.rerun()
                    st.markdown("---")
