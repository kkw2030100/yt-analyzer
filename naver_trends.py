#!/usr/bin/env python3
"""Naver search trend and news analysis for real estate keywords."""
import json, os, sys, requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
    print("WARNING: Naver API keys not found. Set NAVER_CLIENT_ID and NAVER_CLIENT_SECRET in .env")
    print("Visit: https://developers.naver.com/apps/#/register")

# 부동산 관련 주요 키워드들
REAL_ESTATE_KEYWORDS = [
    "아파트", "분양", "전세", "매매", "부동산", "청약",
    "재건축", "재개발", "신축", "입주", "분양권", "중도금",
    "대출", "금리", "주택담보대출", "LTV", "DTI",
    "강남", "서초", "송파", "압구정", "역삼", "판교",
    "용산", "마포", "영등포", "강서", "노원", "은평",
    "수지", "분당", "일산", "평촌", "중동", "광교"
]

class NaverTrendAnalyzer:
    def __init__(self):
        self.headers = {
            'X-Naver-Client-Id': NAVER_CLIENT_ID,
            'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
            'Content-Type': 'application/json'
        }
    
    def get_search_trends(self, keywords, period_days=7):
        """네이버 데이터랩 검색 트렌드 조회"""
        if not NAVER_CLIENT_ID:
            return {"error": "API key not configured"}
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # 네이버 데이터랩 API는 최대 5개 키워드까지 비교 가능
        results = []
        for i in range(0, len(keywords), 5):
            keyword_group = keywords[i:i+5]
            
            data = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "timeUnit": "date",
                "keywordGroups": [
                    {
                        "groupName": keyword,
                        "keywords": [keyword]
                    } for keyword in keyword_group
                ]
            }
            
            try:
                response = requests.post(
                    'https://openapi.naver.com/v1/datalab/search',
                    headers=self.headers,
                    data=json.dumps(data)
                )
                
                if response.status_code == 200:
                    result = response.json()
                    results.append(result)
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"API 요청 실패: {e}")
        
        return results
    
    def search_news(self, keyword, count=10):
        """네이버 뉴스 검색"""
        if not NAVER_CLIENT_ID:
            return {"error": "API key not configured"}
            
        try:
            url = "https://openapi.naver.com/v1/search/news.json"
            params = {
                'query': keyword,
                'display': count,
                'sort': 'sim'  # 정확도순 (sim) 또는 날짜순 (date)
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"뉴스 검색 실패: {response.status_code} - {response.text}")
                return {"error": f"API Error: {response.status_code}"}
                
        except Exception as e:
            print(f"뉴스 검색 실패: {e}")
            return {"error": str(e)}
    
    def analyze_trend_changes(self, trend_data):
        """트렌드 변화율 분석"""
        analysis = []
        
        for result in trend_data:
            if 'results' not in result:
                continue
                
            for keyword_result in result['results']:
                keyword = keyword_result['title']
                data_points = keyword_result['data']
                
                if len(data_points) < 2:
                    continue
                
                # 최근 3일 평균 vs 그 이전 기간 평균
                recent_values = [point['ratio'] for point in data_points[-3:]]
                older_values = [point['ratio'] for point in data_points[:-3]]
                
                if not older_values:
                    continue
                    
                recent_avg = sum(recent_values) / len(recent_values)
                older_avg = sum(older_values) / len(older_values)
                
                if older_avg > 0:
                    change_rate = ((recent_avg - older_avg) / older_avg) * 100
                else:
                    change_rate = 0
                
                analysis.append({
                    'keyword': keyword,
                    'recent_avg': round(recent_avg, 2),
                    'older_avg': round(older_avg, 2),
                    'change_rate': round(change_rate, 2),
                    'trend': 'up' if change_rate > 10 else 'down' if change_rate < -10 else 'stable'
                })
        
        # 변화율 순으로 정렬
        analysis.sort(key=lambda x: abs(x['change_rate']), reverse=True)
        return analysis
    
    def get_trending_keywords(self, period_days=7):
        """급상승 키워드 분석"""
        print(f"부동산 키워드 트렌드 분석 시작... (최근 {period_days}일)")
        
        # 검색 트렌드 수집
        trend_data = self.get_search_trends(REAL_ESTATE_KEYWORDS, period_days)
        
        if not trend_data or (len(trend_data) == 1 and 'error' in trend_data[0]):
            return {"error": "트렌드 데이터를 가져올 수 없습니다."}
        
        # 트렌드 변화 분석
        analysis = self.analyze_trend_changes(trend_data)
        
        # 상위 급상승 키워드들에 대한 뉴스 수집
        top_keywords = [item['keyword'] for item in analysis[:5] if item['trend'] == 'up']
        
        news_results = {}
        for keyword in top_keywords:
            news_data = self.search_news(f"부동산 {keyword}", count=5)
            if 'items' in news_data:
                news_results[keyword] = news_data['items']
        
        return {
            'period_days': period_days,
            'analysis_time': datetime.now().isoformat(),
            'trend_analysis': analysis,
            'trending_news': news_results,
            'summary': {
                'total_keywords': len(analysis),
                'up_trends': len([x for x in analysis if x['trend'] == 'up']),
                'down_trends': len([x for x in analysis if x['trend'] == 'down']),
                'stable_trends': len([x for x in analysis if x['trend'] == 'stable'])
            }
        }

def main():
    """테스트 실행"""
    analyzer = NaverTrendAnalyzer()
    
    # 1일, 3일, 7일, 30일 트렌드 분석
    periods = [1, 3, 7, 30]
    
    results = {}
    for period in periods:
        print(f"\n=== 최근 {period}일 트렌드 분석 ===")
        result = analyzer.get_trending_keywords(period)
        results[f"{period}days"] = result
        
        if 'error' not in result:
            print(f"급상승 키워드: {len([x for x in result['trend_analysis'] if x['trend'] == 'up'])}개")
            print(f"급하락 키워드: {len([x for x in result['trend_analysis'] if x['trend'] == 'down'])}개")
            
            # 상위 5개 변화 키워드 출력
            for item in result['trend_analysis'][:5]:
                print(f"  {item['keyword']}: {item['change_rate']:+.1f}% ({item['trend']})")
        else:
            print(f"오류: {result['error']}")
    
    # 결과를 파일로 저장
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(DATA_DIR, f'naver_trends_{today}.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 저장: {output_file}")
    return results

if __name__ == "__main__":
    main()