import json
import math
import random
from datetime import date
from typing import Dict, List

import streamlit as st


st.set_page_config(
    page_title="릴스 자막 초안 생성기",
    page_icon="🎬",
    layout="wide",
)

# -----------------------------
# Status
# -----------------------------
STATUS_BEFORE = "초안 작성 전"
STATUS_DONE = "생성 완료"
STATUS_EDITING = "수정 중"
STATUS_CONFIRMED = "확정 완료"

# -----------------------------
# Fixed Style Rules
# -----------------------------
ACCOUNT_STYLE_NAME = "롯데몰 잠실점 SNS 전담 카피라이터 톤"

STYLE_RULES = {
    "hook_types": ["question", "scarcity", "visual"],
    "cta_types": ["visit", "recommend", "urgent"],
    "max_line_length": 18,
    "use_emoji": False,
    "one_cut_one_info": True,
    "location_anchor_required": True,
    "urgency_required_near_end": True,
    "cta_at_last_cut": True,
}

CUT_DESCRIPTION_POOL = [
    "행사장 전경 노출",
    "브랜드 입구 또는 간판 노출",
    "위치 정보가 보이는 화면",
    "주력 상품 클로즈업",
    "디테일 샷",
    "가격/혜택 안내 화면",
    "현장 반응 또는 체험 장면",
    "마무리 CTA 화면",
]


# -----------------------------
# Session
# -----------------------------
def init_session() -> None:
    defaults = {
        "status": STATUS_BEFORE,
        "drafts": [],
        "saved_results": [],
        "confirmed_result": None,
        "generation_count": 0,
        "inputs": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# -----------------------------
# Basic Helpers
# -----------------------------
def clean_text(text: str) -> str:
    return text.strip()


def parse_multiline_items(text: str) -> List[str]:
    items = []
    for raw in text.replace(",", "\n").split("\n"):
        item = raw.strip(" -•\t")
        if item:
            items.append(item)
    return items


def split_long_text(text: str, max_len: int = 18) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text

    words = text.split()
    if len(words) <= 1:
        mid = max(1, len(text) // 2)
        return text[:mid] + "\n" + text[mid:]

    line1 = ""
    line2_words = []

    for word in words:
        candidate = (line1 + " " + word).strip()
        if len(candidate) <= max_len:
            line1 = candidate
        else:
            line2_words.append(word)

    if not line2_words:
        return text

    line2 = " ".join(line2_words)

    if len(line2) > max_len and " " in line2:
        words2 = line2.split()
        line2a = ""
        line2b = []
        for word in words2:
            candidate = (line2a + " " + word).strip()
            if len(candidate) <= max_len:
                line2a = candidate
            else:
                line2b.append(word)
        if line2b:
            return f"{line1}\n{line2a}\n{' '.join(line2b)}"
        return f"{line1}\n{line2a}"

    return f"{line1}\n{line2}"


def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            result.append(item)
            seen.add(key)
    return result


def estimate_cut_count(video_length_sec: int, requested_cut_count: int) -> int:
    if requested_cut_count > 0:
        return requested_cut_count
    return max(5, min(10, math.ceil(video_length_sec / 4)))


def extract_anchor_place(inputs: Dict) -> str:
    place = clean_text(inputs.get("event_place", ""))
    floor = clean_text(inputs.get("floor", ""))

    if place and floor:
        return f"{place} {floor}"
    if place:
        return place
    if floor:
        return floor
    return "잠실"


def pick_subject(inputs: Dict, fallback: str = "이거") -> str:
    candidates = [
        clean_text(inputs.get("event_name", "")),
        clean_text(inputs.get("main_product", "")),
        clean_text(inputs.get("event_benefits", "")),
    ]
    candidates = [c for c in candidates if c]
    return random.choice(candidates) if candidates else fallback


# -----------------------------
# Style-driven Variation
# -----------------------------
def choose_hook_type(inputs: Dict) -> str:
    style_template = inputs.get("style_template", "기본형")

    if style_template == "희소성 강조형":
        return random.choice(["scarcity", "scarcity", "question"])
    if style_template == "질문형 훅 강조형":
        return random.choice(["question", "question", "visual"])
    if style_template == "비주얼 훅 강조형":
        return random.choice(["visual", "visual", "question"])

    if inputs.get("price_or_number"):
        return random.choice(["question", "scarcity"])
    if inputs.get("limited_info"):
        return random.choice(["scarcity", "visual"])
    return random.choice(["question", "scarcity", "visual"])


def choose_cta_type(inputs: Dict) -> str:
    if inputs.get("limited_info"):
        return random.choice(["urgent", "visit"])
    return random.choice(["visit", "recommend", "urgent"])


def build_location_variants(inputs: Dict) -> List[str]:
    event_name = clean_text(inputs.get("event_name", ""))
    place = clean_text(inputs.get("event_place", ""))
    floor = clean_text(inputs.get("floor", ""))

    variants = []

    if place and floor:
        variants.extend([
            f"{place} {floor}에서 진행 중",
            f"{place} {floor}에 있음",
            f"{place} {floor} 쪽에서 만날 수 있음",
            f"{place} {floor}로 가면 됨",
        ])

    if place:
        variants.extend([
            f"{place}에서 확인 가능",
            f"{place} 쪽으로 가면 됨",
            f"{place}에서 만나볼 수 있음",
        ])

    if floor:
        variants.extend([
            f"{floor}에서 진행 중",
            f"{floor} 쪽에 있음",
        ])

    if event_name and place:
        variants.extend([
            f"{event_name} {place}에서 진행 중",
            f"{event_name} {place} 쪽에서 볼 수 있음",
        ])

    if not variants:
        variants = [
            "잠실에서 바로 확인 가능",
            "잠실 쪽에서 만나볼 수 있음",
            "잠실에서 진행 중",
        ]

    return dedupe_keep_order(variants)


def add_soft_reaction(line: str) -> str:
    reactions = [
        "반응 올 만함",
        "생각보다 괜찮음",
        "꽤 눈에 들어옴",
        "현장감 잘 사는 편",
        "디테일 보는 맛 있음",
    ]
    if "\n" in line:
        return line
    if len(line) <= 11 and random.random() < 0.22:
        return f"{line}\n{random.choice(reactions)}"
    return line


# -----------------------------
# Caption Generation
# -----------------------------
def generate_hook_line(inputs: Dict) -> str:
    hook_type = choose_hook_type(inputs)

    event_name = clean_text(inputs.get("event_name", ""))
    main_product = clean_text(inputs.get("main_product", ""))
    benefit = clean_text(inputs.get("event_benefits", ""))
    number = clean_text(inputs.get("price_or_number", ""))
    place_anchor = extract_anchor_place(inputs)

    subject = pick_subject(inputs)

    if hook_type == "question":
        patterns = [
            f"{subject} 들어온 거 아시나요?",
            f"{subject} 지금 뜬 거 아세요?",
            f"{place_anchor}에 {subject} 생긴 거 아시나요?",
            f"{subject} 여기서 하는 거 알고 계셨나요?",
            f"{event_name or subject} 보신 분 있나요?",
        ]
        line = random.choice([p for p in patterns if p.strip()])
        return split_long_text(line, STYLE_RULES["max_line_length"])

    if hook_type == "scarcity":
        if number:
            patterns = [
                f"{number} 포인트부터 강한데",
                f"{subject} {number}로 주목받는 중",
                f"{number} 규모면 눈길 갈 만함",
            ]
        else:
            patterns = [
                f"{place_anchor}에서 보기 좋은 타이밍",
                f"{subject} 지금 잠실에서 만날 수 있음",
                f"{subject} 이 시점에 나온 게 큼",
                f"{subject} 놓치기엔 아까운 편",
            ]
        line = random.choice(patterns)
        return split_long_text(line, STYLE_RULES["max_line_length"])

    patterns = [
        f"{subject} 비주얼 꽤 강한데",
        f"{subject} 보자마자 반응 옴",
        f"{subject} 생각보다 더 괜찮은데",
        f"{subject} 눈에 바로 들어오는 편",
        f"{main_product or subject} 존재감 확실한데",
    ]
    line = random.choice([p for p in patterns if p.strip()])
    return split_long_text(line, STYLE_RULES["max_line_length"])


def generate_location_line(inputs: Dict) -> str:
    variants = build_location_variants(inputs)
    return split_long_text(random.choice(variants), STYLE_RULES["max_line_length"])


def build_middle_sequence(inputs: Dict, total_cuts: int) -> List[str]:
    details = []

    promo_points = inputs.get("promo_points", [])
    detail_items = inputs.get("detail_items", [])
    main_product = clean_text(inputs.get("main_product", ""))
    event_benefits = clean_text(inputs.get("event_benefits", ""))
    number = clean_text(inputs.get("price_or_number", ""))
    place_anchor = extract_anchor_place(inputs)

    if main_product:
        details.extend([
            f"{main_product} 중심으로 구성됨",
            f"{main_product} 먼저 체크해도 됨",
            f"{main_product}부터 눈에 들어옴",
        ])

    for point in promo_points:
        point = clean_text(point)
        if not point:
            continue
        details.extend([
            point,
            f"{point} 포인트가 확실함",
            f"{point} 쪽으로 반응 올 만함",
        ])

    for item in detail_items:
        item = clean_text(item)
        if not item:
            continue
        details.extend([
            item,
            f"{item} 디테일도 있음",
            f"{item}까지 같이 보게 됨",
        ])

    if event_benefits:
        details.extend([
            event_benefits,
            f"{event_benefits}까지 챙길 수 있음",
            f"{event_benefits} 포인트도 괜찮음",
        ])

    if number:
        details.extend([
            number,
            f"{number} 정도면 화제성 있음",
            f"{number} 수치가 바로 눈에 띔",
        ])

    if place_anchor:
        details.extend([
            f"{place_anchor}에서 확인 가능",
            f"{place_anchor} 쪽으로 가면 됨",
        ])

    details = dedupe_keep_order(details)
    details = [split_long_text(item, STYLE_RULES["max_line_length"]) for item in details]

    middle_room = max(1, total_cuts - 4)
    return details[:middle_room]


def generate_urgency_line(inputs: Dict) -> str:
    limited_info = clean_text(inputs.get("limited_info", ""))
    number = clean_text(inputs.get("price_or_number", ""))
    benefit = clean_text(inputs.get("event_benefits", ""))
    main_product = clean_text(inputs.get("main_product", ""))

    if limited_info:
        patterns = [
            limited_info,
            f"{limited_info}라 타이밍 중요함",
            f"{limited_info}라 빨리 보는 게 좋음",
            f"{limited_info}라 서두르는 쪽이 맞음",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    if number:
        patterns = [
            f"{number} 포인트라 더 빨리 볼 만함",
            f"{number} 기준으로도 화제성 충분함",
            f"{number}면 늦기 전에 보는 게 맞음",
            f"{number} 스케일이면 타이밍이 중요함",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    if benefit:
        patterns = [
            f"{benefit} 끝나기 전에 가야 함",
            f"{benefit} 있을 때 보는 게 좋음",
            f"{benefit} 타이밍 놓치면 아쉬움",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    if main_product:
        patterns = [
            f"{main_product} 관심 있으면 빨리 가야 함",
            f"{main_product}는 타이밍 맞을 때 보는 게 좋음",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    patterns = [
        "이럴 때 가줘야 함",
        "지금 타이밍에 보는 게 맞음",
        "늦기 전에 들러야 함",
        "지금 아니면 아쉬울 수 있음",
    ]
    return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])


def generate_cta_line(inputs: Dict) -> str:
    required_phrase = clean_text(inputs.get("required_phrase", ""))
    place = clean_text(inputs.get("event_place", ""))
    event_name = clean_text(inputs.get("event_name", ""))
    main_product = clean_text(inputs.get("main_product", ""))

    if required_phrase:
        return split_long_text(required_phrase, STYLE_RULES["max_line_length"])

    cta_type = choose_cta_type(inputs)

    target = None
    for candidate in [event_name, main_product, place]:
        if candidate:
            target = candidate
            break
    if not target:
        target = "여기"

    if cta_type == "visit":
        patterns = [
            f"{target} 한번 들러보세요",
            f"{target} 쪽으로 놀러 오세요",
            f"{target} 직접 보러 가보세요",
            f"{target} 현장으로 가보셔도 좋음",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    if cta_type == "recommend":
        patterns = [
            f"{target} 꽤 추천드릴 만함",
            f"{target} 가보시는 거 추천드립니다",
            f"{target} 관심 있으면 체크해보세요",
            f"{target} 한번 봐두셔도 좋음",
        ]
        return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])

    patterns = [
        f"{target} 지금 가보셔야 합니다",
        f"{target} 늦기 전에 보셔야 함",
        f"{target} 타이밍 맞을 때 가야 함",
        f"{target} 지금 체크하는 쪽이 맞음",
    ]
    return split_long_text(random.choice(patterns), STYLE_RULES["max_line_length"])


def generate_caption_for_cut(index: int, total: int, inputs: Dict, middle_sequence: List[str]) -> str:
    if index == 1:
        return generate_hook_line(inputs)

    if index == 2:
        return generate_location_line(inputs)

    if index == total - 1 and total >= 4:
        return generate_urgency_line(inputs)

    if index == total:
        return generate_cta_line(inputs)

    seq_index = index - 3
    if 0 <= seq_index < len(middle_sequence):
        return add_soft_reaction(middle_sequence[seq_index])

    fallback_candidates = []

    if inputs.get("promo_points"):
        fallback_candidates.extend(inputs["promo_points"])
    if inputs.get("detail_items"):
        fallback_candidates.extend(inputs["detail_items"])
    if inputs.get("main_product"):
        fallback_candidates.append(inputs["main_product"])
    if inputs.get("event_benefits"):
        fallback_candidates.append(inputs["event_benefits"])
    if inputs.get("price_or_number"):
        fallback_candidates.append(inputs["price_or_number"])

    if not fallback_candidates:
        fallback_candidates = [
            "잠실에서 바로 볼 수 있음",
            "현장에서 체크할 포인트 있음",
            "디테일 보는 재미도 있음",
        ]

    chosen = split_long_text(random.choice(fallback_candidates), STYLE_RULES["max_line_length"])
    return add_soft_reaction(chosen)


def generate_cut_description(index: int, total: int, inputs: Dict) -> str:
    if index == 1:
        return "훅이 강하게 들어가는 오프닝 화면"
    if index == 2:
        return "층수/위치 정보가 보이는 화면"
    if index == total - 1 and total >= 4:
        return "한정성, 수치, 인기 포인트를 강조하는 화면"
    if index == total:
        return "방문 유도 또는 추천 CTA 마무리 화면"

    pool = CUT_DESCRIPTION_POOL.copy()

    if inputs.get("main_product"):
        pool.insert(0, f"{inputs['main_product']} 클로즈업")
    if inputs.get("event_benefits"):
        pool.insert(1, f"{inputs['event_benefits']} 안내 화면")
    if inputs.get("price_or_number"):
        pool.insert(2, f"{inputs['price_or_number']} 강조 화면")

    return pool[(index - 3) % len(pool)]


def generate_script(inputs: Dict) -> List[Dict]:
    total_cuts = estimate_cut_count(inputs["video_length"], inputs["cut_count"])
    middle_sequence = build_middle_sequence(inputs, total_cuts)

    drafts = []
    for idx in range(1, total_cuts + 1):
        caption = generate_caption_for_cut(idx, total_cuts, inputs, middle_sequence)
        description = generate_cut_description(idx, total_cuts, inputs)

        drafts.append(
            {
                "id": idx,
                "caption": caption,
                "description": description,
            }
        )
    return drafts


def regenerate_single_cut(cut: Dict, cut_index: int, total: int, inputs: Dict) -> Dict:
    middle_sequence = build_middle_sequence(inputs, total)
    new_caption = generate_caption_for_cut(cut_index + 1, total, inputs, middle_sequence)
    new_description = generate_cut_description(cut_index + 1, total, inputs)

    return {
        **cut,
        "caption": new_caption,
        "description": new_description,
    }


# -----------------------------
# Edit Helpers
# -----------------------------
def move_cut_up(cuts: List[Dict], idx: int) -> List[Dict]:
    if idx <= 0:
        return cuts
    cuts[idx - 1], cuts[idx] = cuts[idx], cuts[idx - 1]
    return reindex_cuts(cuts)


def move_cut_down(cuts: List[Dict], idx: int) -> List[Dict]:
    if idx >= len(cuts) - 1:
        return cuts
    cuts[idx + 1], cuts[idx] = cuts[idx], cuts[idx + 1]
    return reindex_cuts(cuts)


def reindex_cuts(cuts: List[Dict]) -> List[Dict]:
    for i, cut in enumerate(cuts, start=1):
        cut["id"] = i
    return cuts


# -----------------------------
# Export / Save
# -----------------------------
def export_text(cuts: List[Dict], inputs: Dict) -> str:
    header = [
        f"행사명: {inputs.get('event_name', '')}",
        f"행사 기간: {inputs.get('event_period', '')}",
        f"행사 장소: {inputs.get('event_place', '')}",
        f"층수: {inputs.get('floor', '')}",
        f"스타일 기준: {ACCOUNT_STYLE_NAME}",
        "-" * 40,
    ]

    body = []
    for cut in cuts:
        body.append(f"[컷 {cut['id']}]")
        body.append(f"자막: {cut['caption']}")
        body.append(f"컷 설명: {cut['description']}")
        body.append("")

    return "\n".join(header + body)


def save_current_result(inputs: Dict, cuts: List[Dict]) -> None:
    st.session_state.saved_results.append(
        {
            "saved_at": str(date.today()),
            "inputs": inputs,
            "cuts": json.loads(json.dumps(cuts, ensure_ascii=False)),
        }
    )


# -----------------------------
# App UI
# -----------------------------
init_session()

st.title("🎬 릴스 자막 초안 생성기")
st.caption("행사 정보를 입력하면 롯데몰 잠실점 SNS 스타일에 맞춰 컷별 자막 초안을 생성합니다.")

status_color = {
    STATUS_BEFORE: "gray",
    STATUS_DONE: "green",
    STATUS_EDITING: "orange",
    STATUS_CONFIRMED: "blue",
}

st.markdown(
    f"""
<div style="padding:12px 16px; border-radius:12px; background:#f5f7fb; margin-bottom:16px;">
    <b>현재 상태</b>:
    <span style="color:{status_color.get(st.session_state.status, 'black')}; font-weight:700;">
        {st.session_state.status}
    </span><br/>
    <b>적용 톤</b>: {ACCOUNT_STYLE_NAME}
</div>
""",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1, 1.2], gap="large")

with left_col:
    st.subheader("입력 영역")

    with st.form("input_form", clear_on_submit=False):
        event_name = st.text_input("행사명", placeholder="예: OO 팝업스토어")
        event_period = st.text_input("행사 기간", placeholder="예: 4/20 ~ 4/28")
        event_place = st.text_input("행사 장소", placeholder="예: 롯데월드몰 / 에비뉴엘")
        floor = st.text_input("층수", placeholder="예: 지하 1층 / 1층")

        promo_points_text = st.text_area(
            "홍보 포인트",
            placeholder="예:\n국내 최초\n잠실 한정\n비주얼 강한 디저트",
            height=110,
        )

        main_product = st.text_input("주력 상품", placeholder="예: 맘모스 샌드 / 피자 쿠키")

        detail_items_text = st.text_area(
            "구체 디테일",
            placeholder="예:\n200평 규모\n전국에 딱 두 군데\n10분 만에 200개 판매",
            height=100,
        )

        event_benefits = st.text_input("이벤트/혜택", placeholder="예: 한정 수량 증정 / 구매 시 할인")
        price_or_number = st.text_input("숫자/수치 강조 포인트", placeholder="예: 200평 규모 / 하루 100개 한정")
        limited_info = st.text_input("긴박감 포인트", placeholder="예: 한정 수량이라 늦으면 끝")
        required_phrase = st.text_input("마지막 CTA 문구", placeholder="예: 잠실로 놀러 오세요")

        video_length = st.slider("영상 길이(초)", min_value=10, max_value=60, value=20, step=5)
        cut_count = st.number_input("예상 컷 수", min_value=0, max_value=15, value=6, step=1)

        style_template = st.selectbox(
            "스타일 템플릿",
            options=["기본형", "희소성 강조형", "질문형 훅 강조형", "비주얼 훅 강조형"],
        )

        submitted = st.form_submit_button("초안 생성", use_container_width=True)

    if submitted:
        inputs = {
            "event_name": clean_text(event_name),
            "event_period": clean_text(event_period),
            "event_place": clean_text(event_place),
            "floor": clean_text(floor),
            "promo_points": parse_multiline_items(promo_points_text),
            "main_product": clean_text(main_product),
            "detail_items": parse_multiline_items(detail_items_text),
            "event_benefits": clean_text(event_benefits),
            "price_or_number": clean_text(price_or_number),
            "limited_info": clean_text(limited_info),
            "required_phrase": clean_text(required_phrase),
            "video_length": video_length,
            "cut_count": int(cut_count),
            "style_template": style_template,
        }

        st.session_state.generation_count += 1

        with st.spinner("자막 리듬 구성 중..."):
            drafts = generate_script(inputs)

        st.session_state.inputs = inputs
        st.session_state.drafts = drafts
        st.session_state.status = STATUS_DONE
        st.success("초안 생성이 완료되었습니다.")

    if st.session_state.get("inputs"):
        st.markdown("---")
        st.subheader("액션")

        c1, c2 = st.columns(2)

        with c1:
            if st.button("다시 생성", use_container_width=True):
                with st.spinner("컷 리듬 다시 조정 중..."):
                    st.session_state.drafts = generate_script(st.session_state.inputs)
                st.session_state.status = STATUS_DONE
                st.success("새 초안으로 다시 생성했습니다.")
                st.rerun()

        with c2:
            if st.button("저장", use_container_width=True):
                save_current_result(st.session_state.inputs, st.session_state.drafts)
                st.success("현재 결과를 저장했습니다.")

with right_col:
    st.subheader("결과 영역")

    if not st.session_state.drafts:
        st.info("좌측 입력 영역에서 행사 정보를 입력한 뒤 초안을 생성해주세요.")
    else:
        export_payload = export_text(st.session_state.drafts, st.session_state.inputs)

        top1, top2, top3 = st.columns(3)

        with top1:
            st.download_button(
                "텍스트 다운로드",
                data=export_payload.encode("utf-8"),
                file_name="reels_caption_draft.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with top2:
            st.text_area("전체 복사용 텍스트", value=export_payload, height=120)

        with top3:
            if st.button("최종 확정", use_container_width=True):
                st.session_state.confirmed_result = {
                    "inputs": st.session_state.inputs,
                    "cuts": json.loads(json.dumps(st.session_state.drafts, ensure_ascii=False)),
                }
                st.session_state.status = STATUS_CONFIRMED
                st.success("최종 확정되었습니다.")

        st.markdown("### 컷별 편집")

        for idx, cut in enumerate(st.session_state.drafts):
            with st.container(border=True):
                st.markdown(f"#### 컷 {cut['id']}")

                edited_caption = st.text_area(
                    f"자막_{idx}",
                    value=cut["caption"],
                    key=f"caption_{idx}",
                    height=80,
                )
                edited_description = st.text_area(
                    f"컷 설명_{idx}",
                    value=cut["description"],
                    key=f"description_{idx}",
                    height=80,
                )

                st.session_state.drafts[idx]["caption"] = edited_caption
                st.session_state.drafts[idx]["description"] = edited_description

                btn1, btn2, btn3, btn4, btn5 = st.columns(5)

                with btn1:
                    if st.button("부분 재생성", key=f"regen_{idx}", use_container_width=True):
                        st.session_state.drafts[idx] = regenerate_single_cut(
                            st.session_state.drafts[idx],
                            idx,
                            len(st.session_state.drafts),
                            st.session_state.inputs,
                        )
                        st.session_state.status = STATUS_EDITING
                        st.rerun()

                with btn2:
                    if st.button("위로 이동", key=f"up_{idx}", use_container_width=True):
                        st.session_state.drafts = move_cut_up(st.session_state.drafts, idx)
                        st.session_state.status = STATUS_EDITING
                        st.rerun()

                with btn3:
                    if st.button("아래로 이동", key=f"down_{idx}", use_container_width=True):
                        st.session_state.drafts = move_cut_down(st.session_state.drafts, idx)
                        st.session_state.status = STATUS_EDITING
                        st.rerun()

                with btn4:
                    if st.button("삭제", key=f"delete_{idx}", use_container_width=True):
                        st.session_state.drafts.pop(idx)
                        st.session_state.drafts = reindex_cuts(st.session_state.drafts)
                        st.session_state.status = STATUS_EDITING
                        st.rerun()

                with btn5:
                    if st.button("컷 추가", key=f"add_{idx}", use_container_width=True):
                        new_cut = {
                            "id": len(st.session_state.drafts) + 1,
                            "caption": "새 컷 자막을 입력하세요",
                            "description": "새 컷 설명을 입력하세요",
                        }
                        st.session_state.drafts.insert(idx + 1, new_cut)
                        st.session_state.drafts = reindex_cuts(st.session_state.drafts)
                        st.session_state.status = STATUS_EDITING
                        st.rerun()

with st.sidebar:
    st.header("요약")
    st.write(f"생성 횟수: {st.session_state.generation_count}")
    st.write(f"현재 상태: {st.session_state.status}")
    st.write(f"적용 톤: {ACCOUNT_STYLE_NAME}")

    st.markdown("### 고정 가이드")
    st.markdown(
        """
- 첫 컷은 반드시 훅
- 한 컷 = 한 정보
- 중반부는 위치/숫자/메뉴/혜택 디테일
- 후반부는 긴박감
- 마지막은 CTA
- 이모지는 거의 사용하지 않음
- 같은 문장을 직접 반복하지 않고 매번 변주
        """
    )

    if st.session_state.get("inputs"):
        st.markdown("### 입력 정보")
        st.json(st.session_state.inputs, expanded=False)

    if st.session_state.saved_results:
        st.markdown("### 저장된 결과")
        for i, item in enumerate(st.session_state.saved_results, start=1):
            with st.expander(f"저장본 {i} ({item['saved_at']})"):
                st.write(f"행사명: {item['inputs'].get('event_name', '-')}")
                st.write(f"컷 수: {len(item['cuts'])}")

    if st.session_state.confirmed_result:
        st.markdown("### 확정 결과")
        st.success("최종 확정본이 있습니다.")

        final_text = export_text(
            st.session_state.confirmed_result["cuts"],
            st.session_state.confirmed_result["inputs"],
        )

        st.download_button(
            "확정본 다운로드",
            data=final_text.encode("utf-8"),
            file_name="reels_caption_confirmed.txt",
            mime="text/plain",
            use_container_width=True,
        )
