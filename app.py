import streamlit as st
import requests
import json
import time
import datetime
import pandas as pd

# --- [설정 1: 만료 날짜] ---
# 퇴사 등의 사유로 이용을 제한하고 싶을 때 이 날짜를 수정하세요.
EXPIRY_DATE = datetime.date(2026, 12, 31)

# --- [설정 2: API 정보 및 보안] ---
# 서비스 키는 Streamlit Cloud의 Secrets 설정에 넣으셔야 안전합니다.
SERVICE_KEY = st.secrets.get("SERVICE_KEY")

def check_license():
    """날짜 만료 체크 함수"""
    if datetime.date.today() > EXPIRY_DATE:
        st.error(f"🛑 서비스 이용 기간이 만료되었습니다. (만료일: {EXPIRY_DATE})")
        st.info("관리자에게 문의하여 기간을 연장하세요.")
        st.stop()

def check_biz_status(biz_nums):
    """국세청 API 호출 로직"""
    if not SERVICE_KEY:
        st.error("API 서비스 키가 설정되어 있지 않습니다. Streamlit Secrets 설정을 확인하세요.")
        st.stop()
        
    API_URL = f"https://api.odcloud.kr/api/nts-businessman/v1/status?serviceKey={SERVICE_KEY}"
    HEADERS = {"Content-Type": "application/json"}
    
    all_results = []
    progress_bar = st.progress(0)
    
    # 100개씩 끊어서 처리 (API 제한 대응)
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
            
        # 진행률 업데이트
        progress = min((i + 100) / len(biz_nums), 1.0)
        progress_bar.progress(progress)
        time.sleep(0.2)
        
    return all_results

# --- [UI 설정] ---
st.set_page_config(page_title="재고/정산 도우미 - 사업자 조회", page_icon="🏢", layout="wide")

# 사이드바 구성
with st.sidebar:
    st.header("⚙️ 서비스 정보")
    st.info(f"📅 만료 예정일: {EXPIRY_DATE}")
    st.write("---")
    st.caption("본 프로그램은 개인 자산으로 제작되었으며, API 키 보안을 위해 만료일 이후에는 작동이 중지됩니다.")

# 메인 화면
st.title("🏢 사업자 등록 상태 일괄 조회")
st.write(f"현재 업무 효율을 위해 제공되는 도구입니다. (이용 기한: ~ {EXPIRY_DATE})")

# 만료 체크 실행
check_license()

st.divider()

# 파일 업로드 (TXT)
uploaded_file = st.file_uploader("사업자번호가 한 줄에 하나씩 적힌 TXT 파일을 업로드하세요.", type=["txt"])

if uploaded_file:
    # 텍스트 파일 읽기 및 데이터 정제
    content = uploaded_file.read().decode("utf-8")
    biz_nums = [line.strip().replace("-", "") for line in content.splitlines() if line.strip()]

    # 1. 업로드 직후 요약 정보 표시
    total_count = len(biz_nums)
    st.subheader("📋 업로드 데이터 요약")
    st.metric(label="총 업로드 건수", value=f"{total_count} 건")
    
    # 조회 버튼
    if st.button(f"🚀 {total_count}건 일괄 조회 시작"):
        with st.spinner("국세청 서버에서 최신 상태를 가져오는 중입니다..."):
            results = check_biz_status(biz_nums)
            
            # 데이터 분류 (정상 vs 비정상)
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

            # 2. 결과 메트릭 표시
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("조회 완료", f"{len(results)}건")
            col2.metric("정상(계속)", f"{normal_count}건")
            col3.metric("휴/폐업 등", f"{len(abnormal)}건", delta=f"{len(abnormal)}건 발견", delta_color="inverse")

            # 3. 상세 결과 표 출력
            if len(abnormal) > 0:
                st.warning(f"⚠️ 확인이 필요한 사업자가 {len(abnormal)}건 있습니다.")
                
                # 데이터프레임 변환 및 인덱스 설정 (1부터 시작)
                df = pd.DataFrame(abnormal)
                df.index = df.index + 1  # 0부터 시작하는 인덱스를 1부터 시작하게 변경
                df.index.name = '번호'    # 인덱스 열의 이름을 '번호'로 설정
                
                # 표 출력 (번호 열이 제목과 함께 1부터 나옴)
                st.dataframe(df, use_container_width=True)
                
                # 다운로드 버튼
                csv = df.to_csv(index=True, encoding='utf-8-sig') # 번호 포함 저장
                st.download_button(
                    label="📥 비정상 사업자 리스트 다운로드 (CSV)",
                    data=csv,
                    file_name=f"biz_check_{datetime.date.today()}.csv",
                    mime="text/csv"
                )
            else:
                st.balloons()
                st.success("✅ 모든 사업자가 '계속사업자' 상태입니다. 문제가 없습니다!")
