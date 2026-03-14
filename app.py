import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# 1. 과목 및 설정 (수정 시 이 부분만 확인하세요)
# ---------------------------------------------------------
SUBJECT_NAME = "소비자재무설계 퀴즈"  # 과목 제목
CURRENT_WEEK = "3주차"           # 해당 주차
ADMIN_PASSWORD = "3383"          # 선생님용 비밀번호

# 퀴즈 데이터 (수동으로 제공해주신 7문항 반영)
QUIZ_DATA = [
    {"q": "1. 이슈1의 입장A의 전략 중 하나로, 자산의 조기 축적을 통해 일찍 현업에서 벗어나려는 준비를 일컫는 용어는 무엇인가? 영어(대문자)로 답하세요.", "a": "FIRE"},
    {"q": "2. 경제적 복지의 4가지 유형 중에서, 객관적 조건은 좋은데, 주관적 평가가 불만족인 유형은?", "a": "주관적 불만형"},
    {"q": "3. 생애재무설계는 나와 우리 가족의 재무목표를 구체적으로 정한 뒤 그 목표를 달성하기 위해 계획을 세우고 실행하는 것이다. 생애재무설계는 (___________) 정리하기로 시작한다.", "a": "재무목표"},
    {"q": "4. “저 사람(판매자)이 왜 저런 제안을 할까? 나에게 도움이 될까?”라는 의문을 풀기 위한 소비자들이 축적한 경험과 노하우는 무엇인가?", "a": "설득지식"},
    {"q": "5. 시간해석이론에 따르면 사람들은 시간적으로 멀리 있는 대상은 (___________), 본질적, 특징적인 점에 집중해 해석하고, 시간적으로 가까운 대상은 (____________), 표면적, 사소한 점에 주목해 해석한다.", "a": "추상적, 구체적"},
    {"q": "6. 돈을 벌고, 쓰고, 저축하고, 투자하고, 빌리는 개인의 재무적 행동능력과 태도, 가치를 의식적 또는 무의식적으로 배우는 과정은 무엇인가?", "a": "금융사회화"},
    {"q": "7. 돈과 관련된 부부 갈등의 발생 원인은 소득 감소, (_______________), 소비 습관의 차이 등이다.", "a": "재무적 부정직"}
]

NUM_QUESTIONS = len(QUIZ_DATA) 
# ---------------------------------------------------------

# 페이지 설정
st.set_page_config(page_title=f"{SUBJECT_NAME}", layout="wide")

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("구글 시트 연결 설정(Secrets)이 필요합니다.")

if "submitted_on_this_device" not in st.session_state:
    st.session_state.submitted_on_this_device = False

st.title(f"📊 {SUBJECT_NAME}")

tab1, tab2, tab3 = st.tabs(["✍️ 퀴즈 제출", "🖥️ 제출자 명단 확인", "🔐 성적 분석(교수용)"])

# --- [TAB 1] 학생 제출 화면 ---
with tab1:
    st.header("답안지")
    
    if st.session_state.submitted_on_this_device:
        st.warning("⚠️ 이 기기에서 제출이 완료되었습니다. 응시는 더 이상 불가능합니다.")
    else:
        with st.form("quiz_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("이름", placeholder="이름")
            with col2:
                student_id = st.text_input("학번", placeholder="학번")
            
            st.divider()
            
            user_responses = []
            for i, item in enumerate(QUIZ_DATA):
                st.markdown(f"**{item['q']}**")
                ans = st.text_input(f"{i+1}번 답안", key=f"q{i}")
                user_responses.append(ans)

            submitted = st.form_submit_button("답안 제출하기")

            if submitted:
                if not name or not student_id:
                    st.error("이름과 학번을 입력해 주세요.")
                else:
                    try:
                        # 제출 시 중복 확인을 위해 실시간 데이터 읽기
                        master_df = conn.read(worksheet="전체데이터", ttl=0)
                        
                        already_exists = master_df[
                            (master_df['주차'] == CURRENT_WEEK) & 
                            (master_df['학번'] == student_id)
                        ]

                        if not already_exists.empty:
                            st.error(f"❌ {name} 학생은 이미 이번 주 답안을 제출했습니다.")
                        else:
                            kst = timezone(timedelta(hours=9))
                            now_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
                            
                            row_dict = {
                                "주차": CURRENT_WEEK,
                                "제출시간": now_time,
                                "이름": name,
                                "학번": student_id
                            }
                            
                            # 채점 로직 (영어 대소문자 무시 적용)
                            total_correct = 0
                            for i, item in enumerate(QUIZ_DATA, 1):
                                # 양측 답안 모두 공백 제거 및 소문자 변환 후 비교
                                s_ans_set = set(item['a'].replace(" ", "").lower().split(","))
                                u_ans_set = set(user_responses[i-1].replace(" ", "").lower().split(","))
                                
                                is_correct = (s_ans_set == u_ans_set)
                                if is_correct: total_correct += 1
                                
                                row_dict[f"q{i}_답"] = user_responses[i-1]
                                row_dict[f"q{i}_결과"] = "O" if is_correct else "X"
                            
                            row_dict["총점"] = total_correct
                            
                            # 데이터 업데이트
                            updated_master = pd.concat([master_df, pd.DataFrame([row_dict])], ignore_index=True)
                            conn.update(worksheet="전체데이터", data=updated_master)
                            
                            st.session_state.submitted_on_this_device = True
                            st.success(f"{name} 학생, 제출 성공! ({total_correct}/{NUM_QUESTIONS})")
                            # st.balloons() # 트래픽 최적화를 위해 애니메이션 주석 처리 권장
                            st.rerun() 
                            
                    except Exception as e:
                        # 과부하 시 pass 처리하여 사용자 불편 최소화
                        pass

# --- [TAB 2] 제출 명단 확인 (트래픽 최적화 적용) ---
with tab2:
    st.subheader(f"📍 {CURRENT_WEEK} 제출 완료 명단")
    st.info("명단을 확인하려면 아래 버튼을 누르세요.")
    
    if st.button("🔄 명단 확인/새로고침"):
        try:
            # 트래픽 부하 감소를 위해 5분 캐시(ttl=300) 적용
            data = conn.read(worksheet="전체데이터", ttl=300)
            today_list = data[data['주차'] == CURRENT_WEEK]
            
            if not today_list.empty:
                st.write(f"현재 총 {len(today_list)}명 제출 완료")
                cols = st.columns(6)
                for i, row in enumerate(today_list.itertuples()):
                    cols[i % 6].success(f"✅ {row.이름}")
            else:
                st.write("아직 제출자가 없습니다.")
        except:
            st.error("데이터 로드 실패")

# --- [TAB 3] 성적 분석 ---
with tab3:
    st.header("🔐 관리자 인증")
    admin_pw = st.text_input("비밀번호를 입력하세요", type="password")
    
    if admin_pw == ADMIN_PASSWORD:
        st.success("인증 성공")
        try:
            # 관리자용 데이터는 실시간 로드
            data = conn.read(worksheet="전체데이터", ttl=0)
            if not data.empty:
                st.subheader("학생별 평균 정답률")
                stats = data.groupby(['학번', '이름'])['총점'].mean().reset_index()
                stats['정답률(%)'] = (stats['총점'] / NUM_QUESTIONS * 100).round(1)
                st.dataframe(stats, use_container_width=True)
                st.divider()
                st.download_button("엑셀 데이터 다운로드", data=data.to_csv(index=False).encode('utf-8-sig'), file_name=f"{SUBJECT_NAME}_결과.csv", mime="text/csv")
            else:
                st.info("데이터가 없습니다.")
        except:
            st.error("데이터 로드 실패")
    elif admin_pw != "":
        st.error("비밀번호 불일치")

