import streamlit as st
import os
import json
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# 환경 변수 로드
load_dotenv()

# Pinecone 설정
PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
PINECONE_ENVIRONMENT = st.secrets("PINECONE_ENVIRONMENT", "us-east-1")


# 인덱스 이름 설정
PRODUCTS_INDEX_NAME = "sivillage-products"
BRANDS_INDEX_NAME = "sivillage-brands"

# Pinecone 클라이언트 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)

# OpenAI 임베딩 및 LLM 모델 초기화
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(temperature=0.2, model="gpt-4o")

def search_products(query, top_k=5):
    """상품 DB에서 상품을 검색합니다."""
    try:
        # 임베딩 생성
        query_embedding = embeddings.embed_query(query)
        
        # 인덱스 가져오기
        index = pc.Index(PRODUCTS_INDEX_NAME)
        
        # 검색 실행
        results = index.query(
            vector=query_embedding,
            top_k=top_k * 3,  # 더 많은 결과를 가져와서 필터링
            include_metadata=True
        )
        
        # 결과 처리 및 필터링
        search_results = []
        
        # 쿼리에서 키워드 추출
        keywords = query.lower().split()
        
        for item in results.matches:
            if hasattr(item, 'metadata'):
                # 메타데이터에서 필요한 정보 추출
                product_name = item.metadata.get('product_name', '').lower()
                brand = item.metadata.get('brand', '').lower()
                description = item.metadata.get('description', '').lower()
                
                # 키워드 매칭 점수 계산
                keyword_match_score = 0
                for keyword in keywords:
                    if keyword in product_name:
                        keyword_match_score += 5  # 제품명에 키워드가 있으면 가중치 높게
                    if keyword in brand:
                        keyword_match_score += 3  # 브랜드에 키워드가 있으면 중간 가중치
                    if keyword in description:
                        keyword_match_score += 1  # 설명에 키워드가 있으면 낮은 가중치
                
                # 검색 가중치 가져오기 (기본값 1.0)
                search_weight = float(item.metadata.get('search_weight', 1.0))
                
                # 검색 가중치 적용
                keyword_match_score *= search_weight
                
                # 결합 점수 계산 (벡터 유사도 + 키워드 매칭)
                vector_score = item.score * search_weight
                combined_score = vector_score + (keyword_match_score * 0.1)
                
                search_results.append({
                    'id': item.id,
                    'score': combined_score,
                    'vector_score': vector_score,
                    'keyword_score': keyword_match_score,
                    'metadata': item.metadata
                })
        
        # 결합 점수로 정렬
        search_results.sort(key=lambda x: x['score'], reverse=True)
        
        # 상위 결과만 반환
        return search_results[:top_k]
    
    except Exception as e:
        print(f"상품 검색 중 오류가 발생했습니다: {str(e)}")
        return []

def search_brands(query, top_k=5):
    """브랜드 DB에서 브랜드를 검색합니다."""
    try:
        # 임베딩 생성
        query_embedding = embeddings.embed_query(query)
        
        # 인덱스 가져오기
        index = pc.Index(BRANDS_INDEX_NAME)
        
        # 검색 실행
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # 결과 처리
        search_results = []
        for item in results.matches:
            if hasattr(item, 'metadata'):
                search_results.append({
                    'id': item.id,
                    'score': item.score,
                    'metadata': item.metadata
                })
        
        return search_results
    
    except Exception as e:
        print(f"브랜드 검색 중 오류가 발생했습니다: {str(e)}")
        return []

def get_similar_brands(brand_name, top_k=3):
    """특정 브랜드와 유사한 브랜드를 찾습니다."""
    try:
        # 브랜드 검색
        query = f"{brand_name} 브랜드"
        brand_results = search_brands(query, top_k=1)
        
        if not brand_results:
            return []
        
        # 첫 번째 결과의 브랜드 정보 가져오기
        brand_info = brand_results[0]['metadata']
        
        # 유사 브랜드 정보 가져오기
        similar_brands = []
        
        # 1. 경쟁 브랜드 정보 활용
        if 'competing_brands' in brand_info and brand_info['competing_brands'] != 'Unknown':
            competing_brands = [brand.strip() for brand in brand_info['competing_brands'].split(',')]
            similar_brands.extend(competing_brands)
        
        # 2. 같은 카테고리, 비슷한 가격대의 브랜드 검색
        if 'main_category' in brand_info and 'sub_category' in brand_info and 'price_range' in brand_info:
            category_query = f"{brand_info['main_category']} {brand_info['sub_category']} {brand_info['price_range']}"
            category_results = search_brands(category_query, top_k=top_k+2)
            
            # 원래 브랜드를 제외한 결과 추가
            for result in category_results:
                result_brand_name = result['metadata'].get('brand_name_en', '')
                if result_brand_name and result_brand_name != brand_name and result_brand_name not in similar_brands:
                    similar_brands.append(result_brand_name)
        
        # 최대 top_k개 반환
        return similar_brands[:top_k]
    
    except Exception as e:
        print(f"유사 브랜드 검색 중 오류가 발생했습니다: {str(e)}")
        return []

def enrich_product_results_with_brand_info(product_results):
    """상품 검색 결과에 브랜드 정보를 추가합니다."""
    enriched_results = []
    
    for product in product_results:
        # 상품 정보 복사
        enriched_product = product.copy()
        
        # 브랜드 이름 가져오기
        brand_name = product['metadata'].get('brand', '')
        
        if brand_name:
            # 브랜드 정보 검색
            brand_results = search_brands(brand_name, top_k=1)
            
            if brand_results:
                # 브랜드 정보 추가
                enriched_product['brand_info'] = brand_results[0]['metadata']
            else:
                enriched_product['brand_info'] = {'brand_name_en': brand_name}
        
        enriched_results.append(enriched_product)
    
    return enriched_results

def is_brand_centric_query(query):
    """쿼리가 브랜드 중심인지 확인합니다."""
    # 브랜드 중심 쿼리 패턴
    brand_centric_patterns = [
        "와 비슷한", "와 같은", "와 유사한", "스타일의", "같은 스타일", 
        "like", "similar to", "same as", "style of", "similar brand"
    ]
    
    # 패턴 확인
    for pattern in brand_centric_patterns:
        if pattern in query.lower():
            return True
    
    return False

def extract_brand_from_query(query):
    """쿼리에서 브랜드 이름을 추출합니다."""
    # LLM을 사용하여 브랜드 이름 추출
    prompt = ChatPromptTemplate.from_template(
        """다음 쿼리에서 브랜드 이름을 추출해주세요. 브랜드 이름만 반환하세요.
        
        쿼리: {query}
        
        브랜드 이름:"""
    )
    
    messages = prompt.format_messages(query=query)
    response = llm.invoke(messages)
    
    # 응답에서 브랜드 이름 추출
    brand_name = response.content.strip()
    
    return brand_name

def hybrid_search(query, top_k=5):
    """하이브리드 검색을 수행합니다."""
    # 브랜드 중심 쿼리인지 확인
    if is_brand_centric_query(query):
        # 브랜드 이름 추출
        brand_name = extract_brand_from_query(query)
        
        if brand_name:
            print(f"브랜드 중심 쿼리 감지: '{brand_name}'와(과) 유사한 브랜드 검색")
            
            # 유사 브랜드 검색
            similar_brands = get_similar_brands(brand_name, top_k=3)
            
            if similar_brands:
                # 유사 브랜드의 상품 검색
                all_results = []
                
                # 원래 브랜드 포함
                all_brands = [brand_name] + similar_brands
                
                # 쿼리에서 브랜드 관련 부분 제외
                product_type = query.replace(brand_name, "").replace("와 비슷한", "").replace("와 같은", "").replace("와 유사한", "").replace("스타일의", "").replace("같은 스타일", "").strip()
                
                if not product_type:
                    product_type = "제품"  # 기본값
                
                # 각 브랜드별로 검색
                for brand in all_brands:
                    brand_query = f"{brand} {product_type}"
                    results = search_products(brand_query, top_k=2)  # 각 브랜드당 2개씩
                    
                    for result in results:
                        result['query_brand'] = brand
                        all_results.append(result)
                
                # 점수로 정렬
                all_results.sort(key=lambda x: x['score'], reverse=True)
                
                # 브랜드 정보 추가
                enriched_results = enrich_product_results_with_brand_info(all_results[:top_k])
                
                return {
                    'query_type': 'brand_centric',
                    'original_brand': brand_name,
                    'similar_brands': similar_brands,
                    'results': enriched_results
                }
    
    # 일반 검색
    # 1단계: 상품 DB 검색
    product_results = search_products(query, top_k=top_k)
    
    # 2단계: 브랜드 정보로 결과 보강
    enriched_results = enrich_product_results_with_brand_info(product_results)
    
    return {
        'query_type': 'general',
        'results': enriched_results
    }

def print_search_results(search_results):
    """검색 결과를 출력합니다."""
    query_type = search_results['query_type']
    
    if query_type == 'brand_centric':
        print(f"\n원래 브랜드: {search_results['original_brand']}")
        print(f"유사 브랜드: {', '.join(search_results['similar_brands'])}")
    
    results = search_results['results']
    print(f"\n검색 결과: {len(results)}개")
    
    for i, result in enumerate(results):
        product_name = result['metadata'].get('product_name', 'Unknown Product')
        brand = result['metadata'].get('brand', 'Unknown Brand')
        price = result['metadata'].get('price', 'N/A')
        
        print(f"\n{i+1}. {product_name}")
        print(f"   브랜드: {brand}")
        print(f"   가격: {price}")
        print(f"   점수: {result['score']:.4f} (벡터: {result['vector_score']:.4f}, 키워드: {result['keyword_score']:.2f})")
        
        # 브랜드 중심 쿼리인 경우 쿼리 브랜드 표시
        if query_type == 'brand_centric' and 'query_brand' in result:
            print(f"   쿼리 브랜드: {result['query_brand']}")
        
        # 브랜드 정보 출력
        if 'brand_info' in result:
            brand_info = result['brand_info']
            
            # 브랜드 기본 정보
            brand_name_en = brand_info.get('brand_name_en', brand)
            brand_name_ko = brand_info.get('brand_name_ko', 'N/A')
            country = brand_info.get('country_of_origin', 'N/A')
            
            print(f"   브랜드 정보: {brand_name_en} ({brand_name_ko}), 원산지: {country}")
            
            # 브랜드 카테고리
            main_category = brand_info.get('main_category', 'N/A')
            sub_category = brand_info.get('sub_category', 'N/A')
            
            print(f"   카테고리: {main_category} > {sub_category}")
            
            # 브랜드 설명
            description = brand_info.get('brand_description', 'N/A')
            if description != 'N/A':
                print(f"   설명: {description}")
            
            # 타겟 고객층
            target = brand_info.get('target_customers', 'N/A')
            if target != 'N/A':
                print(f"   타겟 고객층: {target}")
            
            # 가격대
            price_range = brand_info.get('price_range', 'N/A')
            if price_range != 'N/A':
                print(f"   가격대: {price_range}")

def main():
    """메인 함수"""
    print("하이브리드 검색 테스트를 시작합니다...")
    
    # 테스트 쿼리
    test_queries = [
        "여성용 가죽 가방",
        "발렌시아가와 비슷한 브랜드의 가방",
        "나이키와 같은 스타일의 운동화",
        "프랑스 럭셔리 브랜드 지갑",
        "20대 여성을 위한 캐주얼 의류"
    ]
    
    for query in test_queries:
        print(f"\n\n===== 검색어: '{query}' =====")
        search_results = hybrid_search(query)
        print_search_results(search_results)

if __name__ == "__main__":
    main() 