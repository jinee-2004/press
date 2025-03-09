import streamlit as st
import re  # 정규표현식 사용
import openai
import os
import datetime
import requests
import matplotlib.pyplot as plt

# validate_phone 함수를 최상단에 정의 (사용 전 반드시 정의되어 있어야 합니다)
def validate_phone():
    phone_val = st.session_state.phone_input
    if phone_val and not re.fullmatch(r"[0-9-]+", phone_val):
        st.session_state.phone_error = "전화번호를 입력해주세요."
    else:
        st.session_state.phone_error = ""

# 페이지 설정 (다른 Streamlit 명령어보다 먼저 호출)
st.set_page_config(page_title="보도자료 작성(ChatGPT-4o-mini)", layout="wide")

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

# 인라인 CSS: 입력폼 타이틀(라벨) 폰트 스타일 (글자 크기를 3포인트 크게, 진하게, 세련된 폰트 적용)
st.markdown("""
    <style>
    div[data-testid="stTextInput"] label,
    div[data-testid="stDateInput"] label {
        font-size: 21px !important;
        font-weight: bold !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 인라인 CSS: st.radio 위젯의 옵션 기본은 세로 배열(별도 flex 스타일 지정 없음)
# (만약 다른 곳에 적용된 전역 CSS가 있다면 해당 영역을 감싸서 오버라이드할 수 있습니다)

# 보도자료 생성 함수 (temperature 값을 매개변수로 추가)
def generate_press_release(api_key, topic, keywords, department, contact_person, phone, email, apply_date, temperature):
    client = openai.Client(api_key=api_key)
    prompt = f"""
    보도자료 작성
    주제: {topic}
    핵심 키워드: {', '.join(keywords)}
    담당 부서: {department}
    담당자: {contact_person}
    연락처: {phone}
    이메일: {email}
    적용 일정: {apply_date}
    
    위의 정보를 바탕으로 전문적인 보도자료를 작성하세요.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 뛰어난 보도자료 작성가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1000
        )
        return response.choices[0].message.content if response.choices else "⚠️ 응답을 생성하지 못했습니다."
    except Exception as e:
        return f"❌ OpenAI API 요청 중 오류 발생: {str(e)}"

# API 사용량 조회 함수
def get_usage(api_key, start_date, end_date):
    url = f"https://api.openai.com/v1/usage?start_date={start_date}&end_date={end_date}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

# 사이드바 메뉴 및 설정 메뉴
with st.sidebar:
    st.image("https://search.pstatic.net/common/?src=http%3A%2F%2Fblogfiles.naver.net%2FMjAyMTA5MjlfMjgw%2FMDAxNjMyODgyNDExOTQ1.k_I9_tlqlKtEmH_MXVaeDk95E58Gtbn3micpH-QL5DAg.Ve1R6QqleIgFgkIAVU86SNnDPceZfl-rVf_ZBaa80yYg.JPEG.afkang%2F%25B4%25D9%25BF%25EE%25B7%25CE%25B5%25E5%25C6%25C4%25C0%25CF%25A3%25AD6.jpg&type=a340", width=150)
    st.markdown("<div class='menu-title'>📌 메뉴</div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    page = st.radio("이동할 화면을 선택하세요", ["보도자료 작성", "사용통계"], index=0, key="page_radio", horizontal=True)
    
    # 설정 메뉴: 하단에 추가
    with st.expander("설정 메뉴", expanded=True):
        st.markdown("**💬 문장 느낌 설정**")
        # 세로로 나열 (horizontal=False는 기본값이므로 생략)
        sentence_style = st.radio("\u200b", ("단순명료", "보통설명", "상세한설명"), index=1, key="sentence_style", help="문장 느낌을 선택하세요")

# temperature 값 결정 (설정 메뉴의 문장 느낌 설정에 따라)
temp_mapping = {"단순명료": 0.3, "보통설명": 0.7, "상세한설명": 1.0}
temperature = temp_mapping[sentence_style]

# 보도자료 작성 페이지
if page == "보도자료 작성":
    st.markdown("""
    <h1 style="font-size: 40px; margin-bottom: 0.5em;">
        보도자료 작성(<span style="font-size: 35px;">ChatGPT-4o-mini</span>)
    </h1>
    """, unsafe_allow_html=True)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ 환경 변수 `OPENAI_API_KEY`가 설정되지 않았습니다!")
        st.stop()
    
    today_date = datetime.date.today()
    if "reset" not in st.session_state:
        st.session_state.reset = False
    if st.session_state.reset:
        st.session_state.clear()
        st.rerun()
    
    # 입력 필드
    topic = st.text_input("📰 보도자료 주제 입력", "세종시 공유 모빌리티 AI 불편접수시스템 도입 추진")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        keyword1 = st.text_input("🔑 핵심 키워드 1", "혁신적인 기술")
    with col2:
        keyword2 = st.text_input("🔑 핵심 키워드 2", "RPA활용")
    with col3:
        keyword3 = st.text_input("🔑 핵심 키워드 3", "시민편의")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        department = st.text_input("🏢 담당 부서", "정보통계담당관")
    with col_info2:
        contact_person = st.text_input("👤 담당자", "이세종")
    with col_info3:
        phone = st.text_input("📞 연락처", value="044-300-0000", key="phone_input", on_change=validate_phone)
        if "phone_error" in st.session_state and st.session_state.phone_error:
            st.error(st.session_state.phone_error)
    
    col_email, col_apply_date = st.columns(2)
    with col_email:
        email = st.text_input("✉️ 이메일", "sejong@korea.kr")
    with col_apply_date:
        apply_date = st.date_input("📅 적용 일정", today_date)
    
    col_btn1, col_empty, col_btn2 = st.columns([1, 6, 1])
    with col_btn1:
        if st.button("새로작성"):
            st.session_state.reset = True
            st.rerun()
    with col_btn2:
        tf_submit = st.button("보도자료 생성")
    
    if tf_submit:
        keyword_list = [keyword1, keyword2, keyword3]
        apply_date_str = apply_date.strftime("%Y-%m-%d")
        with st.spinner("보도자료 생성 중..."):
            press_release = generate_press_release(api_key, topic, keyword_list, department, contact_person, phone, email, apply_date_str, temperature)
        st.subheader("📢 생성된 보도자료")
        st.write(press_release)
        st.markdown('<div class="download-btn-wrapper">', unsafe_allow_html=True)
        st.download_button(
            label="파일 저장 (TXT)",
            data=press_release,
            file_name="보도자료.txt",
            mime="text/plain"
        )
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "사용통계":
    st.title("API 사용 통계")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("❌ 환경 변수 `OPENAI_API_KEY`가 설정되지 않았습니다!")
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작 날짜", datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("종료 날짜", datetime.date.today())
    
    if start_date > end_date:
        st.error("❌ 시작 날짜는 종료 날짜보다 이전이어야 합니다.")
    else:
        with st.spinner("사용 통계 조회 중..."):
            usage_data = get_usage(api_key, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        st.subheader("📊 사용 통계 결과")
        if "error" in usage_data:
            st.error(usage_data["error"])
        else:
            if "total_usage" in usage_data:
                st.write(f"총 사용량: {usage_data['total_usage']} 토큰")
            else:
                st.write("사용량 데이터를 불러올 수 없습니다.")
