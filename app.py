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
    page_title="사업자 등록 상태 조회 시스템 v2.4",
    page_icon="🏢", 
    layout="wide"
)

# 전문가 스타일을 위한 CSS 주입
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        border: none;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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

# 사이드바
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/city-buildings.png", width=80)
    st.title("Business Checker")
    st.markdown("---")
    st.info(f"**상태:** 운영 중\n\n**만료일:** {EXPIRY_DATE}")
    st.caption("© 2026 Lim Jung-taek. All rights reserved.")

# 헤더 섹션
st.title("🏢 사업자 등록 상태 일괄 조회 시스템")
check_license()

# 이용 안내 (이미지 2개 배치 및 350*250 크기 고정)
with st.expander("📌 이용 방법 및 파일 형식 예시 (확인하려면 클릭)", expanded=False):
    st.markdown("파일 형식에 상관없이 **하이픈(`-`)과 모든 공백(띄어쓰기)**은 시스템이 자동으로 제거합니다.")
    
    guide_col1, guide_col2 = st.columns(2)
    
    with guide_col1:
        st.markdown("### 📝 TXT 파일 예시")
        st.write("메모장에 한 줄에 하나씩 번호를 입력하세요.")
        txt_img_path = os.path.join("images", "txt_example.png")
        if os.path.exists(txt_img_path):
            img_txt = Image.open(txt_img_path)
            # 가로 350, 세로 250으로 리사이징
            resized_txt = img_txt.resize((350, 250), Image.Resampling.LANCZOS)
            st.image(resized_txt, caption="TXT 파일 작성 예시", width=350)
        else:
            st.info("💡 `images/txt_example.png` 파일을 준비해 주세요.")

    with guide_col2:
        st.markdown("### 📊 Excel 파일 예시")
        st.write("첫 번째 열(A열)에 번호를 입력하세요.")
        excel_img_path = os.path.join("images", "excel_example.png")
        if os.path.exists(excel_img_path):
            img_excel = Image.open(excel_img_path)
            # 가로 350, 세로 250으로 리사이징
            resized_excel = img_excel.resize((350, 250), Image.Resampling.LANCZOS)
            st.image(resized_excel, caption="Excel 파일 작성 예시", width=350)
        else:
            st.info("💡 `images/excel_example.png` 파일을 준비해 주세요.")

st.markdown("---")

# 업로드 섹션
uploaded_file = st.file_uploader("사업자번호 파일을 업로드하세요 (TXT, XLSX, XLSM 지원)", type=["txt", "xlsx", "xlsm"])

biz_nums = []

if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1].lower()
    raw_list = []

    try:
        # 1. 엑셀 파일 처리
        if file_ext in ["xlsx", "xlsm"]:
            df_input = pd.read_excel(uploaded_file, header=None)
            raw_list = df_input.iloc[:, 0].dropna().astype(str).tolist()
        
        # 2. TXT 파일 처리
        else:
            raw_data = uploaded_file.read()
            try:
                content = raw_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = raw_data.decode("cp949")
            raw_list = content.splitlines()

        # 하이픈 및 모든 공백(띄어쓰기) 제거
        for item in raw_list:
            clean_num = item.replace("-", "").replace(" ", "").strip()
            # 숫자로만 구성된 유효한 번호(최소 10자리)만 추출
            if clean_num.isdigit() and len(clean_num) >= 10:
                biz_nums.append(clean_num)
        
        if biz_nums:
            st.metric("추출된 유효 번호", f"{len(biz_nums)} 건")
        else:
            st.warning("유효한 사업자 번호를 찾을 수 없습니다. 파일 내용을 확인해 주세요.")

    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# 조회 실행 버튼 및 결과 리포트
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

    # 결과 요약 대시보드
    st.subheader("📊 조회 결과 리포트")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("전체 조회", f"{len(results)}건")
    res_col2.metric("정상 사업자", f"{normal_count}건")
    res_col3.metric("주의/폐업", f"{len(abnormal)}건", 
                   delta=f"-{len(abnormal)}" if len(abnormal)>0 else None, 
                   delta_color="inverse")

    if len(abnormal) > 0:
        st.error(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 있습니다. 아래 명단을 확인하세요.")
        df_res = pd.DataFrame(abnormal)
        df_res.index = df_res.index + 1
        st.dataframe(df_res, use_container_width=True)
        
        # 엑셀 다운로드 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_res.to_excel(writer, index=True, sheet_name='주의사업자명단')
            
        st.download_button(
            label="📥 결과 리스트 다운로드 (Excel)",
            data=output.getvalue(),
            file_name=f"biz_check_result_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.balloons()
        st.success("✨ 모든 사업자가 정상 상태(계속사업자)인 것으로 확인되었습니다!")
