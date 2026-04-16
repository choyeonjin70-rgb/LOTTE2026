import json
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="릴스 자막 자동 생성기", layout="wide")

st.title("🎬 릴스 자막 자동 생성기")
st.markdown("AI를 활용해 **컷별 자막 초안**을 생성하고, **컷별 수정/재생성**까지 할 수 있습니다.")

# ---------------------------
# Session State
# ---------------------------
if "result_data" not in st.session_state:
    st.session_state.result_data = None

if "last_input_payload" not in st.session_state:
    st.session_state.last_input_payload = None

# ---------------------------
# Sidebar
# ---------------------------
with st.sidebar:
    st.header("🔑 설정")
    api_key = st.text_input("OpenAI API Key", type="password")
    model_name = st.selectbox(
        "모델 선택",
        ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"],
        index=0
    )

client = OpenAI(api_key=api_key) if api_key else None

# ---------------------------
# Input Area
# ---------------------------
st.subheader("📥 입력 정보")

col1, col2 = st.columns(2)

with col1:
    event_name = st.text_input("행사명", placeholder="예: 스파르타 부트캠프 박람회")
    event_period = st.text_input("행사 기간", placeholder="예: 2026.04.20 ~ 2026.04.25")
    event_location = st.text_input("행사 장소", placeholder="예: 코엑스 Hall C")

with col2:
    promo_points = st.text_area(
        "홍보 포인트 (할인/이벤트/주력상품 등)",
        placeholder="예: 현장 등록 할인, 선착순 굿즈 증정, 인기 강의 체험존 운영"
    )

st.subheader("🎨 스타일 설정")

tone = st.text_input("톤앤매너", placeholder="예: 유쾌한, 감각적인, MZ스럽게")

col_a, col_b = st.columns(2)

with col_a:
    no_must_include = st.checkbox("반드시 포함할 문구 없음", value=False)
    must_include = ""
    if not no_must_include:
        must_include = st.text_area(
            "반드시 포함할 문구",
            placeholder="예: 지금 신청하면 혜택 제공 / 현장 한정 이벤트"
        )

with col_b:
    no_avoid_words = st.checkbox("피해야 할 표현 없음", value=False)
    avoid_words = ""
    if not no_avoid_words:
        avoid_words = st.text_area(
            "피해야 할 표현",
            placeholder="예: 과장된 표현, 지나치게 자극적인 문구"
        )

st.subheader("📚 레퍼런스 (선택)")
reference = st.text_area(
    "기존 자막 레퍼런스 입력 (Few-shot용)",
    placeholder="기존 릴스 자막 예시를 붙여넣어 주세요."
)

# ---------------------------
# Helpers
# ---------------------------
def get_input_payload():
    return {
        "event_name": event_name.strip(),
        "event_period": event_period.strip(),
        "event_location": event_location.strip(),
        "promo_points": promo_points.strip(),
        "tone": tone.strip(),
        "must_include": None if no_must_include else must_include.strip(),
        "avoid_words": None if no_avoid_words else avoid_words.strip(),
        "reference": reference.strip(),
    }


def validate_input(payload: dict) -> list[str]:
    errors = []
    if not payload["event_name"]:
        errors.append("행사명을 입력해주세요.")
    if not payload["promo_points"]:
        errors.append("홍보 포인트를 입력해주세요.")
    return errors


def build_full_prompt(payload: dict) -> str:
    must_include_text = (
        "없음" if payload["must_include"] is None or payload["must_include"] == ""
        else payload["must_include"]
    )
    avoid_words_text = (
        "없음" if payload["avoid_words"] is None or payload["avoid_words"] == ""
        else payload["avoid_words"]
    )
    reference_text = payload["reference"] if payload["reference"] else "없음"

    return f"""
너는 SNS 마케팅 전문가이자 숏폼 콘텐츠 카피라이터다.
릴스 영상(15초 분량)에 들어갈 컷별 자막 초안을 생성하라.

[행사 정보]
- 행사명: {payload["event_name"]}
- 기간: {payload["event_period"]}
- 장소: {payload["event_location"]}

[홍보 포인트]
{payload["promo_points"]}

[스타일]
- 톤앤매너: {payload["tone"]}
- 반드시 포함할 문구: {must_include_text}
- 피해야 할 표현: {avoid_words_text}

[레퍼런스]
{reference_text}

[요구사항]
- 총 10~15컷 구성
- 각 컷마다 1문장 자막
- Hook → 정보 → CTA 흐름이 자연스럽게 이어지도록 구성
- 문장은 짧고 임팩트 있게 작성
- 릴스 자막에 어울리도록 리듬감 있게 작성
- 영상 흐름에 맞는 컷 설명도 함께 작성
- 너무 장황하지 않게 작성
- 반드시 JSON 배열만 출력하고, 설명 문장은 쓰지 마라

[출력 형식]
[
  {{
    "cut": 1,
    "caption": "자막 문구",
    "visual": "해당 컷의 화면/연출 설명"
  }}
]
""".strip()


def build_regenerate_cut_prompt(payload: dict, current_data: list[dict], target_cut: int) -> str:
    must_include_text = (
        "없음" if payload["must_include"] is None or payload["must_include"] == ""
        else payload["must_include"]
    )
    avoid_words_text = (
        "없음" if payload["avoid_words"] is None or payload["avoid_words"] == ""
        else payload["avoid_words"]
    )

    current_json = json.dumps(current_data, ensure_ascii=False, indent=2)

    return f"""
너는 SNS 마케팅 전문가이자 숏폼 콘텐츠 카피라이터다.
아래는 릴스 자막 초안 전체 구성이다.
이 중 {target_cut}번 컷만 새롭게 다시 작성하라.

[행사 정보]
- 행사명: {payload["event_name"]}
- 기간: {payload["event_period"]}
- 장소: {payload["event_location"]}

[홍보 포인트]
{payload["promo_points"]}

[스타일]
- 톤앤매너: {payload["tone"]}
- 반드시 포함할 문구: {must_include_text}
- 피해야 할 표현: {avoid_words_text}

[현재 전체 구성]
{current_json}

[작업 지시]
- {target_cut}번 컷만 다시 써라
- 전체 흐름(Hook → 정보 → CTA)에 자연스럽게 맞아야 한다
- 기존 다른 컷들과 톤이 어울려야 한다
- 결과는 아래 JSON 객체 하나만 출력하라
- 설명 문장은 쓰지 마라

[출력 형식]
{{
  "cut": {target_cut},
  "caption": "새 자막 문구",
  "visual": "새 컷 설명"
}}
""".strip()


def call_llm_json_array(prompt: str) -> list[dict]:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "너는 콘텐츠 마케팅 전문가다. JSON만 정확하게 출력한다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("응답이 JSON 배열이 아닙니다.")
        return data
    except Exception:
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and start < end:
            data = json.loads(content[start:end + 1])
            if isinstance(data, list):
                return data
        raise ValueError("모델 응답을 JSON 배열로 파싱하지 못했습니다.")


def call_llm_json_object(prompt: str) -> dict:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "너는 콘텐츠 마케팅 전문가다. JSON만 정확하게 출력한다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
    )

    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("응답이 JSON 객체가 아닙니다.")
        return data
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and start < end:
            data = json.loads(content[start:end + 1])
            if isinstance(data, dict):
                return data
        raise ValueError("모델 응답을 JSON 객체로 파싱하지 못했습니다.")


def normalize_result_data(data: list[dict]) -> list[dict]:
    normalized = []
    for idx, item in enumerate(data, start=1):
        normalized.append(
            {
                "cut": int(item.get("cut", idx)),
                "caption": str(item.get("caption", "")).strip(),
                "visual": str(item.get("visual", "")).strip(),
            }
        )
    return normalized


# ---------------------------
# Action Buttons
# ---------------------------
top_btn_col1, top_btn_col2 = st.columns([1, 1])

with top_btn_col1:
    generate_clicked = st.button("🚀 처음 생성하기 / 전체 재생성", use_container_width=True)

with top_btn_col2:
    clear_clicked = st.button("🗑️ 결과 초기화", use_container_width=True)

if clear_clicked:
    st.session_state.result_data = None
    st.session_state.last_input_payload = None
    st.success("생성 결과를 초기화했습니다.")

if generate_clicked:
    if not client:
        st.error("OpenAI API Key를 입력해주세요.")
    else:
        payload = get_input_payload()
        errors = validate_input(payload)

        if errors:
            for err in errors:
                st.error(err)
        else:
            with st.spinner("전체 자막을 생성하는 중입니다..."):
                try:
                    prompt = build_full_prompt(payload)
                    data = call_llm_json_array(prompt)
                    st.session_state.result_data = normalize_result_data(data)
                    st.session_state.last_input_payload = payload
                    st.success("전체 자막 초안을 생성했습니다.")
                except Exception as e:
                    st.error(f"생성 중 에러가 발생했습니다: {e}")

# ---------------------------
# Result Editor
# ---------------------------
if st.session_state.result_data:
    st.divider()
    st.subheader("📤 생성 결과")
    st.caption("각 컷의 자막과 화면 설명을 직접 수정하거나, 특정 컷만 다시 생성할 수 있습니다.")

    payload_for_regen = get_input_payload()
    st.session_state.last_input_payload = payload_for_regen

    for idx, item in enumerate(st.session_state.result_data):
        cut_num = item["cut"]

        with st.expander(f"{cut_num}컷 편집", expanded=(idx == 0)):
            st.text_input(
                f"{cut_num}컷 번호",
                value=str(cut_num),
                disabled=True,
                key=f"cut_number_{idx}"
            )

            new_caption = st.text_area(
                f"{cut_num}컷 자막",
                value=item["caption"],
                key=f"caption_{idx}",
                height=100
            )

            new_visual = st.text_area(
                f"{cut_num}컷 화면 설명",
                value=item["visual"],
                key=f"visual_{idx}",
                height=100
            )

            # 수동 편집 반영
            st.session_state.result_data[idx]["caption"] = new_caption
            st.session_state.result_data[idx]["visual"] = new_visual

            btn_col1, btn_col2 = st.columns([1, 1])

            with btn_col1:
                if st.button(f"🔄 {cut_num}컷만 다시 생성", key=f"regen_cut_{idx}", use_container_width=True):
                    if not client:
                        st.error("OpenAI API Key를 입력해주세요.")
                    else:
                        with st.spinner(f"{cut_num}컷을 다시 생성하는 중입니다..."):
                            try:
                                prompt = build_regenerate_cut_prompt(
                                    payload_for_regen,
                                    st.session_state.result_data,
                                    cut_num
                                )
                                regenerated = call_llm_json_object(prompt)

                                st.session_state.result_data[idx]["caption"] = str(
                                    regenerated.get("caption", "")
                                ).strip()
                                st.session_state.result_data[idx]["visual"] = str(
                                    regenerated.get("visual", "")
                                ).strip()

                                st.success(f"{cut_num}컷을 다시 생성했습니다.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"{cut_num}컷 재생성 중 에러가 발생했습니다: {e}")

            with btn_col2:
                if st.button(f"💾 {cut_num}컷 수정 내용 유지", key=f"save_cut_{idx}", use_container_width=True):
                    st.success(f"{cut_num}컷 수정 내용을 반영했습니다.")

    st.divider()

    st.subheader("🧾 최종 JSON 결과")

    final_json = json.dumps(st.session_state.result_data, ensure_ascii=False, indent=2)
    st.code(final_json, language="json")

    download_col1, download_col2 = st.columns([1, 1])

    with download_col1:
        st.download_button(
            label="📥 JSON 다운로드",
            data=final_json,
            file_name="reels_caption.json",
            mime="application/json",
            use_container_width=True
        )

    with download_col2:
        if st.button("🔁 현재 입력값으로 전체 다시 생성", use_container_width=True):
            if not client:
                st.error("OpenAI API Key를 입력해주세요.")
            else:
                payload = get_input_payload()
                errors = validate_input(payload)

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    with st.spinner("현재 입력값으로 전체를 다시 생성하는 중입니다..."):
                        try:
                            prompt = build_full_prompt(payload)
                            data = call_llm_json_array(prompt)
                            st.session_state.result_data = normalize_result_data(data)
                            st.session_state.last_input_payload = payload
                            st.success("전체 자막을 다시 생성했습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"전체 재생성 중 에러가 발생했습니다: {e}")
