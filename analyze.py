#!/usr/bin/env python3
"""Analyze collected YouTube data and generate reports."""
import json, os, re, sys
from datetime import datetime, timezone, timedelta
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

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
    
    for ch in data['channels']:
        ch_name = ch['name']
        subs = ch['subscribers']
        
        # Channel summary
        recent_views = sum(v['viewCount'] for v in ch['videos'])
        avg_views = recent_views / len(ch['videos']) if ch['videos'] else 0
        avg_ratio = sum(v['views_to_subs_ratio'] for v in ch['videos']) / len(ch['videos']) if ch['videos'] else 0
        
        channel_summaries.append({
            'name': ch_name,
            'channelId': ch['channelId'],
            'handle': ch.get('handle', ''),
            'subscribers': subs,
            'totalViews': ch['totalViews'],
            'videoCount': ch['videoCount'],
            'thumbnail': ch.get('thumbnail', ''),
            'recentVideoCount': len(ch['videos']),
            'recentTotalViews': recent_views,
            'avgViews': round(avg_views),
            'avgRatio': round(avg_ratio, 4),
        })
        
        for v in ch['videos']:
            all_videos.append({
                **v,
                'channelName': ch_name,
                'channelId': ch['channelId'],
                'subscribers': subs,
            })
    
    # Sort channel summaries by avg ratio
    channel_summaries.sort(key=lambda x: x['avgRatio'], reverse=True)
    
    # Generate top 10 lists for different periods
    periods = {
        '24h': 1,
        '7d': 7,
        '30d': 30,
    }
    
    top_lists = {}
    for period_name, days in periods.items():
        filtered = filter_by_period(all_videos, days)
        filtered.sort(key=lambda x: x['views_to_subs_ratio'], reverse=True)
        top_lists[period_name] = filtered[:10]
    
    # Also create an overall top 10 (all time from collected data)
    all_sorted = sorted(all_videos, key=lambda x: x['views_to_subs_ratio'], reverse=True)
    top_lists['all'] = all_sorted[:10]
    
    # Extract trending keywords
    keyword_counter = Counter()
    for v in all_videos:
        keywords = extract_keywords(v['title'])
        keyword_counter.update(keywords)
    
    trending_keywords = [
        {'keyword': k, 'count': c}
        for k, c in keyword_counter.most_common(50)
    ]
    
    # Build analysis result
    analysis = {
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'collected_at': collected_at,
        'total_channels': len(data['channels']),
        'total_videos': len(all_videos),
        'top_videos': top_lists,
        'trending_keywords': trending_keywords,
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
    print(f"🎬 분석 영상: {len(all_videos)}개")
    print("=" * 50)
    
    print("\n🔥 TOP 10 영상 (구독자 대비 조회수 비율 - 최근 7일)")
    print("-" * 50)
    top_7d = top_lists.get('7d', [])
    if not top_7d:
        print("  최근 7일 데이터 없음")
    for i, v in enumerate(top_7d, 1):
        ratio_pct = v['views_to_subs_ratio'] * 100
        print(f"{i}. [{v['channelName']}] {v['title'][:40]}")
        print(f"   조회수: {v['viewCount']:,} | 구독자: {v['subscribers']:,} | 비율: {ratio_pct:.1f}%")
    
    print("\n🔥 TOP 10 영상 (구독자 대비 조회수 비율 - 전체)")
    print("-" * 50)
    for i, v in enumerate(top_lists['all'], 1):
        ratio_pct = v['views_to_subs_ratio'] * 100
        print(f"{i}. [{v['channelName']}] {v['title'][:40]}")
        print(f"   조회수: {v['viewCount']:,} | 구독자: {v['subscribers']:,} | 비율: {ratio_pct:.1f}%")
    
    print("\n📈 트렌드 키워드 (상위 20개)")
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
