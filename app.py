import streamlit as st
import requests
import json
import time
import datetime
import pandas as pd
from io import BytesIO
import os

# ==========================================
# 1. 앱 관리 및 시스템 설정
# ==========================================

# [기능] 앱 전체 중지 스위치 (True로 변경 시 앱 작동 중지)
APP_DISABLED = False 

if APP_DISABLED:
    st.error("🚫 현재 시스템 점검 중으로 서비스를 일시 중단합니다.")
    st.stop()

# [기능] 브라우저 탭 이름 및 레이아웃 설정
st.set_page_config(
    page_title="사업자 등록 상태 조회 시스템",
    page_icon="🏢", 
    layout="wide"
)

# --- [설정 1: 만료 날짜] ---
EXPIRY_DATE = datetime.date(2026, 12, 31)

# --- [설정 2: API 정보 및 보안] ---
SERVICE_KEY = st.secrets.get("SERVICE_KEY")

def check_license():
    """날짜 만료 체크 함수"""
    if datetime.date.today() > EXPIRY_DATE:
        st.error(f"🛑 서비스 이용 기간이 만료되었습니다. (만료일: {EXPIRY_DATE})")
        st.stop()

def check_biz_status(biz_nums):
    """국세청 API 호출 로직"""
    if not SERVICE_KEY:
        st.error("API 서비스 키가 설정되어 있지 않습니다. Secrets 설정을 확인하세요.")
        st.stop()
        
    API_URL = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={SERVICE_KEY}"
    HEADERS = {"Content-Type": "application/json"}
    
    all_results = []
    progress_bar = st.progress(0)
    
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
        progress = min((i + 100) / len(biz_nums), 1.0)
        progress_bar.progress(progress)
        time.sleep(0.2)
    return all_results

# ==========================================
# 2. 메인 UI 화면
# ==========================================

with st.sidebar:
    st.header("⚙️ 서비스 정보")
    st.info(f"📅 만료 예정일: {EXPIRY_DATE}")

st.title("🏢 사업자 등록 상태 일괄 조회")
check_license()
st.divider()

# --- [안내 섹션] 이용 방법 및 파일 예시 ---
st.subheader("📋 이용 방법 및 파일 예시")
col1, col2 = st.columns([1, 1.2]) 

with col1:
    st.markdown("""
    1. **사업자 등록 번호**가 한 줄에 하나씩 적힌 **TXT 파일**을 준비합니다.
    2. 번호 사이의 하이픈(`-`)은 자동으로 제거되니 안심하세요.
    3. 아래의 **파일 업로드** 섹션에 파일을 업로드합니다.
    4. **조회 시작** 버튼을 누르면 실시간 국세청 조회가 시작됩니다.
    """)

with col2:
    # 💡 수정된 경로: images 폴더 안의 example.png를 참조합니다.
    image_path = os.path.join("images", "example.png") 
    
    if os.path.exists(image_path):
        st.image(image_path, caption="업로드용 메모장(.txt) 예시 파일", use_container_width=True)
    else:
        # 이미지가 없을 경우 사용자에게 폴더 구조 가이드를 보여줌
        st.info("💡 Tip: 'images' 폴더에 'example.png' 파일을 넣으면 여기에 예시 사진이 나타납니다.")

st.divider()

# 파일 업로더
uploaded_file = st.file_uploader("사업자번호 TXT 파일을 업로드하세요.", type=["txt"])

if uploaded_file:
    raw_data = uploaded_file.read()
    try:
        content = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError:
        content = raw_data.decode("cp949")

    biz_nums = [line.strip().replace("-", "") for line in content.splitlines() if line.strip()]
    total_count = len(biz_nums)
    st.metric(label="총 업로드 건수", value=f"{total_count} 건")
    
    if st.button(f"🚀 {total_count}건 일괄 조회 시작"):
        with st.spinner("국세청 데이터를 가져오는 중..."):
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

            st.divider()
            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("조회 완료", f"{len(results)}건")
            res_col2.metric("정상(계속)", f"{normal_count}건")
            res_col3.metric("휴/폐업 등", f"{len(abnormal)}건")

            if len(abnormal) > 0:
                st.warning(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 발견되었습니다.")
                df = pd.DataFrame(abnormal)
                df.index = df.index + 1
                df.index.name = '번호'
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드 파일 생성
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True, sheet_name='조회결과')
                    workbook  = writer.book
                    worksheet = writer.sheets['조회결과']
                    border_format = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
                    worksheet.set_column(0, 0, 10, border_format)
                    for i, col in enumerate(df.columns):
                        max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 5
                        worksheet.set_column(i + 1, i + 1, max_len, border_format)
                
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 비정상 사업자 리스트 다운로드 (Excel)",
                    data=processed_data,
                    file_name=f"biz_result_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.balloons()
                st.success("✅ 모든 사업자가 '계속사업자' 상태입니다!")
