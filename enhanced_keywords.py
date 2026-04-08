#!/usr/bin/env python3
"""Enhanced keyword analysis with detailed categorization and compound keyword detection."""
import re
from collections import Counter, defaultdict

# 세분화된 키워드 카테고리 트리
KEYWORD_CATEGORIES = {
    "부동산": {
        "투자전략": {
            "갭투자": ["갭투자", "갭투기", "갭 투자", "gap투자", "깡통전세"],
            "영끌": ["영끌", "영혼까지 끌어", "영혼끌어", "대출최대"],
            "패닉바잉": ["패닉바잉", "공포매수", "급매수", "몰림현상"],
            "패닉셀링": ["패닉셀링", "급매", "공포매도", "떨이매도"],
            "레버리지": ["레버리지", "차입매수", "대출투자"],
            "매물갑": ["매물갑", "매물부족", "물건부족"],
            "하락장투자": ["바닥매수", "존버", "물타기", "평단가"]
        },
        "거래유형": {
            "매매": ["매매", "거래", "매수", "매도", "구입", "처분"],
            "전세": ["전세", "전셋값", "전세금", "전세보증금", "전세계약"],
            "월세": ["월세", "월세전환", "반전세", "단기임대"],
            "분양": ["분양", "1차분양", "2차분양", "분양가상한제"],
            "임대사업": ["임대사업", "임대수익", "임대료", "월세수익"]
        },
        "사기/리스크": {
            "전세사기": ["전세사기", "깡통전세", "역전세", "전세피해", "전세보증"],
            "분양사기": ["분양사기", "미분양", "허위분양", "분양취소"],
            "부동산사기": ["부동산사기", "중개사기", "가격조작"],
            "경매리스크": ["경매", "공매", "법정관리", "워크아웃"],
            "깡통전세": ["깡통전세", "역전세", "보증금위험"]
        },
        "정책/제도": {
            "대출규제": ["LTV", "DTI", "DSR", "대출한도", "대출규제"],
            "청약제도": ["청약", "청약당첨", "청약통장", "특별공급", "일반공급"],
            "세금제도": ["양도세", "종부세", "취득세", "재산세", "증여세", "상속세"],
            "주택정책": ["주택공급", "신도시", "공공주택", "임대주택", "보금자리"],
            "규제정책": ["투기지역", "투기과열지구", "조정대상지역", "분양가상한제"]
        },
        "지역별": {
            "강남3구": ["강남", "서초", "송파", "압구정", "청담", "역삼", "도곡"],
            "마용성": ["마포", "용산", "성동", "한남동", "이태원", "성수"],
            "분당판교": ["분당", "판교", "수지", "동천", "정자", "서현"],
            "일산": ["일산", "파주", "김포", "고양", "일산동구", "일산서구"],
            "동탄광교": ["동탄", "광교", "영통", "수원", "화성"],
            "신도시": ["위례", "하남", "검단", "계양", "부천"],
            "지방": ["부산", "대구", "광주", "대전", "울산", "세종"],
            "해외": ["해외부동산", "미국부동산", "일본부동산", "동남아"]
        },
        "주거유형": {
            "아파트": ["아파트", "APT", "단지", "동", "세대"],
            "오피스텔": ["오피스텔", "원룸", "투룸", "쓰리룸"],
            "빌라연립": ["빌라", "연립", "다세대", "다가구"],
            "단독주택": ["단독주택", "전원주택", "농가주택", "한옥"],
            "상업용": ["상가", "사무실", "점포", "건물", "빌딩"],
            "특수용도": ["펜션", "게스트하우스", "숙박업", "카페건물"]
        }
    },
    
    "경제/투자": {
        "주식투자": {
            "대장주": ["삼성전자", "SK하이닉스", "TSMC", "엔비디아"],
            "테마주": ["AI주", "배터리주", "2차전지", "K뷰티", "바이오"],
            "ETF": ["ETF", "인덱스", "QQQ", "SPY", "KODEX"],
            "공매도": ["공매도", "숏", "베어", "풋옵션"],
            "동학개미": ["개미", "동학개미", "개인투자자", "서학개미"]
        },
        "거시경제": {
            "금리": ["금리", "기준금리", "금통위", "연준", "FOMC", "파월"],
            "인플레이션": ["인플레", "인플레이션", "물가", "CPI", "PPI"],
            "환율": ["달러", "원달러", "엔화", "위안", "유로"],
            "유가": ["유가", "WTI", "두바이유", "원유", "브렌트유"],
            "금": ["금값", "금시세", "골드", "금투자"],
            "채권": ["국채", "회사채", "채권금리", "국고채", "장기채"]
        },
        "암호화폐": {
            "비트코인": ["비트코인", "BTC", "코인", "가상화폐", "암호화폐"],
            "알트코인": ["이더리움", "ETH", "리플", "도지코인", "알트"],
            "거래소": ["업비트", "빗썸", "코인베이스", "바이낸스"],
            "NFT": ["NFT", "메타버스", "디지털자산"],
            "규제": ["코인규제", "가상자산법", "거래소폐쇄"]
        }
    },
    
    "라이프스타일": {
        "재테크": {
            "예적금": ["적금", "예금", "정기예금", "CMA", "MMF"],
            "보험": ["보험", "변액보험", "연금보험", "실손보험"],
            "연금": ["연금", "국민연금", "퇴직연금", "개인연금", "IRP"],
            "절세": ["절세", "세테크", "ISA", "연말정산", "소득공제"]
        },
        "소비패턴": {
            "명품": ["명품", "럭셔리", "브랜드", "한정판"],
            "부의상징": ["로렉스", "람보르기니", "펜트하우스", "요트"],
            "가성비": ["가성비", "가심비", "알뜰소비", "할인"]
        }
    }
}

# 복합 키워드 패턴 (정규식)
COMPOUND_PATTERNS = {
    # 수치 포함 키워드
    "DTI규제": [r"DTI\s*\d+", r"DTI.*규제", r"DTI.*한도"],
    "LTV규제": [r"LTV\s*\d+", r"LTV.*규제", r"LTV.*한도"],
    "금리상승": [r"\d+\.?\d*%.*금리", r"금리.*\d+\.?\d*%", r"기준금리.*인상"],
    "집값상승": [r"집값.*\d+", r"\d+.*집값", r"부동산.*상승"],
    
    # 시간 표현 포함
    "올해부동산": [r"2026.*부동산", r"올해.*부동산", r"내년.*부동산"],
    "최근전세": [r"최근.*전세", r"요즘.*전세", r"현재.*전세"],
    
    # 감정 표현 포함
    "부동산공포": [r"부동산.*공포", r"부동산.*패닉", r"부동산.*불안"],
    "투자기회": [r"투자.*기회", r"매수.*타이밍", r"저점.*매수"],
    
    # 액션 키워드
    "급매물": [r"급매", r"급매물", r"급매매"],
    "물량폭탄": [r"물량.*폭탄", r"대량.*매물", r"공급.*폭탄"]
}

class EnhancedKeywordAnalyzer:
    def __init__(self):
        self.flat_keywords = self._flatten_keywords()
        self.category_map = self._build_category_map()
    
    def _flatten_keywords(self):
        """키워드 트리를 평면화"""
        flat = []
        def traverse(node, path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    traverse(value, f"{path}/{key}" if path else key)
            elif isinstance(node, list):
                for keyword in node:
                    flat.append((keyword, path))
        
        traverse(KEYWORD_CATEGORIES)
        return flat
    
    def _build_category_map(self):
        """키워드 → 카테고리 매핑"""
        mapping = {}
        for keyword, category_path in self.flat_keywords:
            mapping[keyword.lower()] = category_path
        return mapping
    
    def extract_compound_keywords(self, text):
        """복합 키워드 추출"""
        found_compounds = []
        
        for compound_name, patterns in COMPOUND_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    found_compounds.extend([(compound_name, match) for match in matches])
        
        return found_compounds
    
    def extract_enhanced_keywords(self, title):
        """향상된 키워드 추출"""
        # 기본 전처리
        cleaned = re.sub(r'[^\w가-힣\s%]', ' ', title)
        words = cleaned.split()
        
        # 1. 복합 키워드 추출
        compound_keywords = self.extract_compound_keywords(title)
        
        # 2. 단일 키워드 추출 및 카테고리 매핑
        categorized_keywords = defaultdict(list)
        simple_keywords = []
        
        for word in words:
            word = word.strip().lower()
            if len(word) < 2:
                continue
            
            # 카테고리 매핑 확인
            if word in self.category_map:
                category = self.category_map[word]
                categorized_keywords[category].append(word)
            else:
                # 부분 매칭 시도
                for keyword, category in self.category_map.items():
                    if keyword in word or word in keyword:
                        categorized_keywords[category].append(word)
                        break
                else:
                    simple_keywords.append(word)
        
        return {
            'compound_keywords': compound_keywords,
            'categorized_keywords': dict(categorized_keywords),
            'simple_keywords': simple_keywords,
            'total_keywords': len(compound_keywords) + sum(len(v) for v in categorized_keywords.values()) + len(simple_keywords)
        }
    
    def analyze_keyword_trends(self, video_list, period_days=7):
        """키워드 트렌드 분석"""
        # 카테고리별 키워드 수집
        category_stats = defaultdict(lambda: defaultdict(int))
        compound_stats = Counter()
        
        for video in video_list:
            extracted = self.extract_enhanced_keywords(video['title'])
            
            # 복합 키워드 집계
            for compound_name, matched_text in extracted['compound_keywords']:
                compound_stats[compound_name] += 1
            
            # 카테고리별 키워드 집계
            for category, keywords in extracted['categorized_keywords'].items():
                for keyword in keywords:
                    category_stats[category][keyword] += 1
        
        # 트렌드 점수 계산
        trending_analysis = self._calculate_trend_scores(category_stats, compound_stats)
        
        return {
            'period_days': period_days,
            'category_stats': dict(category_stats),
            'compound_stats': dict(compound_stats),
            'trending_analysis': trending_analysis,
            'total_categories': len(category_stats),
            'total_compounds': len(compound_stats)
        }
    
    def _calculate_trend_scores(self, category_stats, compound_stats):
        """트렌드 점수 계산"""
        trending_items = []
        
        # 복합 키워드 점수화
        for compound, count in compound_stats.most_common(20):
            score = count * 2.0  # 복합 키워드는 가중치 2배
            urgency = "🔴긴급" if score > 10 else "🟡중요" if score > 5 else "🟢일반"
            
            trending_items.append({
                'type': 'compound',
                'keyword': compound,
                'count': count,
                'score': score,
                'urgency': urgency,
                'category': 'compound_keyword'
            })
        
        # 카테고리별 상위 키워드
        for category, keywords in category_stats.items():
            for keyword, count in Counter(keywords).most_common(5):
                score = count * 1.0  # 기본 가중치
                
                # 카테고리별 가중치 조정
                if 'saegi' in category or '사기' in category:
                    score *= 3.0  # 사기 관련은 3배 가중치
                elif 'policy' in category or '정책' in category:
                    score *= 2.5  # 정책 관련은 2.5배
                elif 'investment' in category or '투자' in category:
                    score *= 2.0  # 투자 관련은 2배
                
                urgency = "🔴긴급" if score > 15 else "🟡중요" if score > 8 else "🟢일반"
                
                trending_items.append({
                    'type': 'categorized',
                    'keyword': keyword,
                    'count': count,
                    'score': score,
                    'urgency': urgency,
                    'category': category
                })
        
        # 점수 순으로 정렬
        trending_items.sort(key=lambda x: x['score'], reverse=True)
        
        return trending_items[:30]  # 상위 30개만 반환

def test_enhanced_analysis():
    """테스트 실행"""
    analyzer = EnhancedKeywordAnalyzer()
    
    # 테스트 영상 제목들
    test_titles = [
        "[긴급] DTI 40% 규제 확정! 갭투자 이제 끝?",
        "전세사기 예방법... HUG 보증 필수 체크사항",
        "2026년 집값 전망, 금리 인상으로 폭락 시작?",
        "강남 아파트 급매물 폭탄! 패닉셀링 시작됐나",
        "청약당첨 후 중도금 대출 거절... 이럴 때 대처법",
        "비트코인 6만 달러 돌파! 올해 10만 달러 가능?",
        "영끌족들 위험신호... LTV 50% 하향 예정"
    ]
    
    print("=== 향상된 키워드 분석 테스트 ===")
    for title in test_titles:
        result = analyzer.extract_enhanced_keywords(title)
        print(f"\n제목: {title}")
        print(f"복합키워드: {result['compound_keywords']}")
        print(f"카테고리별: {result['categorized_keywords']}")
        print(f"기타키워드: {result['simple_keywords'][:5]}")
    
    # 가상의 영상 리스트로 트렌드 분석
    fake_videos = [
        {'title': title, 'viewCount': 50000 + i*1000} 
        for i, title in enumerate(test_titles * 3)  # 3번 반복으로 데이터 증가
    ]
    
    trend_analysis = analyzer.analyze_keyword_trends(fake_videos)
    
    print(f"\n=== 트렌드 분석 결과 ===")
    print(f"분석된 카테고리 수: {trend_analysis['total_categories']}")
    print(f"복합 키워드 수: {trend_analysis['total_compounds']}")
    
    print("\n🔥 상위 트렌딩 키워드:")
    for item in trend_analysis['trending_analysis'][:10]:
        print(f"{item['urgency']} {item['keyword']} (점수:{item['score']:.1f}, 언급:{item['count']}회)")

if __name__ == "__main__":
    test_enhanced_analysis()