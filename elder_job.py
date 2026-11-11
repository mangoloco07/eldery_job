import streamlit as st
import pandas as pd
import json
from openai import OpenAI


# API 설정
st.set_page_config(page_title="노인 일자리 매칭 도움 AI", page_icon="👵👴", layout="wide")

st.sidebar.title("🔑 API 및 시스템 설정")
openai_api_key = st.sidebar.text_input(
    "OpenAI API Key 입력", 
    type="password", 
    help="sk-... 형태의 API 키를 입력하세요."
)

# 사업분류코드 및 기본 채용 조건
LITERACY_CODES = {"B-02", "B-09", "B-12"}
WALKING_CODES = {"A-02", "A-13", "A-16", "A-18", "A-08", "B-08", "E-13", "E-14", "E-15"}
HOURS_CODES = {f"E-0{i}" if i < 10 else f"E-{i}" for i in range(1, 13)}

RAW_BUSINESS_DATA = [
    ("A-01", "공익활동", "노노케어(정서지원)", "취약노인 가구를 방문하여 안부확인 및 말벗, 정서관리 등 수행"),
    ("A-02", "공익활동", "노노케어(활동지원)", "취약노인 가구를 방문하여 수혜노인 활동 지원 및 일상동행, 생활실태 점검 등 수행"),
    ("A-03", "공익활동", "장애인봉사", "지역 내 장애인 가정 및 장애인 보호시설, 학교 내 특수학급 등 지원"),
    ("A-04", "공익활동", "취약가정봉사", "지역 내 다문화가정 및 한부모 가족 상담, 정서지원, 아동보호 서비스 제공"),
    ("A-05", "공익활동", "청소년 선도 봉사", "청소년 비행우발지역 선도 및 상담지원"),
    ("A-06", "공익활동", "생활시설 이용자 지원 봉사", "재가복지시설, 장애인 및 아동생활시설 등 취약계층 이용자 지원"),
    ("A-07", "공익활동", "학교급식 지원봉사", "학생 대상 급식 및 식사예절 지도 등 지원"),
    ("A-08", "공익활동", "스쿨존 교통지원 봉사", "유치원/학교 주변 교통정리, 교통안전 캠페인 및 어린이 안심 등하교 지원"),
    ("A-09", "공익활동", "CCTV상시관제", "학교 내·외부 CCTV 모니터링 후 문제 발생 시 구두보고 및 조치 요청"),
    ("A-10", "공익활동", "보육시설봉사", "보육교사 보조, 생활지도 및 강의 등 지원"),
    ("A-11", "공익활동", "지역아동센터봉사", "지역아동센터 아동의 방과후 교육, 귀가 및 급식 등 지원"),
    ("A-12", "공익활동", "도서관봉사", "국·공립 및 초·중·고등학교 도서관 관리지원"),
    ("A-13", "공익활동", "공원·놀이터 지원봉사", "공원, 놀이터 등 야외 공공시설 관리지원"),
    ("A-14", "공익활동", "문화재 시설 봉사", "지역 문화재 보호, 훼손방지 및 관람편의 제공 지원"),
    ("A-15", "공익활동", "공공업무 및 복지시설 지원봉사", "보건소, 복지기관, 경로당, 유기동물 보호센터 매니저, 위생지원단 등 지원"),
    ("A-16", "공익활동", "지역사회 환경개선 봉사", "지역 내 주거환경 및 생태환경 정화 업무"),
    ("A-17", "공익활동", "자원순환 및 재활용 지원봉사", "아이스팩/커피찌꺼기/종이팩/플라스틱/폐건전지/폐의약품 수거 및 자원순환 봉사"),
    ("A-18", "공익활동", "교통 지원 봉사", "주차 혼잡지역 질서유지 및 계도, 전기차 충전소 관리원 등"),
    ("A-19", "공익활동", "지역사회안전망 구축 지원", "지역사회 방역활동, 안전 위해 요소 점검(지하철, 파손도로) 등"),
    ("A-20", "공익활동", "기타 공공서비스", "기타 분류 안 된 공공서비스 활동"),
    ("A-21", "공익활동", "건강 체조 취미생활 지도", "체육(건강) 및 각종 취미관련 경륜전수 활동"),
    ("A-22", "공익활동", "문화공연 활동", "복지소외지역 또는 각종 생활시설 등 대상 문화 제공활동"),
    ("A-23", "공익활동", "체험 활동 지원", "지역 내 숲 체험 및 문화체험 해설지원 등"),
    ("A-24", "공익활동", "경륜전수 활동", "유아 및 초·중학생 대상 경륜전수 활동"),
    ("A-29", "공익활동", "경로당 배식 지원", "경로당 내 배식 등 지원"),

    ("B-01", "역량활용", "보육시설 운영지원", "어린이집 운영지원"),
    ("B-02", "역량활용", "교육시설 운영지원", "유치원, 초·중·고등학교, 대학, 평생교육시설 등 운영지원"),
    ("B-03", "역량활용", "돌봄·양육·생활시설 운영지원", "공동육아나눔터, 다함께돌봄센터, 지역아동센터, 보육원, 건강가정지원센터 등 운영지원"),
    ("B-04", "역량활용", "노인시설 운영지원", "노인복지시설, 재가노인복지시설, 치매안심센터 등 운영 및 노인맞춤돌봄서비스 지원"),
    ("B-05", "역량활용", "장애인시설 운영지원", "장애인 거주시설, 자립생활지원시설, 직업재활시설 등 운영지원"),
    ("B-06", "역량활용", "국가·지자체·공공단체 시설 운영지원", "행정복지센터, 의료시설, 치안시설, 우체국, 소방서 등 운영지원"),
    ("B-07", "역량활용", "지역 시설·기관 운영지원", "지역 내 사회적경제조직, 수요처 운영지원 및 복지 서비스 제공"),
    ("B-08", "역량활용", "안전관리 지원 (14개)", "디지털 교통안전 도우미, 바다안전순찰대, 승강기안전단, 치안지킴이 등 안전점검"),
    ("B-09", "역량활용", "보건관리 지원 (9개)", "건강의료서비스매니저, 디지털 헬스케어 매니저, 자살예방 상담원 등 보건증진 지원"),
    ("B-10", "역량활용", "환경보존 지원 (3개)", "나눔자원관리, 산림자원보존사업단, 생태도슨트 등 환경보존 활동"),
    ("B-11", "역량활용", "돌봄 지원 (12개)", "고독사예방게이트키퍼, 발달장애인 활동매니저, 온동네 초등돌봄(늘봄학교), 응급안전 지킴이 등"),
    ("B-12", "역량활용", "국민편의 지원 (17개)", "다문화 정착지원, 공항서포터즈, 금융업무지원, 연금가이드, 점자 도우미 등 서비스 안내"),

    ("E-01", "공동체사업단", "식품제조-간식류", "식재료를 활용하여 간식류 식품 제조 및 판매"),
    ("E-02", "공동체사업단", "식품제조-참기름 및 장류", "참기름, 장류 등 식품 제조 및 판매"),
    ("E-03", "공동체사업단", "식품제조-도시락 및 반찬류", "도시락 및 반찬류 식품 제조 및 판매"),
    ("E-04", "공동체사업단", "식품제조-기타", "기타 식품 제조 및 판매"),
    ("E-05", "공동체사업단", "공산품제작-비누류", "규격에 맞춘 비누류 공산품 제작 및 판매"),
    ("E-06", "공동체사업단", "공산품제작-봉제제품", "봉제제품 제작 및 판매"),
    ("E-07", "공동체사업단", "매장운영-카페", "소규모 실버 카페 매장 운영"),
    ("E-08", "공동체사업단", "매장운영-음식점", "소규모 음식점 매장 운영"),
    ("E-09", "공동체사업단", "매장운영-매점(편의점)", "소규모 매점 및 편의점 운영"),
    ("E-10", "공동체사업단", "매장운영-기타", "기타 소규모 매장 및 점포 운영"),
    ("E-11", "공동체사업단", "지역영농", "유·휴경지를 활용하여 콩, 고사리 등 농산물 공동 경작 및 판매"),
    ("E-12", "공동체사업단", "기타 공산품제조/서비스", "사업 수익을 통해 재화 및 기타 서비스 제공"),
    ("E-13", "공동체사업단", "운송-아파트 택배", "아파트 단지 내 택배 물품 배송 및 집하"),
    ("E-14", "공동체사업단", "운송-지하철 택배", "지하철을 이용하여 각종 수하물 및 서류 배달"),
    ("E-15", "공동체사업단", "운송-기타", "기타 물품 운송 및 배달 서비스"),
    ("E-16", "공동체사업단", "이미용 서비스", "이미용 서비스 제공"),
    ("E-17", "공동체사업단", "세차 서비스", "차량 세차 서비스 제공"),
    ("E-18", "공동체사업단", "세탁 서비스", "세탁 서비스 제공"),
    ("E-19", "공동체사업단", "기타 서비스", "기타 공동체사업단 서비스 제공")
]

BUSINESS_CODES = {}
for code, category, name, desc in RAW_BUSINESS_DATA:
    BUSINESS_CODES[code] = {
        "category": category,
        "name": name,
        "desc": desc,
        "req_walking": code in WALKING_CODES,
        "req_literacy": code in LITERACY_CODES,
        "is_hours": code in HOURS_CODES
    }

# 세션 
if "db1_jobs" not in st.session_state:
    st.session_state.db1_jobs = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "안녕하세요, 어르신! 반갑습니다. 일자리 안내를 도와드릴 스마트 도우미입니다. 편하게 이야기 나누어요."}
    ]

if "senior_db2" not in st.session_state:
    st.session_state.senior_db2 = None

if "db2_preferences" not in st.session_state:
    st.session_state.db2_preferences = {}

# 기타 채용 조건과의 일치도 점수 
def calculate_a_index_with_llm(client, senior_exps, job_extras):
    """
    단순 키워드 일치를 넘어 의미상 연관성(예: '요리'↔'조리', '택배'↔'배달')을
    분석하고 a지수 점수(50~100점) 및 매칭 근거를 반환합니다.
    """
    exact_matched = list(set(job_extras).intersection(set(senior_exps)))
    
    if not job_extras:
        return 50.0, ["기본 일치"]
    if not senior_exps:
        return 50.0, ["미입력"]
        
    if not client:
        score = min(50 + len(exact_matched) * 25, 100)
        return float(score), exact_matched if exact_matched else ["기본 일치"]

    try:
        prompt = (
            "당신은 노인일자리 직무-역량 매칭 전문가입니다.\n"
            "구직자의 과거 경력 및 자격 목록과 채용 우대 조건(기타 채용 조건) 목록을 비교하여 의미적 연관성을 평가해 주세요.\n\n"
            f"구직자 경력 및 자격: {json.dumps(senior_exps, ensure_ascii=False)}\n"
            f"채용 우대조건: {json.dumps(job_extras, ensure_ascii=False)}\n\n"
            "평가 규칙:\n"
            "1. 단순 단어 일치뿐만 아니라 의미가 통하는 유의어/연관역량(예: '요리'↔'조리', '택배'↔'배송')도 매칭으로 인정합니다.\n"
            "2. 기본 점수는 50점입니다. 일치하거나 연관성이 인정된 항목 수에 따라 50점~100점 사이로 점수를 산출하세요.\n"
            "3. 일치 및 연관 인정된 역량을 텍스트 리스트로 정리하세요. (예: ['요리 ↔ 조리 (연관 인정)', '택배 (일치)'])\n\n"
            "반드시 JSON 포맷으로 응답하세요:\n"
            '{"score": 85, "matched_reasons": ["요리 ↔ 조리 (연관 인정)"]}'
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        res = json.loads(response.choices[0].message.content)
        return float(res.get("score", 50)), res.get("matched_reasons", exact_matched)
    except Exception:
        score = min(50 + len(exact_matched) * 25, 100)
        return float(score), exact_matched if exact_matched else ["기본 일치"]

# 모드 선택
st.sidebar.divider()
user_role = st.sidebar.radio(
    "접속 모드 선택", 
    ["🏢 사업주 모드", "👵 구직자 모드", "⚙️ 일자리 추천"]
)

# [1] 사업주 모드: 일자리 등록
if user_role == "🏢 사업주 모드":
    st.header("🏢 사업주 전용 - 일자리 등록")

    with st.form("employer_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("업무명")
            comp_name = st.text_input("사업체(기관)명")
            code_sel = st.selectbox(
                "2026 사업분류코드 선택", 
                list(BUSINESS_CODES.keys()), 
                format_func=lambda x: f"[{x}] {BUSINESS_CODES[x]['name']} ({BUSINESS_CODES[x]['category']})"
            )
            region = st.text_input("지역 (시/군/구)")

        with col2:
            pay = st.number_input("임금 (월/원)", value=0, step=10000)
            hours = st.number_input("근무 시간 (월/시간)", value=0, step=5)
            extra_conds = st.text_input("기타 채용 조건 (우대 키워드, 쉼표 구분)")

        req_w = code_sel in WALKING_CODES
        req_l = code_sel in LITERACY_CODES
        is_h = code_sel in HOURS_CODES

        st.info(f"💡 **기본 채용 조건**: 거동 ({'예' if req_w else '아니오'}) | 기초문해력 ({'예' if req_l else '아니오'}) | 장시간근무 ({'예' if is_h else '아니오'})")

        submit = st.form_submit_button("등록")
        if submit:
            new_job = {
                "id": f"JOB-2026-0{len(st.session_state.db1_jobs) + 1}",
                "company_name": comp_name,
                "title": title,
                "code": code_sel,
                "region_sigungu": region,
                "pay": pay,
                "hours": hours,
                "req_walking": req_w,
                "req_literacy": req_l,
                "is_hours": is_h,
                "extra_conditions": [x.strip() for x in extra_conds.split(",") if x.strip()]
            }
            st.session_state.db1_jobs.append(new_job)
            st.success("일자리가 성공적으로 등록되었습니다.")

    st.subheader("📋 현재 등록된 일자리")
    if st.session_state.db1_jobs:
        st.dataframe(pd.DataFrame(st.session_state.db1_jobs), use_container_width=True)
    else:
        st.write("등록된 일자리가 없습니다.")

# [2] 구직자 모드: 구직자 프로필 저장
elif user_role == "👵 구직자 모드":
    st.header("👵 어르신을 위한 챗봇")

    if not openai_api_key:
        st.warning("⚠️ 사이드바에 OpenAI API Key를 먼저 입력해 주세요.")
    else:
        client = OpenAI(api_key=openai_api_key)

        for msg in st.session_state.chat_history:
            st.chat_message(msg["role"]).write(msg["content"])

        if user_input := st.chat_input("답변을 입력하세요 (예: 나 수원시 살고 옛날에 청소 일 했어. 허리가 좀 아파.)"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.chat_message("user").write(user_input)

            system_prompt = (
                "당신은 어르신을 모시는 따뜻하고 친절한 노인일자리 안내 챗봇입니다. "
                "어르신의 (1)거주 지역, (2)글 읽기/쓰기 여부, (3)거동 가능 여부 및 오래 일하기 가능 여부, "
                "(4)희망 임금 및 시간, (5)과거 직업 경험 및 잘하는 일을 자연스럽게 여쭈어보고 다정하게 호응해 주세요."
            )

            messages = [{"role": "system", "content": system_prompt}] + st.session_state.chat_history
            
            with st.chat_message("assistant"):
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7
                )
                bot_reply = response.choices[0].message.content
                st.write(bot_reply)
                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})

        st.divider()

        if st.button("내 일자리 프로필 저장하기"):
            with st.spinner("대화를 정밀 분석 중입니다..."):
                parse_prompt = (
                    "다음 대화 내역 전체를 분석하여 구직자의 프로필을 JSON 형식으로만 파싱해 주세요.\n"
                    "반드시 JSON 포맷만을 출력해야 합니다. 파악되지 않은 값은 기본값(false 또는 null)을 넣으세요.\n\n"
                    "JSON 키 항목:\n"
                    "- region_sigungu (string: 시/군/구)\n"
                    "- has_literacy (boolean: 읽기/쓰기 가능 여부)\n"
                    "- can_walking (boolean: 거동 가능 여부, 통증/불편 시 false)\n"
                    "- can_hours (boolean: 장시간 근무 가능 여부)\n"
                    "- target_pay (int: 희망 월 임금 숫자만)\n"
                    "- target_hours (int: 희망 월 근무시간 숫자만)\n"
                    "- experiences (list of strings: 과거 경력 키워드)\n\n"
                    f"대화 내역:\n{json.dumps(st.session_state.chat_history, ensure_ascii=False)}"
                )

                parse_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": parse_prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )

                parsed_json = json.loads(parse_response.choices[0].message.content)
                st.session_state.senior_db2 = parsed_json
                st.success("프로필을 성공적으로 저장했습니다.")

        if st.session_state.senior_db2:
            st.subheader("구직자 프로필")
            st.json(st.session_state.senior_db2)

# 맞는 일자리 찾기 
elif user_role == "⚙️ 일자리 추":
    senior = st.session_state.senior_db2
    if not senior:
        st.warning("⚠️ '👵 구직자 모드' 탭에서 프로필을 먼저 저장해 주세요.")
    elif not st.session_state.db1_jobs:
        st.warning("⚠️ '🏢 사업주 모드' 탭에서 일자리를 먼저 등록해 주세요.")
    else:
        # Client 인스턴스 준비
        client = OpenAI(api_key=openai_api_key) if openai_api_key else None

        # [하드필터링]
        passed_jobs = []
        failed_jobs = []

        for j in st.session_state.db1_jobs:
            reasons = []
            if j.get("region_sigungu") != senior.get("region_sigungu"):
                reasons.append(f"지역 불일치 ({j.get('region_sigungu')} ≠ {senior.get('region_sigungu')})")
            if j.get("req_walking") and not senior.get("can_walking", False):
                reasons.append("거동 조건 미달")
            if j.get("req_literacy") and not senior.get("has_literacy", False):
                reasons.append("기초문해력 미달")
            if j.get("is_hours") and not senior.get("can_hours", False):
                reasons.append("장시간근무 미달")
            if j.get("pay", 0) < senior.get("target_pay", 0) * 0.8:
                reasons.append("희망임금 미달")

            if reasons:
                failed_jobs.append((j, reasons))
            else:
                passed_jobs.append(j)

        # [소프트스코어링]
        st.divider()
        scored_list = []

        with st.spinner("실시간 분석 중입니다..."):
            for j in passed_jobs:
                # [기타 채용 조건과의 일치도 점수]
                job_extras = j.get("extra_conditions", [])
                senior_exps = senior.get("experiences", [])
                
                a_index, matched_reasons = calculate_a_index_with_llm(client, senior_exps, job_extras)

                # [이전 유사 고령자의 선호도 점수]
                pref_data = st.session_state.db2_preferences.get(j["id"], {"select_count": 0})
                select_cnt = pref_data["select_count"]
                b_index = min(select_cnt * 10, 100)  

                # 최종 점수 합산 
                if select_cnt == 0:
                    final_score = float(a_index) 
                    weight_info = "a지수 100% (최초)"
                else:
                    final_score = (a_index * 0.6) + (b_index * 0.4)  
                    weight_info = f"a지수({a_index:.1f}점)*0.6 + b지수({b_index}점)*0.4"

                scored_list.append({
                    "job": j,
                    "a_index": a_index,
                    "b_index": b_index,
                    "final_score": final_score,
                    "weight_info": weight_info,
                    "matched": matched_reasons
                })

        # 추천 순위 정렬
        scored_list.sort(key=lambda x: x["final_score"], reverse=True)

        st.subheader("🏆 맘에 드는 일자리 순위")
        
        for rank, item in enumerate(scored_list, 1):
            j = item["job"]
            with st.expander(f"✨ [{rank}위] {j['title']} (최종 점수: {item['final_score']:.1f}점)", expanded=True):
                st.write(f"- **사업체명**: {j['company_name']} | **사업코드**: `{j['code']}`")
                st.write(f"- **a지수 (LLM 역량 의미일치도)**: **{item['a_index']:.1f}점** (매칭 판단: `{', '.join(item['matched'])}`)")
                st.write(f"- **b지수 (유사 구직자 선호도)**: **{item['b_index']}점** (산출 방식: {item['weight_info']})")
                
                # 어르신이 맘에 드는 일자리 선택 버튼 
                if st.button(f"👍 이 일자리 마음에 듭니다/지원하기 (JOB: {j['id']})", key=j['id']):
                    if j['id'] not in st.session_state.db2_preferences:
                        st.session_state.db2_preferences[j['id']] = {
                            "exp_tags": senior.get("experiences", []), 
                            "select_count": 1
                        }
                    else:
                        st.session_state.db2_preferences[j['id']]["select_count"] += 1
                    
                    st.success("✅ 선택 내역이 반영되었습니다!")
