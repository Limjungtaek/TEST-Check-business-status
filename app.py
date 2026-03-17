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
    page_title="사업자 등록 상태 조회 시스템 v2.7",
    page_icon="🏢", 
    layout="wide"
)

# [개선] 메트릭 카드 및 텍스트 시인성 강화를 위한 CSS
st.markdown("""
    <style>
    .main {
        background-color: #ffffff;
    }
    /* 버튼 스타일 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        font-size: 1.1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        color: white;
    }
    /* 메트릭 카드 디자인 - 짙은 배경과 밝은 글씨로 고정 */
    [data-testid="stMetric"] {
        background-color: #0F172A !important; /* 매우 짙은 남색 */
        padding: 25px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
        border: 1px solid #1E293B !important;
    }
    /* 메트릭 라벨(제목) */
    [data-testid="stMetricLabel"] p {
        color: #94A3B8 !important; /* 밝은 회색 */
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    /* 메트릭 값(숫자) */
    [data-testid="stMetricValue"] div {
        color: #FFFFFF !important; /* 완전 흰색 */
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }
    /* 안내 문구 스타일 */
    .guide-box {
        background-color: #F1F5F9;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        margin-bottom: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

EXPIRY_DATE = datetime.date(2026, 12, 31)
SERVICE_KEY = st.secrets.get("SERVICE_KEY")

def check_license():
    if datetime.date.today() > EXPIRY_DATE:
        st.error(f"🛑 서비스 이용 기간이 만료되었습니다. (만료일: {EXPIRY_DATE})")
        st.stop()

def check_biz_status(biz_nums):
    if not SERVICE_KEY:
        st.error("API 서비스 키가 설정되어 있지 않습니다.")
        st.stop()
        
    API_URL = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={SERVICE_KEY}"
    HEADERS = {"Content-Type": "application/json"}
    
    all_results = []
    progress_text = "국세청 실시간 데이터를 조회 중입니다..."
    my_bar = st.progress(0, text=progress_text)
    
    for i in range(0, len(biz_nums), 100):
        chunk = biz_nums[i:i+100]
        payload = {"b_no": chunk}
        try:
            response = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload), timeout=15)
            if response.status_code == 200:
                result = response.json()
                all_results.extend(result.get("data", []))
        except Exception as e:
            st.error(f"조회 중 오류 발생: {e}")
            break
        percent = min((i + 100) / len(biz_nums), 1.0)
        my_bar.progress(percent, text=f"진행율: {int(percent*100)}% ({len(all_results)}건 완료)")
        time.sleep(0.1)
    
    time.sleep(0.5)
    my_bar.empty()
    return all_results

# ==========================================
# 2. 메인 UI 화면
# ==========================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/city-buildings.png", width=80)
    st.title("Business Checker")
    st.markdown("---")
    st.info(f"**상태:** 운영 중\n**만료일:** {EXPIRY_DATE}")
    st.caption("© 2026 Lim Jung-taek.")

st.title("🏢 사업자 등록 상태 일괄 조회 시스템")
check_license()

# [수정] Expander 없이 바로 노출되는 이용 방법 섹션
st.markdown("""
<div class="guide-box">
    <h3 style="margin-top:0;">📌 이용 방법 안내</h3>
    1. <b>TXT</b> 혹은 <b>Excel(xlsx, xlsm)</b> 파일을 준비합니다.<br>
    2. 파일 형식에 상관없이 <b>하이픈(-)과 모든 공백</b>은 시스템이 자동으로 제거합니다.<br>
    3. 아래 예시와 같이 데이터를 구성하여 업로드해 주세요.
</div>
""", unsafe_allow_html=True)

# 예시 이미지 섹션 (500*300 고정)
guide_col1, guide_col2 = st.columns(2)

with guide_col1:
    st.subheader("📝 TXT 파일 예시")
    txt_img_path = os.path.join("images", "txt_example.png")
    if os.path.exists(txt_img_path):
        img_txt = Image.open(txt_img_path)
        resized_txt = img_txt.resize((500, 300), Image.Resampling.LANCZOS)
        st.image(resized_txt, caption="메모장 작성 예시", width=500)
    else:
        st.info("💡 images/txt_example.png 파일이 필요합니다.")

with guide_col2:
    st.subheader("📊 Excel 파일 예시")
    excel_img_path = os.path.join("images", "excel_example.png")
    if os.path.exists(excel_img_path):
        img_excel = Image.open(excel_img_path)
        resized_excel = img_excel.resize((500, 300), Image.Resampling.LANCZOS)
        st.image(resized_excel, caption="엑셀(첫 번째 열) 작성 예시", width=500)
    else:
        st.info("💡 images/excel_example.png 파일이 필요합니다.")

st.markdown("---")

# 파일 업로드 섹션
uploaded_file = st.file_uploader("사업자번호 파일을 업로드하세요 (TXT, XLSX, XLSM 지원)", type=["txt", "xlsx", "xlsm"])

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
                content = raw_data.decode("cp949")
            raw_list = content.splitlines()

        for item in raw_list:
            # 하이픈, 공백, 탭 문자 모두 제거
            clean_num = item.replace("-", "").replace(" ", "").replace("\t", "").strip()
            if clean_num.isdigit() and len(clean_num) >= 10:
                biz_nums.append(clean_num)
        
        if biz_nums:
            st.metric("추출된 유효 번호", f"{len(biz_nums)} 건")
        else:
            st.warning("유효한 사업자 번호를 찾을 수 없습니다.")

    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# 조회 실행 및 결과 출력
if biz_nums and st.button(f"🚀 {len(biz_nums)}건 국세청 실시간 조회 시작"):
    results = check_biz_status(biz_nums)
    abnormal = []
    normal_count = 0
    
    for item in results:
        if item.get("b_stt") == "계속사업자":
            normal_count += 1
        else:
            abnormal.append({
                "사업자번호": item.get('b_no'),
                "상태": item.get('b_stt') if item.get('b_stt') else "조회불가",
                "과세유형": item.get('tax_type', '-'),
                "폐업일자": item.get('end_dt') if item.get('end_dt') else "-"
            })

    st.markdown("### 📊 조회 결과 리포트")
    res_col1, res_col2, res_col3 = st.columns(3)
    
    # 짙은 배경에 흰색 글씨 카드가 출력됩니다.
    res_col1.metric("전체 조회 건수", f"{len(results)}건")
    res_col2.metric("정상(계속사업자)", f"{normal_count}건")
    res_col3.metric("주의 필요 대상", f"{len(abnormal)}건")

    if len(abnormal) > 0:
        st.error(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 있습니다.")
        df_res = pd.DataFrame(abnormal)
        df_res.index = df_res.index + 1
        st.dataframe(df_res, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_res.to_excel(writer, index=True, sheet_name='주의사업자명단')
            
        st.download_button(
            label="📥 결과 리스트 다운로드 (Excel)",
            data=output.getvalue(),
            file_name=f"biz_result_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.balloons()
        st.success("✨ 모든 사업자가 정상 상태(계속사업자)입니다!")
