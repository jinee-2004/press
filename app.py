import streamlit as st
import re  # 정규표현식 사용
import openai
import os
import datetime
import requests
import matplotlib.pyplot as plt

# validate_phone 함수를 최상단에 정의 (사용 전 반드시 정의되어 있어야 합니다)
def validate_phone():
    phone_val = st.session_state.get("phone_input", "")
    if phone_val and not re.fullmatch(r"[0-9-]+", phone_val):
        st.session_state.phone_error = "전화번호를 정확히 입력해주세요. (숫자와 '-'만 허용)"
    else:
        st.session_state.phone_error = ""

# 페이지 설정 (다른 Streamlit 명령어보다 먼저 호출)
st.set_page_config(page_title="세종시 인공지능 보도자료 작성 서비스", layout="wide")

# 인라인 CSS: 공통 버튼 스타일 (st.button과 st.download_button 모두 적용)
st.markdown("""
    <style>
    /* st.button은 button 태그, st.download_button은 a 태그로 렌더링됨 */
    div.stButton > button,
    div.download-btn-wrapper a {
        background-color: #6c5ce7;
        color: white;
        text-decoration: none;
        display: inline-block;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        border-radius: 8px;
        transition: background-color 0.3s ease;
        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
        white-space: nowrap;
    }
    div.stButton > button:hover,
    div.download-btn-wrapper a:hover {
        background-color: #a29bfe;
    }
    </style>
    """, unsafe_allow_html=True)

# 인라인 CSS: 사이드바 스타일링 (왼쪽 정렬 적용)
st.markdown("""
    <style>
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #ffffff, #f0f2f6);
        padding: 20px;
        border-radius: 8px;
        text-align: left;
    }
    .menu-title {
        text-align: left;
        color: #333333;
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 인라인 CSS: 입력폼 타이틀(라벨) 폰트 스타일 및 placeholder 색상 조절
st.markdown("""
    <style>
    div[data-testid="stTextInput"] label,
    div[data-testid="stDateInput"] label {
        font-size: 21px !important;
        font-weight: bold !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    /* placeholder 색상: 기본보다 더 옅게 표시 */
    input::placeholder {
        color: #aaa;
    }
    </style>
    """, unsafe_allow_html=True)

# ex.txt 파일에서 작성 예시 내용을 읽어오기 및 상태 메시지 결정
example_text = ""
example_status = ""
try:
    with open("ex.txt", "r", encoding="utf-8") as file:
        example_text = file.read()
    example_status = "*작성서식 학습 완료"
except Exception as e:
    example_status = "*작성서식 읽기 오류"

# 보도자료 생성 함수 (ex.txt 파일의 작성 예시 내용을 prompt에 포함)
def generate_press_release(api_key, title, contact_person, phone, press_core, temperature, example_text):
    openai.api_key = api_key
    prompt = f"""
보도자료 작성 작업을 시작합니다.
다음의 정보를 바탕으로 보도자료를 아래의 형식에 맞게 작성하세요.

[입력 정보]
- 보도자료 제목: {title}
- 담당자: {contact_person}
- 연락처: {phone}
- 보도자료 핵심반영: {press_core}

[출력 형식]
1. 보도자료 제목: 보도자료의 핵심을 담은 제목을 HTML h1 태그를 사용하여 진하게 작성하세요.
2. 보도자료 추천 제목: 보도자료 제목에 어울리는 추천 제목 4개를 1번부터 4번까지 번호 매긴 리스트 형식(일반 본문 글씨)으로 작성하세요.
3. 보도자료 내용: 전문적인 보도자료 본문을 작성하되 아래의 예시와 유사한 스타일로 여러 문단에 걸쳐 작성하세요.

[작성 예시]
{example_text}

출력은 반드시 Markdown 형식으로 제공해 주세요.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # 필요에 따라 모델명을 수정하세요.
            messages=[
                {"role": "system", "content": "당신은 뛰어난 보도자료 작성가입니다. 서식을 준수하나, 출력폼에 맞추어 자동 줄바꿈 해주세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=4000
        )
        return response.choices[0].message.content if response.choices else "⚠️ 응답을 생성하지 못했습니다."
    except Exception as e:
        return f"❌ OpenAI API 요청 중 오류 발생: {str(e)}"

# API 사용량 조회 함수 (단일 날짜를 사용하도록 수정)
def get_usage(api_key, usage_date):
    # 사용량 조회에 필요한 'date' 파라미터를 추가 (YYYY-MM-DD 형식)
    url = f"https://api.openai.com/v1/usage?date={usage_date}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

# 사이드바 메뉴 및 설정 메뉴
with st.sidebar:
    st.image("https://search.pstatic.net/common/?src=http%3A%2F%2Fblogfiles.naver.net%2FMjAyMTA5MjlfMjgw%2FMDAxNjMyODgyNDExOTQ1.k_I9_tlqlKtEmH_MXVaeDk95E58Gtbn3micpH-QL5DAg.Ve1R6QqleIgFgkIAVU86SNnDPceZfl-rVf_ZBaa80yYg.JPEG.afkang%2F%25B4%25D9%25BF%25EE%25B7%25CE%25B5%25E5%25C6%25C4%25C0%25CF%25A3%25AD6.jpg", width=150)
    st.markdown("<div class='menu-title'>📌 메뉴</div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    page = st.radio("이동할 화면을 선택하세요", ["보도자료 작성", "사용통계"], index=0, key="page_radio", horizontal=True)
    
    with st.expander("설정 메뉴", expanded=True):
        st.markdown("**💬 문장 느낌 설정**")
        sentence_style = st.radio("\u200b", ("단순명료", "보통설명", "상세한설명"), index=2, key="sentence_style", help="문장 느낌을 선택하세요")

# temperature 값 결정 (설정 메뉴의 문장 느낌 설정에 따라)
temp_mapping = {"단순명료": 0.3, "보통설명": 0.7, "상세한설명": 1.0}
temperature = temp_mapping[sentence_style]

# 페이지 분기: 보도자료 작성과 사용통계
if page == "보도자료 작성":
    st.markdown("""
    <h1 style="font-size: 40px; margin-bottom: 0.5em;">
        세종시 생성형AI 보도자료 작성 서비스
    </h1>
    """, unsafe_allow_html=True)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ 환경 변수 OPENAI_API_KEY가 설정되지 않았습니다!")
        st.stop()
    
    left_col, right_col = st.columns(2)
    
    with left_col:
        press_title = st.text_input("📰 보도자료 제목", placeholder="(예시) 세종시, 생활폐기물 불법배출 강력 단속")
        contact_person = st.text_input("👤 담당자", placeholder="(예시) 정보통계담당관 이세종 주무관")
        phone = st.text_input("📞 연락처", value="044-300-0000", key="phone_input", on_change=validate_phone)
        if "phone_error" in st.session_state and st.session_state.phone_error:
            st.error(st.session_state.phone_error)
        press_core = st.text_area("💡 보도자료 핵심반영", placeholder="(예시) 3월 17일~28일 공동주택, 상가 등 자동크린넷 상습 막힘지역 집중 단속, 대형폐기물의 자동크린넷 투입, 종량제봉투 미사용, 재활용 가능 자원의 혼합배출 등 폐기물관리법 위반 사항 집중 단속")
        tf_submit = st.button("보도자료 생성")
        st.caption(example_status)  # ex.txt 파일 리드 상태 메시지 표시

    with right_col:
        if tf_submit:
            errors = []
            if not press_title.strip():
                errors.append("보도자료 제목 입력 필요")
            if not contact_person.strip():
                errors.append("담당자 입력 필요")
            if not phone.strip():
                errors.append("연락처 입력 필요")
            if not press_core.strip():
                errors.append("보도자료 핵심반영 입력 필요")
            if errors:
                for err in errors:
                    st.error(err)
            else:
                with st.spinner("보도자료 생성 중..."):
                    press_release = generate_press_release(api_key, press_title, contact_person, phone, press_core, temperature, example_text)
                st.subheader("📢 생성된 보도자료")
                st.markdown(press_release, unsafe_allow_html=True)
                st.download_button(
                    label="파일 저장 (TXT)",
                    data=press_release,
                    file_name="보도자료.txt",
                    mime="text/plain"
                )
        else:
            st.info("여기에 생성된 보도자료 결과가 표시됩니다.")

elif page == "사용통계":
    st.title("API 사용 통계")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ 환경 변수 OPENAI_API_KEY가 설정되지 않았습니다!")
        st.stop()
    
    # 시작일과 종료일 선택 (날짜 범위)
    start_date = st.date_input("시작 날짜", datetime.date.today() - datetime.timedelta(days=7))
    end_date = st.date_input("종료 날짜", datetime.date.today())
    
    if start_date > end_date:
        st.error("❌ 시작 날짜는 종료 날짜보다 이전이어야 합니다.")
    else:
        dates = []
        usage_values = []
        current_date = start_date
        with st.spinner("사용 통계 조회 중..."):
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                usage_data = get_usage(api_key, date_str)
                # API 호출 오류 발생 시 0으로 처리하고 로그 출력
                if "error" in usage_data:
                    usage = 0
                    st.warning(f"{date_str} 사용량 조회 오류: {usage_data['error']}")
                else:
                    usage = usage_data.get("total_usage", 0)
                dates.append(date_str)
                usage_values.append(usage)
                current_date += datetime.timedelta(days=1)
        
        # 그래프 그리기
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(dates, usage_values, marker='o')
        ax.set_xlabel("날짜")
        ax.set_ylabel("총 사용량 (토큰)")
        ax.set_title("OpenAI API 사용량")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
        
        # 데이터 테이블 함께 표시 (선택 사항)
        st.subheader("날짜별 사용량 데이터")
        data = {"날짜": dates, "총 사용량 (토큰)": usage_values}
        st.table(data)
