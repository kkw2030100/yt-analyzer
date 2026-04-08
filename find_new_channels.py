#!/usr/bin/env python3
"""Find popular Korean real estate and economy YouTube channels and add to channels.json."""

import json
import os
import time
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNELS_FILE = "channels.json"

# Search keywords
KEYWORDS = [
    "부동산", "부동산투자", "경제", "재테크", "아파트투자",
    "부동산분석", "경제뉴스", "주식투자", "금융"
]

# Specific channel names to search for
SPECIFIC_CHANNELS = [
    "월급쟁이부자들", "삼프로TV", "슈카월드", "신사임당", "김작가TV",
    "전원주", "머니인사이드", "박곰희TV", "소수몽키", "부동산지식채널",
    "이진우의손에잡히는경제", "재테크하는아빠곰", "너나위", "한문철TV", "월부TV"
]

def main():
    youtube = build("youtube", "v3", developerKey=API_KEY)

    # Load existing channels
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    existing_ids = {ch["id"] for ch in data["channels"]}
    print(f"Existing channels: {len(data['channels'])}")

    # Collect candidate channel IDs
    candidate_ids = set()

    # 1) Search by keywords
    for kw in KEYWORDS:
        print(f"Searching keyword: {kw}")
        try:
            resp = youtube.search().list(
                q=kw, type="channel", regionCode="KR",
                maxResults=25, part="snippet"
            ).execute()
            for item in resp.get("items", []):
                cid = item["snippet"]["channelId"]
                candidate_ids.add(cid)
            time.sleep(0.2)
        except Exception as e:
            print(f"  Error searching '{kw}': {e}")

    # 2) Search specific channel names
    for name in SPECIFIC_CHANNELS:
        print(f"Searching channel: {name}")
        try:
            resp = youtube.search().list(
                q=name, type="channel", regionCode="KR",
                maxResults=5, part="snippet"
            ).execute()
            for item in resp.get("items", []):
                cid = item["snippet"]["channelId"]
                candidate_ids.add(cid)
            time.sleep(0.2)
        except Exception as e:
            print(f"  Error searching '{name}': {e}")

    print(f"\nTotal candidate channel IDs found: {len(candidate_ids)}")
    
    # Remove already existing
    new_ids = candidate_ids - existing_ids
    print(f"New (not in channels.json): {len(new_ids)}")

    if not new_ids:
        print("No new channels to add.")
        return

    # 3) Get channel details in batches of 50
    new_channels = []
    id_list = list(new_ids)
    for i in range(0, len(id_list), 50):
        batch = id_list[i:i+50]
        try:
            resp = youtube.channels().list(
                id=",".join(batch),
                part="snippet,statistics"
            ).execute()
            for item in resp.get("items", []):
                subs = int(item["statistics"].get("subscriberCount", 0))
                if subs < 10000:
                    continue
                # Categorize
                if subs >= 100000:
                    category = "benchmark"
                elif subs >= 30000:
                    category = "mid"
                else:
                    category = "small"
                
                handle = item["snippet"].get("customUrl", "")
                new_channels.append({
                    "name": item["snippet"]["title"],
                    "id": item["id"],
                    "handle": handle,
                    "category": category,
                    "subscribers": subs  # for sorting/display, will remove before save
                })
        except Exception as e:
            print(f"  Error fetching channel details: {e}")

    # Sort by subscribers descending
    new_channels.sort(key=lambda x: x["subscribers"], reverse=True)

    # Limit to reach ~40-50 total
    max_to_add = 50 - len(data["channels"])
    if len(new_channels) > max_to_add:
        new_channels = new_channels[:max_to_add]

    print(f"\nAdding {len(new_channels)} new channels:")
    print(f"{'Name':<30} {'Subscribers':>12} {'Category':<10}")
    print("-" * 55)
    for ch in new_channels:
        print(f"{ch['name']:<30} {ch['subscribers']:>12,} {ch['category']:<10}")

    # Add to data (without subscribers field)
    for ch in new_channels:
        subs = ch.pop("subscribers")
        data["channels"].append(ch)

    # Save
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nTotal channels now: {len(data['channels'])}")
    print(f"Saved to {CHANNELS_FILE}")

if __name__ == "__main__":
    main()
