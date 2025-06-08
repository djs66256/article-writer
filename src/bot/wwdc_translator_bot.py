import os
import asyncio

from src.agent.wwdc_translator import graph

async def _translate_wwdc_video(year, video_id):
    async for chunk in graph.astream(
        input={},
        config={
            "configurable": {
                "model": os.environ.get("LLM_MODEL", ""),
                "base_url": os.environ.get("LLM_BASE_URL", ""),
                "api_key": os.environ.get("LLM_API_KEY", ""),

                "year": year,
                "video_id": video_id
            }
        }
    ):
        print(chunk)

async def translate_wwdc_videos_async(year: str, video_ids: list[str]):
    tasks = [_translate_wwdc_video(year, video_id) for video_id in video_ids]
    results = await asyncio.gather(*tasks)
    print('All results:', results)


def translate_wwdc_videos(year: str, video_ids: list[str]):
    asyncio.run(translate_wwdc_videos_async(year, video_ids))