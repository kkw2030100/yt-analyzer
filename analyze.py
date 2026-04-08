#!/usr/bin/env python3
"""Analyze collected YouTube data and generate reports."""
import json, os, re, sys
from datetime import datetime, timezone, timedelta
from collections import Counter

# Import enhanced keyword analyzer
try:
    from enhanced_keywords import EnhancedKeywordAnalyzer
    ENHANCED_ANALYSIS = True
except ImportError:
    ENHANCED_ANALYSIS = False
    print("Warning: Enhanced keyword analysis not available")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 부동산/경제 관련 키워드 — 제목에 하나라도 포함되면 관련 영상으로 판정
RELEVANT_KEYWORDS = [
    # 부동산
    '부동산', '아파트', '전세', '월세', '매매', '분양', '재건축', '재개발', '청약',
    '입주', '공급', '미분양', '매물', '집값', '전셋값', '주택', '오피스텔', '빌라',
    '토지', '상가', '건물', '임대', '임차', '계약', '등기', '중개', '공인중개',
    '리모델링', '인테리어', '건축', '시행', '시공', 'PF', '분상제', '디벨로퍼',
    '신축', '구축', '갭투자', '역전세', '깡통', '전세사기', '전월세', '보증금',
    '내집마련', '내 집', '주거', '거주', '이사', '입지', '학군', '역세권', '교통',
    # 지역 (주요)
    '강남', '서초', '송파', '마포', '용산', '성동', '광진', '영등포', '양천',
    '수도권', '서울', '경기', '인천', '부산', '대구', '광주', '대전', '세종',
    '판교', '분당', '일산', '위례', '과천', '하남', '미사', '동탄', '광교',
    '해운대', '수영', '남천', '센텀', '마린시티',
    # 경제/금융
    '경제', '금리', '환율', '물가', '인플레', '디플레', 'GDP', '고용', '실업',
    '경기', '불황', '호황', '침체', '회복', '성장률', '기준금리', '금통위',
    '연준', '파월', 'FOMC', '기축통화', '달러', '엔화', '위안', '원화',
    '무역', '수출', '수입', '관세', '무역전쟁', '관세전쟁',
    # 재테크/자산관리 (부동산+경제 중심, 주식/ETF/채권 제외)
    '금투자', '은투자', '금값', '은값', '금시세', '은시세', '골드', '실버',
    '원자재', '자산', '재테크', '저축', '적금',
    '연금', '보험', '대출', '모기지', '담보', 'IRP', '퇴직금', '퇴직연금',
    '종잣돈', '복리', '이자', '예금', '원유',
    # 세금/정책
    '세금', '양도세', '종부세', '취득세', '재산세', '증여세', '상속세',
    '절세', '세율', '공시가', '공시지가', '규제', '대출규제', 'DSR', 'DTI', 'LTV',
    '정책', '부동산정책', '대책', '특례',
]

# 짧은 키워드는 단독 단어로만 매칭 (예: '은' → '은행'에 걸리면 안 되지만, '영국은'에도 걸리면 안 됨)
_SHORT_KEYWORDS = set()  # 2글자 이하로 다른 단어에 포함될 수 있는 것들

def is_relevant(title):
    """Check if a video title is related to real estate or economy."""
    title_lower = title.lower()
    for kw in RELEVANT_KEYWORDS:
        kw_lower = kw.lower()
        if kw in _SHORT_KEYWORDS:
            # 단독 단어 매칭: 앞뒤가 한글/영문이 아닌 경우만
            pattern = r'(?<![가-힣a-zA-Z])' + re.escape(kw_lower) + r'(?![가-힣a-zA-Z])'
            if re.search(pattern, title_lower):
                return True
        else:
            if kw_lower in title_lower:
                return True
    return False


# Korean stop words to filter out
STOP_WORDS = set([
    '의', '가', '이', '은', '는', '을', '를', '에', '에서', '와', '과', '도', '로', '으로',
    '만', '까지', '부터', '에게', '한테', '께', '보다', '처럼', '같이', '마다', '밖에',
    '하다', '되다', '있다', '없다', '않다', '못하다', '이다', '아니다',
    '그', '그녀', '그것', '이것', '저것', '것', '수', '등', '및', '또', '또는',
    '그리고', '하지만', '그런데', '따라서', '때문에', '위해', '대해', '통해',
    '더', '가장', '매우', '너무', '정말', '진짜', '아주', '꽤', '상당히',
    '안', '못', '잘', '다', '모두', '다시', '이미', '아직', '바로', '지금',
    '년', '월', '일', '시', '분', '초', '개', '번', '명', '원', '만원', '억',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'vs', 'ft', 'ep', 'vol', '|', '-', '~', '!', '?', '#', '&',
    '이번', '지금', '오늘', '내일', '어제', '최근', '현재', '올해', '내년',
    '합니다', '합니다.', '입니다', '입니다.', '에요', '해요', '했다', '된다',
])


def extract_keywords(title):
    """Extract meaningful Korean words from a video title."""
    # Remove special characters but keep Korean and alphanumeric
    cleaned = re.sub(r'[^\w가-힣\s]', ' ', title)
    words = cleaned.split()
    keywords = []
    for w in words:
        w = w.strip()
        if len(w) < 2:
            continue
        if w.lower() in STOP_WORDS:
            continue
        if w.isdigit():
            continue
        keywords.append(w)
    return keywords


def filter_by_period(videos, days):
    """Filter videos published within the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []
    for v in videos:
        try:
            pub = datetime.fromisoformat(v['publishedAt'].replace('Z', '+00:00'))
            if pub >= cutoff:
                filtered.append(v)
        except (ValueError, KeyError):
            continue
    return filtered


def main():
    latest_file = os.path.join(DATA_DIR, 'latest.json')
    if not os.path.exists(latest_file):
        print("ERROR: data/latest.json not found. Run collect.py first.", file=sys.stderr)
        sys.exit(1)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    collected_at = data.get('collected_at', '')
    
    # Flatten all videos with channel info
    all_videos = []
    channel_summaries = []
    all_regular = []
    all_shorts = []
    
    for ch in data['channels']:
        ch_name = ch['name']
        subs = ch['subscribers']
        
        # Separate counts for shorts vs regular
        ch_regular = [v for v in ch['videos'] if not v.get('isShorts', v.get('duration', 0) <= 60)]
        ch_shorts = [v for v in ch['videos'] if v.get('isShorts', v.get('duration', 0) <= 60)]
        
        # Channel summary — 기본 성과는 동영상(regular)만으로 계산 (Shorts 제외)
        recent_views_regular = sum(v['viewCount'] for v in ch_regular)
        avg_views = recent_views_regular / len(ch_regular) if ch_regular else 0
        avg_ratio = sum(v['views_to_subs_ratio'] for v in ch_regular) / len(ch_regular) if ch_regular else 0
        
        channel_summaries.append({
            'name': ch_name,
            'channelId': ch['channelId'],
            'handle': ch.get('handle', ''),
            'subscribers': subs,
            'totalViews': ch['totalViews'],
            'videoCount': ch['videoCount'],
            'thumbnail': ch.get('thumbnail', ''),
            'recentVideoCount': len(ch_regular),
            'recentTotalViews': recent_views_regular,
            'avgViews': round(avg_views),
            'avgRatio': round(avg_ratio, 4),
            'regularCount': len(ch_regular),
            'shortsCount': len(ch_shorts),
            'avgViewsRegular': round(sum(v['viewCount'] for v in ch_regular) / len(ch_regular)) if ch_regular else 0,
            'avgViewsShorts': round(sum(v['viewCount'] for v in ch_shorts) / len(ch_shorts)) if ch_shorts else 0,
            'avgRatioRegular': round(sum(v['views_to_subs_ratio'] for v in ch_regular) / len(ch_regular), 4) if ch_regular else 0,
            'avgRatioShorts': round(sum(v['views_to_subs_ratio'] for v in ch_shorts) / len(ch_shorts), 4) if ch_shorts else 0,
        })
        
        for v in ch['videos']:
            entry = {
                **v,
                'channelName': ch_name,
                'channelId': ch['channelId'],
                'subscribers': subs,
            }
            # Determine isShorts: use field if present, otherwise fallback to duration
            is_short = v.get('isShorts', v.get('duration', 0) <= 60)
            entry['isShorts'] = is_short
            entry['isRelevant'] = is_relevant(v['title'])
            all_videos.append(entry)
            if is_short:
                all_shorts.append(entry)
            else:
                all_regular.append(entry)
    
    # Sort channel summaries by avg ratio
    channel_summaries.sort(key=lambda x: x['avgRatio'], reverse=True)
    
    # Generate top 10 lists for different periods
    periods = {
        '24h': 1,
        '7d': 7,
        '30d': 30,
    }
    
    top_videos_lists = {}
    top_shorts_lists = {}
    for period_name, days in periods.items():
        fv = filter_by_period(all_regular, days)
        fv = [v for v in fv if v['viewCount'] >= 50000 and v.get('isRelevant', True)]
        fv.sort(key=lambda x: x['views_to_subs_ratio'], reverse=True)
        top_videos_lists[period_name] = fv[:10]
        
        fs = filter_by_period(all_shorts, days)
        fs = [v for v in fs if v['viewCount'] >= 50000 and v.get('isRelevant', True)]
        fs.sort(key=lambda x: x['views_to_subs_ratio'], reverse=True)
        top_shorts_lists[period_name] = fs[:10]
    
    # Also create an overall top 10 (all time from collected data)
    reg_filtered = [v for v in all_regular if v['viewCount'] >= 50000 and v.get('isRelevant', True)]
    reg_sorted = sorted(reg_filtered, key=lambda x: x['views_to_subs_ratio'], reverse=True)
    top_videos_lists['all'] = reg_sorted[:10]
    
    shorts_filtered = [v for v in all_shorts if v['viewCount'] >= 50000 and v.get('isRelevant', True)]
    shorts_sorted = sorted(shorts_filtered, key=lambda x: x['views_to_subs_ratio'], reverse=True)
    top_shorts_lists['all'] = shorts_sorted[:10]
    
    # Extract trending keywords (enhanced if available)
    if ENHANCED_ANALYSIS:
        analyzer = EnhancedKeywordAnalyzer()
        enhanced_analysis = analyzer.analyze_keyword_trends(all_videos, period_days=30)
        
        trending_keywords = [
            {
                'keyword': item['keyword'],
                'count': item['count'], 
                'score': item.get('score', 0),
                'urgency': item.get('urgency', '🟢일반'),
                'category': item.get('category', 'unknown'),
                'type': item.get('type', 'simple')
            }
            for item in enhanced_analysis['trending_analysis']
        ]
        
        # Also keep basic keyword analysis for backward compatibility
        keyword_counter = Counter()
        for v in all_videos:
            keywords = extract_keywords(v['title'])
            keyword_counter.update(keywords)
        
        basic_keywords = [
            {'keyword': k, 'count': c, 'score': c, 'urgency': '🟢일반', 'category': 'basic', 'type': 'basic'}
            for k, c in keyword_counter.most_common(30)
        ]
    else:
        # Fallback to basic keyword analysis
        keyword_counter = Counter()
        for v in all_videos:
            keywords = extract_keywords(v['title'])
            keyword_counter.update(keywords)
        
        trending_keywords = [
            {'keyword': k, 'count': c, 'score': c, 'urgency': '🟢일반', 'category': 'basic', 'type': 'basic'}
            for k, c in keyword_counter.most_common(50)
        ]
        basic_keywords = trending_keywords
        enhanced_analysis = None
    
    # Build analysis result
    analysis = {
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'collected_at': collected_at,
        'total_channels': len(data['channels']),
        'total_videos': len(all_videos),
        'total_regular': len(all_regular),
        'total_shorts': len(all_shorts),
        'top_videos': top_videos_lists,
        'top_shorts': top_shorts_lists,
        'trending_keywords': trending_keywords,
        'basic_keywords': basic_keywords if ENHANCED_ANALYSIS else trending_keywords,
        'enhanced_analysis': enhanced_analysis,
        'has_enhanced_analysis': ENHANCED_ANALYSIS,
        'channel_summaries': channel_summaries,
    }
    
    # Save analysis
    analysis_file = os.path.join(DATA_DIR, 'analysis.json')
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"Analysis saved to {analysis_file}", file=sys.stderr)
    
    # Print summary report to stdout (for Telegram)
    print("=" * 50)
    print("📊 유튜브 채널 분석 리포트")
    print(f"📅 수집: {collected_at[:10] if collected_at else 'N/A'}")
    print(f"📺 분석 채널: {len(data['channels'])}개")
    print(f"🎬 분석 영상: {len(all_videos)}개 (동영상: {len(all_regular)} / Shorts: {len(all_shorts)})")
    print("=" * 50)
    
    print("\n🔥 TOP 10 동영상 (구독자 대비 조회수 비율 - 최근 7일)")
    print("-" * 50)
    top_7d = top_videos_lists.get('7d', [])
    if not top_7d:
        print("  최근 7일 데이터 없음")
    for i, v in enumerate(top_7d, 1):
        ratio_pct = v['views_to_subs_ratio'] * 100
        print(f"{i}. [{v['channelName']}] {v['title'][:40]}")
        print(f"   조회수: {v['viewCount']:,} | 구독자: {v['subscribers']:,} | 비율: {ratio_pct:.1f}%")
    
    print("\n🔥 TOP 10 동영상 (구독자 대비 조회수 비율 - 전체)")
    print("-" * 50)
    for i, v in enumerate(top_videos_lists['all'], 1):
        ratio_pct = v['views_to_subs_ratio'] * 100
        print(f"{i}. [{v['channelName']}] {v['title'][:40]}")
        print(f"   조회수: {v['viewCount']:,} | 구독자: {v['subscribers']:,} | 비율: {ratio_pct:.1f}%")
    
    if top_shorts_lists.get('all'):
        print("\n📱 TOP 5 Shorts (구독자 대비 조회수 비율 - 전체)")
        print("-" * 50)
        for i, v in enumerate(top_shorts_lists['all'][:5], 1):
            ratio_pct = v['views_to_subs_ratio'] * 100
            print(f"{i}. [{v['channelName']}] {v['title'][:40]}")
            print(f"   조회수: {v['viewCount']:,} | 구독자: {v['subscribers']:,} | 비율: {ratio_pct:.1f}%")
    
    print("\n📈 트렌드 키워드 분석")
    print("=" * 50)
    
    if ENHANCED_ANALYSIS and enhanced_analysis:
        # Enhanced analysis output
        print("🔥 세분화된 키워드 분석 (상위 15개)")
        print("-" * 50)
        
        urgent_keywords = [k for k in trending_keywords if k.get('urgency') == '🔴긴급']
        important_keywords = [k for k in trending_keywords if k.get('urgency') == '🟡중요']
        normal_keywords = [k for k in trending_keywords if k.get('urgency') == '🟢일반']
        
        if urgent_keywords:
            print("🔴 긴급 키워드:")
            for k in urgent_keywords[:5]:
                category_short = k['category'].split('/')[-1] if '/' in k['category'] else k['category']
                print(f"   {k['keyword']} (점수:{k['score']:.1f}, 언급:{k['count']}회, {category_short})")
        
        if important_keywords:
            print("🟡 중요 키워드:")
            for k in important_keywords[:5]:
                category_short = k['category'].split('/')[-1] if '/' in k['category'] else k['category']
                print(f"   {k['keyword']} (점수:{k['score']:.1f}, 언급:{k['count']}회, {category_short})")
        
        if normal_keywords:
            print("🟢 일반 키워드:")
            for k in normal_keywords[:5]:
                category_short = k['category'].split('/')[-1] if '/' in k['category'] else k['category']
                print(f"   {k['keyword']} (점수:{k['score']:.1f}, 언급:{k['count']}회, {category_short})")
        
        # Category summary
        category_counts = {}
        for k in trending_keywords:
            main_category = k['category'].split('/')[0] if '/' in k['category'] else k['category']
            category_counts[main_category] = category_counts.get(main_category, 0) + k['count']
        
        if category_counts:
            print("\n📊 카테고리별 언급량:")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {category}: {count}회")
        
        print(f"\n분석 통계: 카테고리 {enhanced_analysis.get('total_categories', 0)}개, 복합키워드 {enhanced_analysis.get('total_compounds', 0)}개")
    else:
        # Basic analysis fallback
        print("📈 기본 키워드 (상위 20개)")
        print("-" * 50)
        kw_str = ", ".join([f"{k['keyword']}({k['count']})" for k in trending_keywords[:20]])
        print(kw_str)
    
    print("\n📊 채널별 성과 (평균 조회수/구독자 비율)")
    print("-" * 50)
    for ch in channel_summaries:
        ratio_pct = ch['avgRatio'] * 100
        emoji = "🔴" if ch['avgRatio'] > 0.10 else "🟠" if ch['avgRatio'] > 0.05 else "🟡" if ch['avgRatio'] > 0.02 else "⚪"
        print(f"{emoji} {ch['name']}: 구독자 {ch['subscribers']:,} | 평균비율 {ratio_pct:.1f}% | 평균조회 {ch['avgViews']:,}")
    
    print("\n" + "=" * 50)


if __name__ == '__main__':
    main()
