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
    page_title="사업자 등록 상태 조회 시스템 v2.0",
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
    progress_text = "조회 중입니다. 잠시만 기다려 주세요."
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

# 사이드바 개선
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/city-buildings.png", width=80)
    st.title("Business Checker")
    st.markdown("---")
    st.info(f"**상태:** 운영 중\n\n**만료일:** {EXPIRY_DATE}")
    st.caption("© 2026 Lim Jung-taek. All rights reserved.")

# 헤더 섹션
st.title("🏢 사업자 등록 상태 일괄 조회 시스템")
check_license()

# 이용 안내를 Expander로 묶어 화면을 깔끔하게 유지
with st.expander("📌 이용 방법 및 파일 예시 (처음이시라면 클릭하세요)", expanded=False):
    guide_col1, guide_col2 = st.columns([2, 1])
    with guide_col1:
        st.markdown("""
        1. **사업자 등록 번호**가 한 줄에 하나씩 적힌 **TXT 파일**을 준비합니다.
        2. 번호 사이의 하이픈(`-`)은 시스템이 자동으로 제거합니다.
        3. 아래 **업로드 섹션**에 파일을 드래그 앤 드롭 하세요.
        4. **일괄 조회 시작** 버튼을 누르면 실시간 결과가 출력됩니다.
        """)
    with guide_col2:
        image_path = os.path.join("images", "example.png") 
        if os.path.exists(image_path):
            img = Image.open(image_path)
            resized_img = img.resize((250, 180), Image.Resampling.LANCZOS)
            st.image(resized_img, caption="권장 TXT 형식 예시", width=250)

st.markdown("---")

# 업로드 섹션 디자인
main_container = st.container()
with main_container:
    col_up1, col_up2 = st.columns([2, 1])
    with col_up1:
        uploaded_file = st.file_uploader("사업자번호 TXT 파일을 업로드하세요", type=["txt"], help="메모장에서 작성한 .txt 파일만 지원합니다.")
    with col_up2:
        if uploaded_file:
            raw_data = uploaded_file.read()
            try:
                content = raw_data.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = raw_data.decode("cp949")
            
            biz_nums = [line.strip().replace("-", "") for line in content.splitlines() if line.strip()]
            st.metric("업로드된 번호", f"{len(biz_nums)} 건")

# 조회 실행 버튼 및 결과
if uploaded_file and st.button(f"🚀 {len(biz_nums)}건 국세청 실시간 조회 시작"):
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
                "폐업일자": item.get('end_dt') if item.get('end_dt') else "-"
            })

    # 결과 대시보드
    st.subheader("📊 조회 결과 리포트")
    res_col1, res_col2, res_col3 = st.columns(3)
    res_col1.metric("전체 조회", f"{len(results)}건", delta_color="off")
    res_col2.metric("정상 사업자", f"{normal_count}건")
    res_col3.metric("주의/폐업", f"{len(abnormal)}건", delta=f"-{len(abnormal)}" if len(abnormal)>0 else None, delta_color="inverse")

    if len(abnormal) > 0:
        st.error(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 있습니다. 아래 명단을 확인하세요.")
        df = pd.DataFrame(abnormal)
        df.index = df.index + 1
        st.dataframe(df, use_container_width=True)
        
        # 엑셀 생성 로직 (동일)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=True, sheet_name='조회결과')
            workbook = writer.book
            worksheet = writer.sheets['조회결과']
            border_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            worksheet.set_column(0, 0, 10, border_format)
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 5
                worksheet.set_column(i + 1, i + 1, max_len, border_format)
        
        st.download_button(
            label="📥 결과 리스트 다운로드 (Excel)",
            data=output.getvalue(),
            file_name=f"biz_check_result_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.balloons()
        st.success("✨ 모든 사업자가 정상 상태(계속사업자)인 것으로 확인되었습니다!")
