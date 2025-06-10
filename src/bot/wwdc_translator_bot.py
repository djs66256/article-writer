import os
import sys
import asyncio
import urllib

from src.agent.wwdc_translator import graph

# https://developer.apple.com/cn/videos/play/wwdc2025/221/
# get last 2 components of url
# @return (year, video_id)
def _parse_video_url(video_url):
    parsed = urllib.parse.urlparse(video_url)
    path_components = parsed.path.strip('/').split('/')
    if len(path_components) >= 2:
        year = path_components[-2].replace('wwdc', '')
        video_id = path_components[-1]
        return (year, video_id)
    raise ValueError("Invalid WWDC video URL format")

async def _translate_wwdc_video(video):
    if video_url := video.get('url', None):
        try:
            year, video_id = _parse_video_url(video_url)
            print(f"Translating {year} {video_id}...")
            async for chunk in graph.astream(
                input={},
                config={
                    "configurable": {
                        "model": os.environ.get("LLM_MODEL", ""),
                        "base_url": os.environ.get("LLM_BASE_URL", ""),
                        "api_key": os.environ.get("LLM_API_KEY", ""),

                        "year": year,
                        "video_id": video_id,
                        "use_cache": True
                    }
                }
            ):
                print(chunk)
        except Exception as e:
            print(e, file=sys.stderr)
            return
    

async def translate_wwdc_videos_async(videos: list, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def limited_task(video):
        async with semaphore:
            return await _translate_wwdc_video(video)

    tasks = [limited_task(video) for video in videos]
    results = await asyncio.gather(*tasks)
    print('All results:', results)


def translate_wwdc_videos(videos: list):
    asyncio.run(translate_wwdc_videos_async(videos))