import json
import streamlit as st

st.set_page_config(page_title="릴스 자막 자동 생성기", layout="wide")

st.title("🎬 릴스 자막 자동 생성기")
st.markdown(
    """
AI API 없이 사용하는 버전입니다.

**사용 방법**
1. 아래 정보를 입력합니다.
2. **전체 생성 프롬프트 만들기** 버튼을 눌러 프롬프트를 생성합니다.
3. 생성된 프롬프트를 ChatGPT 웹에 붙여넣습니다.
4. ChatGPT가 반환한 JSON 결과를 앱에 다시 붙여넣습니다.
5. 앱에서 컷별 수정 / 특정 컷 재생성용 프롬프트 생성까지 할 수 있습니다.
"""
)

# ---------------------------
# Session State
# ---------------------------
if "result_data" not in st.session_state:
    st.session_state.result_data = None

if "generated_prompt" not in st.session_state:
    st.session_state.generated_prompt = ""

if "parsed_json_text" not in st.session_state:
    st.session_state.parsed_json_text = ""

if "cut_regen_prompt" not in st.session_state:
    st.session_state.cut_regen_prompt = ""

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
        placeholder="예: 현장 등록 할인, 선착순 굿즈 증정, 인기 강의 체험존 운영",
        height=140
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
            placeholder="예: 지금 신청하면 혜택 제공 / 현장 한정 이벤트",
            height=100
        )

with col_b:
    no_avoid_words = st.checkbox("피해야 할 표현 없음", value=False)
    avoid_words = ""
    if not no_avoid_words:
        avoid_words = st.text_area(
            "피해야 할 표현",
            placeholder="예: 과장된 표현, 지나치게 자극적인 문구",
            height=100
        )

st.subheader("📚 레퍼런스 (선택)")
reference = st.text_area(
    "기존 자막 레퍼런스 입력 (Few-shot용)",
    placeholder="기존 릴스 자막 예시를 붙여넣어 주세요.",
    height=180
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


def validate_input(payload: dict) -> list:
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


def build_regenerate_cut_prompt(payload: dict, current_data: list, target_cut: int, extra_instruction: str) -> str:
    must_include_text = (
        "없음" if payload["must_include"] is None or payload["must_include"] == ""
        else payload["must_include"]
    )
    avoid_words_text = (
        "없음" if payload["avoid_words"] is None or payload["avoid_words"] == ""
        else payload["avoid_words"]
    )

    current_json = json.dumps(current_data, ensure_ascii=False, indent=2)
    extra_instruction_text = extra_instruction.strip() if extra_instruction.strip() else "없음"

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

[추가 수정 지시]
{extra_instruction_text}

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


def normalize_result_data(data: list) -> list:
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


def extract_json_array(text: str):
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and start < end:
        candidate = text[start:end + 1]
        data = json.loads(candidate)
        if isinstance(data, list):
            return data

    raise ValueError("JSON 배열을 찾지 못했습니다.")


def extract_json_object(text: str):
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidate = text[start:end + 1]
        data = json.loads(candidate)
        if isinstance(data, dict):
            return data

    raise ValueError("JSON 객체를 찾지 못했습니다.")


# ---------------------------
# Full Prompt Generation
# ---------------------------
st.divider()
st.subheader("🪄 1) ChatGPT에 넣을 전체 생성 프롬프트 만들기")

payload = get_input_payload()

btn_col1, btn_col2 = st.columns([1, 1])

with btn_col1:
    if st.button("📋 전체 생성 프롬프트 만들기", use_container_width=True):
        errors = validate_input(payload)
        if errors:
            for err in errors:
                st.error(err)
        else:
            st.session_state.generated_prompt = build_full_prompt(payload)
            st.success("전체 생성 프롬프트를 만들었습니다.")

with btn_col2:
    if st.button("🗑️ 결과 초기화", use_container_width=True):
        st.session_state.result_data = None
        st.session_state.generated_prompt = ""
        st.session_state.parsed_json_text = ""
        st.session_state.cut_regen_prompt = ""
        st.success("초기화했습니다.")

if st.session_state.generated_prompt:
    st.text_area(
        "아래 프롬프트를 ChatGPT 웹에 붙여넣으세요",
        value=st.session_state.generated_prompt,
        height=360
    )

# ---------------------------
# Paste Result from ChatGPT
# ---------------------------
st.divider()
st.subheader("📥 2) ChatGPT 결과 붙여넣기")

pasted_result = st.text_area(
    "ChatGPT가 반환한 JSON 결과를 그대로 붙여넣으세요",
    value=st.session_state.parsed_json_text,
    height=260,
    placeholder='예: [{"cut":1,"caption":"...","visual":"..."}]'
)

parse_col1, parse_col2 = st.columns([1, 1])

with parse_col1:
    if st.button("✅ 결과 불러오기", use_container_width=True):
        try:
            parsed = extract_json_array(pasted_result)
            st.session_state.result_data = normalize_result_data(parsed)
            st.session_state.parsed_json_text = pasted_result
            st.success("결과를 불러왔습니다.")
        except Exception as e:
            st.error(f"결과 파싱 중 오류가 발생했습니다: {e}")

with parse_col2:
    if st.button("📄 샘플 JSON 넣기", use_container_width=True):
        sample = [
            {"cut": 1, "caption": "놓치면 아쉬운 이번 행사", "visual": "행사 전경이 빠르게 등장"},
            {"cut": 2, "caption": "현장 한정 혜택까지 준비됐어요", "visual": "혜택 안내 보드 클로즈업"},
            {"cut": 3, "caption": "지금 바로 확인해보세요", "visual": "CTA 텍스트와 함께 마무리"}
        ]
        sample_text = json.dumps(sample, ensure_ascii=False, indent=2)
        st.session_state.parsed_json_text = sample_text
        st.rerun()

# ---------------------------
# Result Editor
# ---------------------------
if st.session_state.result_data:
    st.divider()
    st.subheader("✍️ 3) 컷별 편집")

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

            st.session_state.result_data[idx]["caption"] = new_caption
            st.session_state.result_data[idx]["visual"] = new_visual

            extra_instruction = st.text_input(
                f"{cut_num}컷 추가 수정 지시사항 (선택)",
                key=f"extra_instruction_{idx}",
                placeholder="예: 더 긴박하게 / CTA를 더 강하게 / 더 짧고 강하게"
            )

            if st.button(f"🔄 {cut_num}컷 재생성용 프롬프트 만들기", key=f"regen_prompt_{idx}"):
                try:
                    regen_prompt = build_regenerate_cut_prompt(
                        payload,
                        st.session_state.result_data,
                        cut_num,
                        extra_instruction
                    )
                    st.session_state.cut_regen_prompt = regen_prompt
                    st.success(f"{cut_num}컷 재생성용 프롬프트를 만들었습니다.")
                except Exception as e:
                    st.error(f"재생성용 프롬프트 생성 중 오류가 발생했습니다: {e}")

    # ---------------------------
    # Cut Regeneration Prompt
    # ---------------------------
    if st.session_state.cut_regen_prompt:
        st.divider()
        st.subheader("🔁 4) 특정 컷 재생성용 프롬프트")

        st.text_area(
            "아래 프롬프트를 ChatGPT 웹에 붙여넣어 특정 컷만 다시 생성하세요",
            value=st.session_state.cut_regen_prompt,
            height=320
        )

        regen_result = st.text_area(
            "재생성된 특정 컷의 JSON 결과를 여기에 붙여넣으세요",
            height=180,
            key="regen_result_text",
            placeholder='예: {"cut": 3, "caption": "...", "visual": "..."}'
        )

        if st.button("✅ 특정 컷 결과 반영"):
            try:
                obj = extract_json_object(regen_result)
                target_cut = int(obj["cut"])

                matched = False
                for i, item in enumerate(st.session_state.result_data):
                    if int(item["cut"]) == target_cut:
                        st.session_state.result_data[i]["caption"] = str(obj.get("caption", "")).strip()
                        st.session_state.result_data[i]["visual"] = str(obj.get("visual", "")).strip()
                        matched = True
                        break

                if matched:
                    st.success(f"{target_cut}컷 결과를 반영했습니다.")
                    st.rerun()
                else:
                    st.error("해당 cut 번호와 일치하는 항목을 찾지 못했습니다.")
            except Exception as e:
                st.error(f"특정 컷 결과 반영 중 오류가 발생했습니다: {e}")

    # ---------------------------
    # Final JSON
    # ---------------------------
    st.divider()
    st.subheader("🧾 최종 JSON 결과")

    final_json = json.dumps(st.session_state.result_data, ensure_ascii=False, indent=2)
    st.code(final_json, language="json")

    st.download_button(
        label="📥 JSON 다운로드",
        data=final_json,
        file_name="reels_caption.json",
        mime="application/json",
        use_container_width=True
    )
