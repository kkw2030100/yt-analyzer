#!/usr/bin/env python3
"""Collect YouTube channel and video data for Korean real estate channels."""
import json, os, sys, re
from datetime import datetime, timezone
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')
if not API_KEY:
    print("ERROR: YOUTUBE_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)

youtube = build('youtube', 'v3', developerKey=API_KEY)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)


def parse_duration(duration_str):
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    if not duration_str:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    h, m, s = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)


def get_channel_stats(channel_ids):
    """Get channel statistics for a batch of channel IDs (max 50)."""
    stats = {}
    try:
        resp = youtube.channels().list(
            part='statistics,snippet',
            id=','.join(channel_ids)
        ).execute()
        for item in resp.get('items', []):
            cid = item['id']
            s = item['statistics']
            stats[cid] = {
                'title': item['snippet']['title'],
                'subscribers': int(s.get('subscriberCount', 0)),
                'totalViews': int(s.get('viewCount', 0)),
                'videoCount': int(s.get('videoCount', 0)),
                'thumbnail': item['snippet']['thumbnails'].get('default', {}).get('url', ''),
            }
    except HttpError as e:
        print(f"ERROR getting channel stats: {e}", file=sys.stderr)
    return stats


def get_upload_playlist_id(channel_id):
    """Get the uploads playlist ID for a channel."""
    return 'UU' + channel_id[2:]


def get_latest_videos(channel_id, max_results=30):
    """Get latest videos from a channel's uploads playlist."""
    videos = []
    playlist_id = get_upload_playlist_id(channel_id)
    try:
        next_page = None
        fetched = 0
        while fetched < max_results:
            batch = min(50, max_results - fetched)
            resp = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=batch,
                pageToken=next_page
            ).execute()
            for item in resp.get('items', []):
                videos.append({
                    'videoId': item['contentDetails']['videoId'],
                    'title': item['snippet']['title'],
                    'publishedAt': item['contentDetails'].get('videoPublishedAt', item['snippet']['publishedAt']),
                    'thumbnail': item['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                })
            fetched += len(resp.get('items', []))
            next_page = resp.get('nextPageToken')
            if not next_page:
                break
    except HttpError as e:
        print(f"ERROR getting videos for {channel_id}: {e}", file=sys.stderr)
    return videos[:max_results]


def get_video_stats(video_ids):
    """Get statistics for a batch of videos (max 50)."""
    stats = {}
    if not video_ids:
        return stats
    try:
        # Process in batches of 50
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            resp = youtube.videos().list(
                part='statistics,contentDetails',
                id=','.join(batch)
            ).execute()
            for item in resp.get('items', []):
                vid = item['id']
                s = item['statistics']
                stats[vid] = {
                    'viewCount': int(s.get('viewCount', 0)),
                    'likeCount': int(s.get('likeCount', 0)),
                    'commentCount': int(s.get('commentCount', 0)),
                    'duration': parse_duration(item['contentDetails'].get('duration', '')),
                    'durationRaw': item['contentDetails'].get('duration', ''),
                }
    except HttpError as e:
        print(f"ERROR getting video stats: {e}", file=sys.stderr)
    return stats


def main():
    # Load channel list
    channels_file = os.path.join(BASE_DIR, 'channels.json')
    with open(channels_file, 'r', encoding='utf-8') as f:
        channels_data = json.load(f)
    
    channels = channels_data['channels']
    channel_ids = [ch['id'] for ch in channels if ch['id'] not in ('FIND_ID', 'NOT_FOUND', 'ERROR')]
    
    if not channel_ids:
        print("ERROR: No valid channel IDs found", file=sys.stderr)
        sys.exit(1)
    
    print(f"Collecting data for {len(channel_ids)} channels...", file=sys.stderr)
    
    # Get channel stats in batches of 50
    all_channel_stats = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        stats = get_channel_stats(batch)
        all_channel_stats.update(stats)
    
    print(f"Got stats for {len(all_channel_stats)} channels", file=sys.stderr)
    
    # Collect video data for each channel
    results = {
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'channels': []
    }
    
    for ch in channels:
        cid = ch['id']
        if cid in ('FIND_ID', 'NOT_FOUND', 'ERROR'):
            continue
        
        ch_stats = all_channel_stats.get(cid, {})
        if not ch_stats:
            print(f"WARN: No stats for {ch['name']} ({cid})", file=sys.stderr)
            continue
        
        print(f"  Fetching videos for {ch_stats.get('title', ch['name'])}...", file=sys.stderr)
        
        # Get latest videos
        videos = get_latest_videos(cid, max_results=30)
        
        # Get video stats
        video_ids = [v['videoId'] for v in videos]
        video_stats = get_video_stats(video_ids)
        
        # Merge and calculate ratios
        subs = ch_stats['subscribers']
        enriched_videos = []
        for v in videos:
            vs = video_stats.get(v['videoId'], {})
            views = vs.get('viewCount', 0)
            ratio = round(views / subs, 4) if subs > 0 else 0
            enriched_videos.append({
                'videoId': v['videoId'],
                'title': v['title'],
                'publishedAt': v['publishedAt'],
                'thumbnail': v['thumbnail'],
                'viewCount': views,
                'likeCount': vs.get('likeCount', 0),
                'commentCount': vs.get('commentCount', 0),
                'duration': vs.get('duration', 0),
                'durationRaw': vs.get('durationRaw', ''),
                'isShorts': vs.get('duration', 0) <= 60,
                'views_to_subs_ratio': ratio,
            })
        
        channel_entry = {
            'channelId': cid,
            'name': ch_stats.get('title', ch['name']),
            'handle': ch.get('handle', ''),
            'subscribers': subs,
            'totalViews': ch_stats['totalViews'],
            'videoCount': ch_stats['videoCount'],
            'thumbnail': ch_stats.get('thumbnail', ''),
            'videos': enriched_videos,
        }
        results['channels'].append(channel_entry)
        print(f"    -> {len(enriched_videos)} videos collected (subs: {subs:,})", file=sys.stderr)
    
    # Save results
    today = datetime.now().strftime('%Y-%m-%d')
    dated_file = os.path.join(DATA_DIR, f'{today}.json')
    latest_file = os.path.join(DATA_DIR, 'latest.json')
    
    for filepath in [dated_file, latest_file]:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nData saved to {dated_file} and {latest_file}", file=sys.stderr)
    print(f"Total channels: {len(results['channels'])}", file=sys.stderr)
    total_videos = sum(len(ch['videos']) for ch in results['channels'])
    print(f"Total videos: {total_videos}", file=sys.stderr)


if __name__ == '__main__':
    main()
