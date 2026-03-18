import streamlit as st
import requests
import json
import time
import datetime
import pandas as pd
from io import BytesIO
import os
from PIL import Image

# ==========================================
# 1. 시스템 설정 및 커스텀 스타일
# ==========================================

APP_DISABLED = False 

if APP_DISABLED:
    st.error("🚫 현재 시스템 점검 중으로 서비스를 일시 중단합니다.")
    st.stop()

st.set_page_config(
    page_title="사업자 등록 상태 조회 시스템 v3.0",
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 고급스러운 UI를 위한 추가 CSS
st.markdown("""
    <style>
    /* 메트릭 카드 디자인 강화 */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e293b, #0f172a) !important;
        padding: 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important;
        border: 1px solid #334155 !important;
        text-align: center;
    }
    [data-testid="stMetricLabel"] p {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
    [data-testid="stMetricValue"] div {
        color: #f8fafc !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }
    
    /* 탭 디자인 정돈 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom: 3px solid #3b82f6;
        color: #3b82f6 !important;
        font-weight: bold;
    }
    
    /* 버튼 스타일 통일 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        font-weight: 700;
        transition: all 0.3s ease;
    }
    .stButton>button[kind="primary"] {
        background-color: #3b82f6;
        color: white;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #2563eb;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 전역 변수 및 세션 상태 초기화
# ==========================================
EXPIRY_DATE = datetime.date(2026, 12, 31)
SERVICE_KEY = st.secrets.get("SERVICE_KEY")

# 데이터 증발을 막기 위한 세션 상태 관리 (매우 중요)
if 'search_completed' not in st.session_state:
    st.session_state.search_completed = False
if 'results_data' not in st.session_state:
    st.session_state.results_data = []
if 'abnormal_data' not in st.session_state:
    st.session_state.abnormal_data = []

# ==========================================
# 3. 핵심 함수
# ==========================================
def check_license():
    if datetime.date.today() > EXPIRY_DATE:
        st.error(f"🛑 서비스 이용 기간이 만료되었습니다. (만료일: {EXPIRY_DATE})")
        st.stop()

def check_biz_status(biz_nums):
    if not SERVICE_KEY:
        st.error("🔑 API 서비스 키가 설정되어 있지 않습니다. Streamlit Secrets를 확인해주세요.")
        st.stop()
        
    API_URL = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={SERVICE_KEY}"
    HEADERS = {"Content-Type": "application/json"}
    
    all_results = []
    progress_bar = st.progress(0, text="국세청 실시간 데이터를 조회 중입니다... ⏳")
    
    for i in range(0, len(biz_nums), 100):
        chunk = biz_nums[i:i+100]
        payload = {"b_no": chunk}
        try:
            response = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload), timeout=15)
            if response.status_code == 200:
                result = response.json()
                all_results.extend(result.get("data", []))
            else:
                st.warning(f"⚠️ API 응답 오류 (코드: {response.status_code})")
        except Exception as e:
            st.error(f"❌ 조회 중 통신 오류가 발생했습니다: {e}")
            break
            
        percent = min((i + 100) / len(biz_nums), 1.0)
        progress_bar.progress(percent, text=f"데이터 수신 중... {int(percent*100)}% ({len(all_results)}건 완료)")
        time.sleep(0.1) # 서버 과부하 방지
    
    time.sleep(0.5)
    progress_bar.empty()
    return all_results

# ==========================================
# 4. 화면 레이아웃 구성
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/city-buildings.png", width=80)
    st.title("Biz Checker Pro")
    st.markdown("---")
    st.info(f"🟢 **운영 상태:** 정상\n\n📅 **라이선스 만료:** {EXPIRY_DATE}")
    
    # 세션 초기화 버튼 (새로운 조회를 원할 때)
    if st.session_state.search_completed:
        if st.button("🔄 새로운 조회 시작", use_container_width=True):
            st.session_state.search_completed = False
            st.session_state.results_data = []
            st.session_state.abnormal_data = []
            st.rerun()
            
    st.markdown("---")
    st.caption("© 2026 Lim Jung-taek. All rights reserved.")

st.title("🏢 사업자 등록 상태 일괄 조회 시스템")
st.markdown("국세청 데이터를 기반으로 다수의 사업자등록번호 상태를 실시간으로 확인합니다.")
check_license()

# 탭을 활용한 화면 분할 (조회 화면 / 가이드 화면)
tab_main, tab_guide = st.tabs(["🚀 실시간 조회", "📖 이용 가이드"])

# ----------------- [탭 2: 이용 가이드] -----------------
with tab_guide:
    st.info("""
    **📌 데이터 업로드 및 정제 기준**
    * **파일 형식:** TXT 파일 또는 Excel 파일(xlsx, xlsm)만 지원합니다.
    * **자동 정제:** 번호 사이의 하이픈(-)이나 띄어쓰기는 시스템이 자동으로 제거합니다.
    * **엑셀 인식:** 엑셀 업로드 시 반드시 **첫 번째 열(A열)**에 사업자 번호를 기입해 주세요.
    * **추출 기준:** 문자열이 제외된 10자리 이상의 순수 숫자만 유효 데이터로 취급합니다.
    """)
    
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.markdown("##### 📝 TXT 파일 작성 예시")
        txt_img_path = os.path.join("images", "txt_example.png")
        if os.path.exists(txt_img_path):
            st.image(Image.open(txt_img_path), use_column_width=True)
        else:
            st.code("123-45-67890\n2345678901\n345 67 89012", language="text")
            
    with g_col2:
        st.markdown("##### 📊 Excel 파일 작성 예시")
        excel_img_path = os.path.join("images", "excel_example.png")
        if os.path.exists(excel_img_path):
            st.image(Image.open(excel_img_path), use_column_width=True)
        else:
            st.markdown("*A열에만 데이터를 입력하세요 (헤더 유무 무관)*")
            st.table(pd.DataFrame({"A열 (사업자번호)": ["123-45-67890", "2345678901", "345 67 89012"]}))

# ----------------- [탭 1: 실시간 조회 (메인)] -----------------
with tab_main:
    st.markdown("#### 1. 데이터 업로드")
    uploaded_file = st.file_uploader("사업자번호 리스트 파일을 업로드하세요", type=["txt", "xlsx", "xlsm"])
    biz_nums = []

    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        raw_list = []
        try:
            if file_ext in ["xlsx", "xlsm"]:
                df_input = pd.read_excel(uploaded_file, header=None)
                raw_list = df_input.iloc[:, 0].dropna().astype(str).tolist()
            else:
                raw_data = uploaded_file.read()
                try:
                    content = raw_data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    content = raw_data.decode("cp949") # 한글 윈도우 인코딩 대응
                raw_list = content.splitlines()

            # 데이터 정제 로직
            for item in raw_list:
                clean_num = item.replace("-", "").replace(" ", "").replace("\t", "").strip()
                if clean_num.isdigit() and len(clean_num) >= 10:
                    biz_nums.append(clean_num)
            
            # 중복 제거 옵션 (필요시 활성화)
            biz_nums = list(dict.fromkeys(biz_nums)) 

            if biz_nums:
                st.success(f"✅ 총 **{len(biz_nums)}건**의 유효한 사업자 번호가 추출되었습니다.")
                with st.expander("추출된 데이터 미리보기"):
                    st.write(biz_nums[:20] + ["..."] if len(biz_nums) > 20 else biz_nums)
            else:
                st.warning("⚠️ 유효한 사업자 번호를 찾을 수 없습니다. 파일 형식을 다시 확인해 주세요.")

        except Exception as e:
            st.error(f"❌ 파일을 읽는 중 오류가 발생했습니다: {e}")

    # 조회 실행부
    st.markdown("#### 2. 상태 조회")
    if biz_nums and not st.session_state.search_completed:
        if st.button(f"🚀 {len(biz_nums)}건 국세청 실시간 조회 시작", type="primary"):
            results = check_biz_status(biz_nums)
            abnormal = []
            
            for item in results:
                if item.get("b_stt") != "계속사업자":
                    abnormal.append({
                        "사업자번호": item.get('b_no'),
                        "상태": item.get('b_stt', '조회불가'),
                        "과세유형": item.get('tax_type', '-'),
                        "폐업일자": item.get('end_dt', '-')
                    })
            
            # 조회 결과를 세션 상태에 저장 (데이터 증발 방지)
            st.session_state.results_data = results
            st.session_state.abnormal_data = abnormal
            st.session_state.search_completed = True
            st.rerun() # 화면 갱신

    # 결과 출력부 (조회가 완료된 상태일 때만 표시)
    if st.session_state.search_completed:
        results = st.session_state.results_data
        abnormal = st.session_state.abnormal_data
        normal_count = len(results) - len(abnormal)
        
        st.markdown("---")
        st.markdown("### 📊 최종 조회 리포트")
        
        # 메트릭스 대시보드
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("전체 조회 건수", f"{len(results)}건")
        res_col2.metric("🟢 정상 (계속사업자)", f"{normal_count}건")
        res_col3.metric("🔴 주의 필요 대상", f"{len(abnormal)}건")

        st.markdown("<br>", unsafe_allow_html=True)

        if len(abnormal) > 0:
            st.error(f"⚠️ 휴폐업 및 조회 불가 등 확인이 필요한 사업자가 **{len(abnormal)}건** 발견되었습니다.")
            
            # UI가 깔끔한 인터랙티브 데이터프레임
            df_res = pd.DataFrame(abnormal)
            st.dataframe(
                df_res, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "사업자번호": st.column_config.TextColumn("사업자번호", width="medium"),
                    "상태": st.column_config.TextColumn("현재 상태", width="small"),
                    "과세유형": st.column_config.TextColumn("과세/면세 유형", width="large"),
                    "폐업일자": st.column_config.DateColumn("폐업일자", format="YYYY-MM-DD")
                }
            )
            
            # 엑셀 다운로드 (세션 스테이트 덕분에 버튼을 눌러도 데이터가 날아가지 않음)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_res.to_excel(writer, index=False, sheet_name='주의사업자명단')
                
            st.download_button(
                label="📥 주의 대상 결과 다운로드 (Excel)",
                data=output.getvalue(),
                file_name=f"biz_alert_result_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
        else:
            st.balloons()
            st.success("🎉 완벽합니다! 조회하신 모든 사업자가 정상(계속사업자) 상태입니다.")
