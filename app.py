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
    page_title="사업자 등록 상태 조회 시스템 v2.9",
    page_icon="🏢", 
    layout="wide"
)

# [개선] 다크/라이트 모드 통합 시인성 강화 CSS
st.markdown("""
    <style>
    /* 1. 이용 방법 안내 박스 (중립적인 배경색으로 다크/라이트 모두 대응) */
    .guide-box {
        background-color: #f0f4f8 !important; 
        padding: 25px;
        border-radius: 12px;
        border-left: 6px solid #007bff;
        margin-bottom: 30px;
        color: #1a202c !important; /* 항상 어두운 글자색 유지 */
    }
    .guide-box h3 {
        color: #2c5282 !important;
        margin-top: 0;
        font-weight: 800;
    }
    .guide-box li, .guide-box p {
        color: #2d3748 !important;
        font-size: 1.05rem;
        font-weight: 600;
    }

    /* 2. 메트릭 카드 - 어떤 모드에서도 가독성이 높은 고정 스타일 */
    [data-testid="stMetric"] {
        background-color: #1e293b !important; /* 짙은 네이비 고정 */
        padding: 25px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        border: 1px solid #334155 !important;
    }
    /* 메트릭 라벨(제목) */
    [data-testid="stMetricLabel"] p {
        color: #e2e8f0 !important; /* 밝은 회색 고정 */
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }
    /* 메트릭 값(숫자) */
    [data-testid="stMetricValue"] div {
        color: #ffffff !important; /* 완전 흰색 고정 */
        font-weight: 800 !important;
        font-size: 2.3rem !important;
    }

    /* 3. 일반 텍스트 및 버튼 시인성 */
    h1, h2, h3 {
        font-weight: 800 !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #007bff;
        color: white !important;
        font-weight: bold;
        border: none;
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

# [개선] 안내 섹션 - 텍스트 색상 강제 지정으로 다크모드 대응
st.markdown("""
<div class="guide-box">
    <h3>📌 이용 방법 안내</h3>
    <ul>
        <li><b>파일 준비:</b> TXT 혹은 Excel(xlsx, xlsm) 파일을 준비합니다.</li>
        <li><b>자동 정제:</b> 하이픈(-)과 모든 공백(띄어쓰기, 탭)은 시스템이 자동으로 제거합니다.</li>
        <li><b>엑셀 데이터:</b> 엑셀 파일은 <b>첫 번째 열(A열)</b>의 데이터를 인식합니다.</li>
        <li><b>추출 기준:</b> 숫자로만 구성된 10자리 이상의 번호만 추출됩니다.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

guide_col1, guide_col2 = st.columns(2)

with guide_col1:
    st.markdown("### 📝 TXT 파일 예시")
    txt_img_path = os.path.join("images", "txt_example.png")
    if os.path.exists(txt_img_path):
        img_txt = Image.open(txt_img_path)
        resized_txt = img_txt.resize((500, 300), Image.Resampling.LANCZOS)
        st.image(resized_txt, caption="TXT 파일 예시", width=500)
    else:
        st.info("💡 images/txt_example.png 파일이 필요합니다.")

with guide_col2:
    st.markdown("### 📊 Excel 파일 예시")
    excel_img_path = os.path.join("images", "excel_example.png")
    if os.path.exists(excel_img_path):
        img_excel = Image.open(excel_img_path)
        resized_excel = img_excel.resize((500, 300), Image.Resampling.LANCZOS)
        st.image(resized_excel, caption="Excel 파일 예시", width=500)
    else:
        st.info("💡 images/excel_example.png 파일이 필요합니다.")

st.markdown("---")

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
            clean_num = item.replace("-", "").replace(" ", "").replace("\t", "").strip()
            if clean_num.isdigit() and len(clean_num) >= 10:
                biz_nums.append(clean_num)
        
        if biz_nums:
            st.metric("추출된 유효 번호", f"{len(biz_nums)} 건")
        else:
            st.warning("유효한 사업자 번호를 찾을 수 없습니다.")

    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

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

    st.markdown("## 📊 조회 결과 리포트")
    res_col1, res_col2, res_col3 = st.columns(3)
    
    res_col1.metric("전체 조회 건수", f"{len(results)}건")
    res_col2.metric("정상(계속사업자)", f"{normal_count}건")
    res_col3.metric("주의 필요 대상", f"{len(abnormal)}건")

    if len(abnormal) > 1:
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
    elif len(abnormal) == 0:
        st.balloons()
        st.success("✨ 모든 사업자가 정상 상태(계속사업자)입니다!")
