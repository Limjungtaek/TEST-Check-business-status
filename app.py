# 아래 코드를 활성화하면 전체 코드가 실행되지 않도록 할 수 있습니다.
# (비활성화 상태, 필요 시 아래 if문 주석을 해제하여 사용)
# import sys
# sys.exit("이 코드는 현재 구동되지 않도록 비활성화 되어 있습니다.")

import streamlit as st
import requests
import json
import time
import datetime
import pandas as pd

# --- [설정 1: 만료 날짜] ---
EXPIRY_DATE = datetime.date(2026, 12, 31)

# --- [설정 2: API 정보] ---
SERVICE_KEY = st.secrets.get("SERVICE_KEY")
if not SERVICE_KEY:
    st.error("API 서비스 키가 설정되어 있지 않습니다. 관리자에게 문의하시거나 `.streamlit/secrets.toml` 파일에 SERVICE_KEY 항목을 추가하세요.")
    st.stop()

API_URL = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={SERVICE_KEY}"
HEADERS = {"Content-Type": "application/json"}

def check_license():
    """날짜 만료 체크"""
    if datetime.date.today() > EXPIRY_DATE:
        st.error(f"🛑 서비스 이용 기간이 만료되었습니다. (만료일: {EXPIRY_DATE})")
        st.stop()

def check_biz_status(biz_nums):
    """사업자 상태 조회 로직"""
    all_results = []
    progress_bar = st.progress(0)
    
    # 100개씩 끊어서 처리
    for i in range(0, len(biz_nums), 100):
        chunk = biz_nums[i:i+100]
        payload = {"b_no": chunk}
        
        try:
            response = requests.post(API_URL, headers=HEADERS, data=json.dumps(payload), timeout=10)
            if response.status_code == 200:
                result = response.json()
                all_results.extend(result.get("data", []))
        except Exception as e:
            st.error(f"조회 중 오류 발생: {e}")
            break
            
        # 진행 바 업데이트
        progress = min((i + 100) / len(biz_nums), 1.0)
        progress_bar.progress(progress)
        time.sleep(0.2)
        
    return all_results

# --- 웹 화면 구성 ---
st.set_page_config(page_title="사업자 상태 조회기", page_icon="🏢")

# --- 사이드바 만료 안내 ---
with st.sidebar:
    st.info(f"ℹ️ 본 서비스는 {EXPIRY_DATE} 까지 사용 가능합니다.")

st.title("🏢 사업자 등록 상태 일괄 조회")
st.write(f"사용 가능 기한: ~ {EXPIRY_DATE}")

check_license()

# 파일 업로드 (TXT)
uploaded_file = st.file_uploader("사업자번호가 담긴 TXT 파일을 업로드하세요.", type=["txt"])

if uploaded_file:
    # 텍스트 파일 읽기 및 번호 추출
    content = uploaded_file.read().decode("utf-8")
    biz_nums = [line.strip() for line in content.splitlines() if line.strip()]

    # --- 메트릭 카드: 전체/정상/휴폐업 건수 요약 표시 (업로드 시 표시) ---
    st.subheader("사업자번호 건수 요약")
    total_count = len(biz_nums)
    st.columns(3)  # 보조용, 실제 결과 나오기 전 넓이 확보

    # 결과 전 메트릭(임시, 아직 분류 안 됨)
    st.metric(label="전체 업로드 건수", value=total_count)
    st.write("")

    if st.button(f"{len(biz_nums)}건 조회 시작"):
        with st.spinner("국세청 데이터를 조회 중입니다..."):
            results = check_biz_status(biz_nums)
            # 카운트 분류
            abnormal = [
                {
                    "사업자번호": item.get('b_no'),
                    "상태": item.get('b_stt'),
                    "폐업일자": item.get('end_dt') if item.get('end_dt') else "-"
                } 
                for item in results if item.get("b_stt") != "계속사업자"
            ]
            normal = [
                {
                    "사업자번호": item.get('b_no'),
                    "상태": item.get('b_stt'),
                    "폐업일자": item.get('end_dt') if item.get('end_dt') else "-"
                }
                for item in results if item.get("b_stt") == "계속사업자"
            ]
            cnt_total = len(results)
            cnt_normal = len(normal)
            cnt_abnormal = len(abnormal)

            # --- 상단 메트릭 카드(전체,정상,휴폐업) ---
            col1, col2, col3 = st.columns(3)
            col1.metric("전체 조회 건수", cnt_total)
            col2.metric("정상(계속사업자)", cnt_normal)
            col3.metric("휴/폐업 등", cnt_abnormal)
            
            st.divider()
            
            if cnt_abnormal == 0:
                st.balloons()
                st.success("✅ 조회된 모든 사업자가 '계속사업자' 상태입니다!")
            else:
                st.warning(f"⚠️ 휴/폐업 상태인 사업자가 {cnt_abnormal}건 발견되었습니다.")
                
                # 결과 테이블 출력
                df = pd.DataFrame(abnormal)
                st.table(df) # 혹은 st.dataframe(df) 사용 가능
                
                # 결과 다운로드 (CSV)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 비정상 사업자 리스트 다운로드 (CSV)",
                    data=csv,
                    file_name="abnormal_biz_list.csv",
                    mime="text/csv"
                )
