#!/usr/bin/env python3
"""Find YouTube channel IDs by searching for channel names/handles."""
import json, os, sys
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)

channels = [
    {"name": "전세매물왕", "handle": "@jeonse_king"},
    {"name": "부동산 탐정", "handle": "@budongsan_detective"},
    {"name": "알짜부동산", "handle": "@alzzabudongsan"},
    {"name": "돈 되는 부동산", "handle": "@moneybudongsan"},
    {"name": "부동산 지식인", "handle": "@budongsan_jiskim"},
    {"name": "부동산 분석왕", "handle": "@budongsan_king"},
    {"name": "리얼터 김사부", "handle": "@realtorkimsabu"},
    {"name": "부동산 하우스", "handle": "@budongsan_house"},
    {"name": "집터뷰", "handle": "@jipterview"},
    {"name": "경제 읽어주는 언니", "handle": "@economysister"},
    {"name": "월급쟁이 부동산 투자", "handle": "@wbinvest"},
    {"name": "부룡이네 부동산", "handle": "@BuryongBudongsan"},
    {"name": "집코노미", "handle": "@zipconomy"},
    {"name": "부동산 읽어주는 남자", "handle": ""},
    {"name": "셜록현준", "handle": "@sherlockhyunjoon"},
    {"name": "빠숑", "handle": "@ppasyong"},
    {"name": "리치고TV", "handle": ""},
]

results = []
for ch in channels:
    query = ch['handle'] if ch['handle'] else ch['name']
    try:
        # Try handle-based lookup first
        if ch['handle']:
            try:
                resp = youtube.channels().list(part='snippet', forHandle=ch['handle'].lstrip('@')).execute()
                if resp.get('items'):
                    item = resp['items'][0]
                    ch['id'] = item['id']
                    ch['resolved_name'] = item['snippet']['title']
                    results.append(ch)
                    print(f"✓ {ch['name']} -> {ch['id']} ({ch['resolved_name']})", file=sys.stderr)
                    continue
            except Exception as e:
                print(f"  Handle lookup failed for {ch['handle']}: {e}", file=sys.stderr)
        
        # Fall back to search
        resp = youtube.search().list(part='snippet', q=ch['name'] + ' 부동산', type='channel', maxResults=3).execute()
        if resp.get('items'):
            item = resp['items'][0]
            ch['id'] = item['snippet']['channelId']
            ch['resolved_name'] = item['snippet']['title']
            results.append(ch)
            print(f"✓ {ch['name']} -> {ch['id']} ({ch['resolved_name']})", file=sys.stderr)
        else:
            ch['id'] = 'NOT_FOUND'
            results.append(ch)
            print(f"✗ {ch['name']} -> NOT FOUND", file=sys.stderr)
    except Exception as e:
        ch['id'] = 'ERROR'
        results.append(ch)
        print(f"✗ {ch['name']} -> ERROR: {e}", file=sys.stderr)

output = {"channels": [{"name": r['name'], "id": r['id'], "handle": r['handle']} for r in results]}
print(json.dumps(output, ensure_ascii=False, indent=2))
