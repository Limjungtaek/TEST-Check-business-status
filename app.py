import streamlit as st
import requests
import json
import time
import datetime
import pandas as pd
from io import BytesIO

# --- [추가 기능: 앱 전체 중지 스위치] ---
# 필요할 때 아래 True를 False로 바꾸거나, UI에서 체크박스를 통해 제어할 수 있습니다.
APP_DISABLED = False  # 이 값을 True로 변경하면 앱이 즉시 중지됩니다.

if APP_DISABLED:
    st.error("🚫 현재 시스템 점검 중으로 서비스를 일시 중단합니다.")
    st.stop()

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

# --- [UI 설정] ---
st.set_page_config(page_title="사업자상태 조회_임정택", page_icon="🏢", layout="wide")

with st.sidebar:
    st.header("⚙️ 서비스 정보")
    st.info(f"📅 만료 예정일: {EXPIRY_DATE}")
    # 관리용 중지 스위치 (UI에서 직접 끄고 싶을 경우 사용)
    # stop_app = st.checkbox("관리자 모드: 앱 즉시 중지", value=False)
    # if stop_app: st.stop()

st.title("🏢 사업자 등록 상태 일괄 조회")
check_license()
st.divider()

uploaded_file = st.file_uploader("사업자번호 TXT 파일을 업로드하세요.", type=["txt"])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    biz_nums = [line.strip().replace("-", "") for line in content.splitlines() if line.strip()]
    total_count = len(biz_nums)
    st.metric(label="총 업로드 건수", value=f"{total_count} 건")
    
    if st.button(f"🚀 {total_count}건 일괄 조회 시작"):
        with st.spinner("데이터 조회 중..."):
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
            col1, col2, col3 = st.columns(3)
            col1.metric("조회 완료", f"{len(results)}건")
            col2.metric("정상(계속)", f"{normal_count}건")
            col3.metric("휴/폐업 등", f"{len(abnormal)}건")

            if len(abnormal) > 0:
                st.warning(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 발견되었습니다.")
                df = pd.DataFrame(abnormal)
                df.index = df.index + 1
                df.index.name = '번호'
                st.dataframe(df, use_container_width=True)
                
                # --- [엑셀 파일 생성 및 서식 지정] ---
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=True, sheet_name='조회결과')
                    
                    workbook  = writer.book
                    worksheet = writer.sheets['조회결과']
                    
                    # 1. 모든 셀에 테두리를 적용할 포맷 생성
                    border_format = workbook.add_format({
                        'border': 1,       # 테두리 두께
                        'align': 'left',   # 정렬
                        'valign': 'vcenter'
                    })
                    
                    # 2. 열 너비 자동 조절 및 테두리 적용
                    # Index(번호) 포함 모든 열에 대해 루프
                    for i, col in enumerate(df.columns):
                        # 열 이름의 길이나 데이터 중 가장 긴 길이를 계산
                        column_len = max(df[col].astype(str).map(len).max(), len(col)) + 5
                        # 데이터 영역에 테두리 적용 (set_column 사용)
                        worksheet.set_column(i + 1, i + 1, column_len, border_format)
                    
                    # 인덱스(A열) 처리
                    worksheet.set_column(0, 0, 10, border_format)
                
                processed_data = output.getvalue()
                
                st.download_button(
                    label="📥 비정상 사업자 리스트 다운로드 (Excel)",
                    data=processed_data,
                    file_name=f"biz_result_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.balloons()
                st.success("✅ 모두 정상입니다!")
