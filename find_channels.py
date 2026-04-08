#!/usr/bin/env python3
import json, os, time
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)

# Load existing channels
with open("channels.json") as f:
    data = json.load(f)
existing_ids = {ch["id"] for ch in data["channels"]}

# Keywords to search
keywords = ["부동산", "부동산투자", "경제", "재테크", "아파트투자", "부동산분석", "경제뉴스", "주식투자", "금융"]
# Specific channel names to search
specific_names = ["월급쟁이부자들", "삼프로TV", "슈카월드", "신사임당", "김작가TV", "전원주", 
                  "머니인사이드", "박곰희TV", "소수몽키", "부동산지식채널", "재테크하는아빠곰", 
                  "너나위", "월부TV"]

all_channel_ids = set()

# Search by keywords
for kw in keywords:
    try:
        resp = youtube.search().list(q=kw, type="channel", regionCode="KR", maxResults=25, part="snippet").execute()
        for item in resp.get("items", []):
            cid = item["snippet"]["channelId"]
            all_channel_ids.add(cid)
        print(f"Keyword '{kw}': found {len(resp.get('items', []))} channels")
        time.sleep(0.2)
    except Exception as e:
        print(f"Error searching '{kw}': {e}")

# Search by specific names
for name in specific_names:
    try:
        resp = youtube.search().list(q=name, type="channel", regionCode="KR", maxResults=5, part="snippet").execute()
        for item in resp.get("items", []):
            cid = item["snippet"]["channelId"]
            all_channel_ids.add(cid)
        print(f"Name '{name}': found {len(resp.get('items', []))} channels")
        time.sleep(0.2)
    except Exception as e:
        print(f"Error searching '{name}': {e}")

print(f"\nTotal unique channel IDs collected: {len(all_channel_ids)}")

# Remove already existing
new_ids = all_channel_ids - existing_ids
print(f"New channel IDs (not in existing): {len(new_ids)}")

# Batch fetch stats for new channels
new_channels = []
id_list = list(new_ids)
for i in range(0, len(id_list), 50):
    batch = id_list[i:i+50]
    resp = youtube.channels().list(part="snippet,statistics", id=",".join(batch)).execute()
    for item in resp.get("items", []):
        stats = item.get("statistics", {})
        subs = int(stats.get("subscriberCount", 0))
        if subs < 10000:
            continue
        snippet = item["snippet"]
        handle = snippet.get("customUrl", "")
        name = snippet["title"]
        cid = item["id"]
        
        if subs >= 100000:
            cat = "benchmark"
        elif subs >= 30000:
            cat = "mid"
        else:
            cat = "small"
        
        new_channels.append({
            "name": name,
            "id": cid,
            "handle": handle,
            "category": cat,
            "_subs": subs  # temp for sorting/display
        })

# Sort by subscribers desc
new_channels.sort(key=lambda x: x["_subs"], reverse=True)

# We want 40-50 total. Currently 16. So add up to 34.
max_to_add = 50 - len(data["channels"])
channels_to_add = new_channels[:max_to_add]

print(f"\nChannels meeting criteria (10k+ subs): {len(new_channels)}")
print(f"Adding {len(channels_to_add)} new channels (limit to reach ~50 total)")
print(f"\nNew channels to add:")
for ch in channels_to_add:
    print(f"  {ch['name']:30s} | {ch['_subs']:>10,} subs | {ch['category']:10s} | {ch['handle']}")

# Remove temp _subs field and merge
for ch in channels_to_add:
    entry = {k: v for k, v in ch.items() if k != "_subs"}
    data["channels"].append(entry)

print(f"\nTotal channels after merge: {len(data['channels'])}")

# Save
with open("channels.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Saved channels.json")
