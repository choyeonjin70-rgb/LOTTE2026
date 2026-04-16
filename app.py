import json
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


def init_state() -> None:
    if "status" not in st.session_state:
        st.session_state.status = "idle"
    if "drafts" not in st.session_state:
        st.session_state.drafts = []
    if "saved_versions" not in st.session_state:
        st.session_state.saved_versions = []
    if "generation_log" not in st.session_state:
        st.session_state.generation_log = []
    if "last_input_payload" not in st.session_state:
        st.session_state.last_input_payload = {}
    if "copied_text" not in st.session_state:
        st.session_state.copied_text = ""


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
    promo_points = payload["홍보 포인트"] or ["놓치면 아쉬운 혜택"]
    products = payload["주력 상품"] or ["인기 상품"]
    benefits = payload["이벤트/혜택"] or ["특별 혜택"]
    required = payload["필수 포함 문구"]

    candidate_pool = [
        {
            "caption": f"{period}, {event_name} 꼭 체크하세요",
            "description": f"{place} 전경과 행사 타이틀을 보여주는 오프닝 컷",
        },
        {
            "caption": f"{products[0]} 중심으로 지금 가장 반응 좋은 포인트만 담았어요",
            "description": f"{products[0]} 클로즈업과 핵심 특징을 빠르게 보여주는 컷",
        },
        {
            "caption": f"{benefits[0]} 혜택으로 체감되는 매력을 강조해보세요",
            "description": "혜택 문구와 가격/혜택 강조 그래픽이 함께 나오는 컷",
        },
        {
            "caption": f"{promo_points[0]} 포인트를 한눈에 전달하는 핵심 설명 컷",
            "description": "현장 분위기 또는 사용 장면을 보여주는 설명 컷",
        },
        {
            "caption": "지금 바로 확인하고 원하는 혜택을 챙겨보세요",
            "description": "CTA 중심 마무리 컷",
        },
    ]

    tone_map = {
        "밝고 경쾌함": "리듬감 있게",
        "신뢰감/정보형": "명확하고 또렷하게",
        "세일즈/강조형": "임팩트 있게",
        "트렌디/숏폼형": "짧고 감각적으로",
    }
    tone_prefix = tone_map.get(tone, "자연스럽게")

    drafts: List[Dict] = []
    for idx in range(target_count):
        base = candidate_pool[idx % len(candidate_pool)]
        caption = f"{tone_prefix} {base['caption']}"
        description = f"{style} 스타일로 {base['description']}"

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
    new_cut = {
        "id": after_index + 2,
        "caption": "새 컷 자막을 입력하세요",
        "description": "새 컷 설명을 입력하세요",
    }
    st.session_state.drafts.insert(after_index + 1, new_cut)
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
    version = {
        "saved_at": str(date.today()),
        "status": st.session_state.status,
        "payload": deepcopy(st.session_state.last_input_payload),
        "drafts": deepcopy(st.session_state.drafts),
    }
    st.session_state.saved_versions.append(version)


def run_generation() -> None:
    payload = build_input_payload()
    st.session_state.last_input_payload = payload
    st.session_state.generation_log = ["행사 포인트 정리 중...", "자막 흐름 구성 중..."]

    with st.spinner("AI가 초안을 생성하고 있습니다..."):
        drafts = fallback_generate_drafts(payload, payload["예상 컷 수"])

    st.session_state.drafts = drafts
    st.session_state.status = "generated"
    st.session_state.copied_text = export_text(drafts)


init_state()

st.title("🎬 릴스 자막 초안 생성기")
status_col, info_col = st.columns([1, 3])
with status_col:
    st.metric("현재 상태", STATUS_LABELS[st.session_state.status])
with info_col:
    st.caption("입력 → 생성 → 검수/수정 → 확정 흐름에 맞춘 내부 업무용 초안 생성 화면")

left, right = st.columns([1, 1.25], gap="large")

with left:
    st.subheader("입력 영역")
    st.text_input("행사명", key="event_name", placeholder="예: 여름 바캉스 특가전")
    st.text_input("행사 기간", key="event_period", placeholder="예: 2026.07.10 - 2026.07.14")
    st.text_input("행사 장소", key="event_place", placeholder="예: 스타필드 코엑스점")
    st.text_area(
        "홍보 포인트",
        key="promo_points",
        placeholder="쉼표, 줄바꿈으로 여러 개 입력\n예: 여름 한정 특가, 인기 브랜드 참여, 현장 체험존 운영",
        height=100,
    )
    st.text_area(
        "주력 상품",
        key="main_products",
        placeholder="예: 냉감 의류, 여행용 캐리어, 선케어 세트",
        height=80,
    )
    st.text_area(
        "이벤트/혜택",
        key="benefits",
        placeholder="예: 최대 30% 할인, 사은품 증정, 1+1",
        height=80,
    )
    st.text_area(
        "필수 포함 문구",
        key="required_lines",
        placeholder="예: 한정 수량 / 조기 품절 가능",
        height=80,
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

    action1, action2 = st.columns(2)
    with action1:
        if st.button("초안 생성", use_container_width=True, type="primary"):
            run_generation()
            st.rerun()
    with action2:
        if st.button("다시 생성", use_container_width=True):
            run_generation()
            st.rerun()

    st.divider()
    st.subheader("생성 로그")
    if st.session_state.generation_log:
        for msg in st.session_state.generation_log:
            st.write(f"- {msg}")
    else:
        st.caption("생성 전에는 로그가 표시되지 않습니다.")

with right:
    st.subheader("결과 / 편집 영역")

    if not st.session_state.drafts:
        st.info("좌측 입력값을 채운 뒤 초안 생성을 누르면 컷별 자막 카드가 표시됩니다.")
    else:
        for idx, item in enumerate(st.session_state.drafts):
            with st.container(border=True):
                top1, top2 = st.columns([3, 2])
                with top1:
                    st.markdown(f"### 컷 {item['id']}")
                with top2:
                    st.caption("부분 수정 / 부분 재생성 중심")

                caption_key = f"caption_{idx}"
                desc_key = f"desc_{idx}"

                new_caption = st.text_area(
                    "자막",
                    value=item["caption"],
                    key=caption_key,
                    height=90,
                )
                new_desc = st.text_area(
                    "컷 설명",
                    value=item["description"],
                    key=desc_key,
                    height=80,
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

        st.divider()
        full_text = export_text(st.session_state.drafts)
        st.session_state.copied_text = full_text

        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.download_button(
                "텍스트 다운로드",
                data=full_text,
                file_name="reels_caption_draft.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with a2:
            if st.button("전체 복사", use_container_width=True):
                st.code(full_text, language="text")
        with a3:
            if st.button("저장", use_container_width=True):
                save_current_version()
                st.success("현재 초안이 저장되었습니다.")
        with a4:
            if st.button("최종 확정", use_container_width=True, type="primary"):
                st.session_state.status = "finalized"
                st.success("최종 자막안이 확정되었습니다.")

        st.text_area("최종 결과 미리보기", value=full_text, height=220)

st.divider()
st.subheader("저장된 결과")
if st.session_state.saved_versions:
    for i, version in enumerate(reversed(st.session_state.saved_versions), start=1):
        with st.expander(f"저장본 {i} · {version['saved_at']}"):
            st.write(f"상태: {STATUS_LABELS.get(version['status'], version['status'])}")
            st.json(version["payload"], expanded=False)
            st.text(export_text(version["drafts"]))
else:
    st.caption("저장된 결과가 없습니다.")
