import os
import sys
import asyncio
import urllib
import datetime

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

def _generate_blog_post(video: map):
    print(f"generating blog post ({video.get('url', None)})...")
    if video_url := video.get('url', None):
        year, video_id = _parse_video_url(video_url)
        base_path = os.path.dirname(os.path.abspath(__file__))
        rewrite_path = os.path.join(base_path, '..', '..', f"output/wwdc/{year}/{video_id}_zh_rewrite.md")
        output_path = os.path.join(base_path, '..', '..', f"output/blog/wwdc/")
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        blog_file_name = f'{datetime.datetime.now().strftime("%Y-%m-%d")}-wwdc{year}_{video_id}.md'
        with open(os.path.join(output_path, blog_file_name), "w") as f:
            head = f"""---
title: {video["title"]}
date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
tags:
- wwdc{year}
{ '\n'.join([f"- {tag}" for tag in video["platform"].split('|')]) }
- {video["category"]}
---
{video.get('description', '')}
<!--more-->

![视频封面]({video["image"]})
[视频地址]({video["url"]})
"""
            foot="""> 此文章由AI生成，可能存在错误，如有问题，请联系[djs66256@163.com](djs66256@163.com)"""
            f.write(head)
            f.write("\n")
            with open(rewrite_path, "r") as ff:
                f.write(ff.read())
            f.write("\n")
            f.write(foot)

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
                # print(chunk)
                pass
            _generate_blog_post(video)
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


def translate_wwdc_videos(videos: list, max_concurrent=3):
    asyncio.run(translate_wwdc_videos_async(videos, max_concurrent=max_concurrent))