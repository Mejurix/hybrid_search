import streamlit as st
import os
import re
from dotenv import load_dotenv
from hybrid_search import hybrid_search, print_search_results
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hybrid_search import hybrid_search, print_search_results


# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="S.I.Village: Brand Agent 검색 시스템",
    page_icon="🔍",
    layout="wide"
)

# CSS 스타일 추가
st.markdown("""
<style>
    .search-type-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
        border-left: 5px solid #4e8df5;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .search-type-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .search-type-title {
        color: #1e3a8a;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .search-example {
        background-color: #e6f3ff;
        border-radius: 5px;
        padding: 5px 10px;
        margin: 5px 0;
        display: inline-block;
        font-size: 0.9rem;
        cursor: pointer;
        border: 1px solid #c0d8f0;
    }
    .search-example:hover {
        background-color: #c0d8f0;
    }
    .main-search-box {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .search-button {
        background-color: #4e8df5;
        color: white;
        border-radius: 5px;
        padding: 5px 15px;
        font-weight: bold;
    }
    .sidebar-category {
        font-weight: bold;
        color: #1e3a8a;
        margin-top: 15px;
    }
    .sidebar-subcategory {
        font-weight: bold;
        color: #4a5568;
        margin-top: 10px;
        margin-bottom: 5px;
    }
    .sidebar-query {
        background-color: #e6f3ff;
        border-radius: 5px;
        padding: 5px 10px;
        margin: 3px 0;
        font-size: 0.9rem;
        cursor: pointer;
        border: 1px solid #c0d8f0;
        display: block;
        width: 100%;
        text-align: left;
    }
    .sidebar-query:hover {
        background-color: #c0d8f0;
    }
    .result-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .brand-centric-banner {
        background-color: #fdf6e3;
        border-left: 5px solid #f59e0b;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 5px;
    }
    .general-search-banner {
        background-color: #e6f3ff;
        border-left: 5px solid #3b82f6;
        padding: 10px 15px;
        margin-bottom: 15px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# 제목 및 소개
st.title("🔍 S.I.Village: Brand Agent 검색 시스템")
st.markdown("""
이 검색 시스템은 S.I.Village의 AI 퍼스널 쇼퍼를 위한 브랜드 에이전트 지원용 고급 검색 엔진입니다.
주요 제품 및 브랜드 정보를 벡터화하여 고성능 데이터 스토어에 저장하고, 나이, 유사 상품, 브랜드 유사성, 스타일 등 다양한 요소를 고려한 정교한 검색 기능을 제공합니다.
이를 통해 고객에게 개인 맞춤형 추천 경험을 제공하며, AI 기반 쇼핑 경험을 한층 더 향상시킵니다.
""")

# 샘플 쿼리 파일에서 쿼리 로드
def load_sample_queries():
    queries_by_category = {}
    current_category = None
    current_subcategory = None
    
    try:
        with open('sample_queries.md', 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
            for line in lines:
                line = line.strip()
                
                # 대분류 (##로 시작)
                if line.startswith('## '):
                    current_category = line[3:]
                    queries_by_category[current_category] = {}
                    current_subcategory = None
                
                # 소분류 (###로 시작)
                elif line.startswith('### '):
                    if current_category:
                        current_subcategory = line[4:]
                        queries_by_category[current_category][current_subcategory] = []
                
                # 쿼리 항목 (-로 시작)
                elif line.startswith('- ') and current_category and current_subcategory:
                    query = line[2:]
                    queries_by_category[current_category][current_subcategory].append(query)
    
    except FileNotFoundError:
        st.sidebar.warning("sample_queries.md 파일을 찾을 수 없습니다.")
        return {}
    
    return queries_by_category

# 세션 상태 초기화
if 'query' not in st.session_state:
    st.session_state.query = ""
if 'run_search' not in st.session_state:
    st.session_state.run_search = False
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "검색"

# 메인 화면에 검색 유형 카드 표시 (검색 탭이 활성화된 경우에만)
if st.session_state.active_tab == "검색" and not ((st.session_state.run_search or 'search_button_clicked' in st.session_state) and st.session_state.query):
    # 검색 유형 설명 카드
    st.markdown("## 다양한 검색 유형")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">🔎 일반 제품 검색</div>
            <p>원하는 제품을 직접 검색합니다. 제품명, 속성, 카테고리 등을 포함할 수 있습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("여성용 가죽 가방", key="main_example_1"):
                st.session_state.query = "여성용 가죽 가방"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("고급 손목시계", key="main_example_2"):
                st.session_state.query = "고급 손목시계"
                st.session_state.run_search = True
                st.rerun()
        
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">🌍 지역 기반 검색</div>
            <p>특정 국가나 지역의 브랜드 또는 제품을 검색합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("프랑스 럭셔리 브랜드 제품", key="main_example_3"):
                st.session_state.query = "프랑스 럭셔리 브랜드 제품"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("이탈리아 가죽 제품", key="main_example_4"):
                st.session_state.query = "이탈리아 가죽 제품"
                st.session_state.run_search = True
                st.rerun()
        
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">💰 가격대 검색</div>
            <p>특정 가격대의 제품을 검색합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("고가 럭셔리 시계", key="main_example_5"):
                st.session_state.query = "고가 럭셔리 시계"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("합리적인 가격의 아동복", key="main_example_6"):
                st.session_state.query = "합리적인 가격의 아동복"
                st.session_state.run_search = True
                st.rerun()
    
    with col2:
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">👗 브랜드 유사성 검색</div>
            <p>특정 브랜드와 유사한 스타일의 제품을 검색합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("발렌시아가와 비슷한 브랜드의 가방", key="main_example_7"):
                st.session_state.query = "발렌시아가와 비슷한 브랜드의 가방"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("구찌와 같은 스타일의 지갑", key="main_example_8"):
                st.session_state.query = "구찌와 같은 스타일의 지갑"
                st.session_state.run_search = True
                st.rerun()
        
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">👨‍👩‍👧‍👦 인구통계학적 검색</div>
            <p>특정 연령대, 성별, 라이프스타일에 맞는 제품을 검색합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("20대 여성을 위한 캐주얼 의류", key="main_example_9"):
                st.session_state.query = "20대 여성을 위한 캐주얼 의류"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("직장인을 위한 오피스 룩", key="main_example_10"):
                st.session_state.query = "직장인을 위한 오피스 룩"
                st.session_state.run_search = True
                st.rerun()
        
        st.markdown("""
        <div class="search-type-card">
            <div class="search-type-title">🎨 스타일 검색</div>
            <p>특정 디자인 스타일이나 시즌에 맞는 제품을 검색합니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        example_col1, example_col2 = st.columns(2)
        with example_col1:
            if st.button("미니멀 디자인 홈 인테리어", key="main_example_11"):
                st.session_state.query = "미니멀 디자인 홈 인테리어"
                st.session_state.run_search = True
                st.rerun()
        with example_col2:
            if st.button("여름 리조트 룩", key="main_example_12"):
                st.session_state.query = "여름 리조트 룩"
                st.session_state.run_search = True
                st.rerun()

# 메인 검색 박스
st.markdown("<div class='main-search-box'>", unsafe_allow_html=True)
st.subheader("🔍 검색어 입력")

# 검색 입력 필드
query = st.text_input(label="검색어", value=st.session_state.query, placeholder="예: 여성용 가죽 가방, 발렌시아가와 비슷한 브랜드의 가방", key="search_input")

# 검색 버튼 클릭 시 세션 상태 업데이트
search_button = st.button("검색", key="main_search_button")
if search_button:
    st.session_state.query = query  # 현재 입력된 검색어로 세션 상태 업데이트
    st.session_state.run_search = True
    st.session_state.search_button_clicked = True

st.markdown("</div>", unsafe_allow_html=True)

# 사이드바 - 검색 예시
with st.sidebar:
    st.header("💡 검색 예시")
    
    # 샘플 쿼리 로드
    sample_queries = load_sample_queries()
    
    if sample_queries:
        # 카테고리별 아코디언 생성
        for category, subcategories in sample_queries.items():
            st.markdown(f"<div class='sidebar-category'>{category}</div>", unsafe_allow_html=True)
            
            for subcategory, queries in subcategories.items():
                with st.expander(subcategory):
                    for query in queries:
                        if st.button(query, key=f"{category}_{subcategory}_{query}", use_container_width=True):
                            # 세션 상태 초기화 후 새 쿼리 설정
                            st.session_state.query = query
                            st.session_state.run_search = True
                            st.rerun()
    else:
        # 기본 예시 쿼리 (파일이 없는 경우)
        st.markdown("""
        ### 일반 제품 검색
        - 여성용 가죽 가방
        - 남성 캐주얼 셔츠
        - 고급 손목시계
        
        ### 브랜드 유사성 검색
        - 발렌시아가와 비슷한 브랜드의 가방
        - 구찌와 같은 스타일의 지갑
        - 나이키와 유사한 운동화
        """)

# 결과 표시
if (search_button or st.session_state.run_search) and st.session_state.query:
    # 현재 검색어 저장
    current_query = st.session_state.query
    
    # 탭을 검색 결과로 변경
    st.session_state.active_tab = "검색 결과"
    
    with st.spinner("검색 중..."):
        search_results = hybrid_search(current_query)
    
    # 세션 상태 초기화 (run_search만 초기화하고 query는 유지)
    st.session_state.run_search = False
    
    # 검색 쿼리 표시
    st.markdown(f"## 검색어: \"{current_query}\"")
    
    # 검색 유형 표시
    if search_results['query_type'] == 'brand_centric':
        st.markdown(f"""
        <div class="brand-centric-banner">
            <h3>👗 브랜드 중심 검색</h3>
            <p>'{search_results['original_brand']}'와(과) 유사한 브랜드를 검색했습니다.</p>
            <p><strong>유사 브랜드:</strong> {', '.join(search_results['similar_brands'])}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="general-search-banner">
            <h3>🔎 일반 검색</h3>
            <p>일반 검색 쿼리로 제품을 검색했습니다.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 결과 개수
    st.markdown(f"### 검색 결과: {len(search_results['results'])}개")
    
    # 결과 표시
    for i, result in enumerate(search_results['results']):
        st.markdown(f"<div class='result-card'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        
        # 제품 이미지 (이미지 URL이 있는 경우)
        with col1:
            image_url = result['metadata'].get('image_url', '')
            if image_url:
                st.image(image_url, width=200)
            else:
                st.image("https://via.placeholder.com/200?text=No+Image", width=200)
        
        # 제품 정보
        with col2:
            product_name = result['metadata'].get('product_name', 'Unknown Product')
            brand = result['metadata'].get('brand', 'Unknown Brand')
            price = result['metadata'].get('price', 'N/A')
            product_url = result['metadata'].get('product_url', '')
            
            st.markdown(f"### {i+1}. {product_name}")
            st.markdown(f"**브랜드:** {brand}")
            st.markdown(f"**가격:** {price}")
            
            # 점수 정보
            st.markdown(f"""
            <div style="background-color: #f0f9ff; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <strong>관련성 점수:</strong> {result['score']:.4f}
                <div style="display: flex; margin-top: 5px;">
                    <div style="flex: 1; padding-right: 10px;">
                        <div style="font-size: 0.9rem;"><strong>벡터 유사도:</strong> {result['vector_score']:.4f}</div>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-size: 0.9rem;"><strong>키워드 매칭:</strong> {result['keyword_score']:.2f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 브랜드 중심 쿼리인 경우 쿼리 브랜드 표시
            if search_results['query_type'] == 'brand_centric' and 'query_brand' in result:
                st.markdown(f"""
                <div style="background-color: #fff7ed; padding: 10px; border-radius: 5px; margin-top: 10px;">
                    <strong>쿼리 브랜드:</strong> {result['query_brand']}
                </div>
                """, unsafe_allow_html=True)
            
            # 제품 URL이 있는 경우 링크 제공
            if product_url:
                st.markdown(f"[제품 상세 페이지 보기]({product_url})")
        
        # 브랜드 정보 확장 섹션
        if 'brand_info' in result:
            with st.expander("브랜드 정보 더 보기"):
                brand_info = result['brand_info']
                
                # 브랜드 기본 정보
                brand_name_en = brand_info.get('brand_name_en', brand)
                brand_name_ko = brand_info.get('brand_name_ko', 'N/A')
                country = brand_info.get('country_of_origin', 'N/A')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**브랜드:** {brand_name_en} ({brand_name_ko})")
                    st.markdown(f"**원산지:** {country}")
                
                with col2:
                    # 브랜드 카테고리
                    main_category = brand_info.get('main_category', 'N/A')
                    sub_category = brand_info.get('sub_category', 'N/A')
                    
                    st.markdown(f"**카테고리:** {main_category} > {sub_category}")
                    
                    # 가격대
                    price_range = brand_info.get('price_range', 'N/A')
                    if price_range != 'N/A':
                        st.markdown(f"**가격대:** {price_range}")
                
                # 브랜드 설명
                description = brand_info.get('brand_description', 'N/A')
                if description != 'N/A':
                    st.markdown("**설명:**")
                    st.markdown(f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>{description}</div>", unsafe_allow_html=True)
                
                # 타겟 고객층
                target = brand_info.get('target_customers', 'N/A')
                if target != 'N/A':
                    st.markdown("**타겟 고객층:**")
                    st.markdown(f"<div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>{target}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# 푸터
st.markdown("---")
st.markdown("© 2025 Super Shopping Agent") 