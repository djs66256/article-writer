import os
import subprocess
import json

year = "2025"

def craw_videos():
    year = "2025"
    base_path = os.path.dirname(os.path.abspath(__file__))
    scrapy_path = os.path.join(base_path, "src/tools/scrapy_spider")
    output_path = os.path.join(base_path, f"output/wwdc/{year}/videos.jsonl")
    if os.path.exists(output_path):
        os.remove(output_path)
    subprocess.run([
            "scrapy", "crawl", "wwdc_video_links",
            "-a", f"wwdc={year}", 
            "--loglevel=ERROR",
            "-o", output_path
        ], 
        cwd=scrapy_path)

    try:
        with open(output_path, "r") as f:
            data = f.readlines()[-1].strip()
            json_data = json.loads(data)
            videos = json_data["videos"]
            return videos
    except:
        return None

if __name__ == "__main__":
    from src.bot.wwdc_translator_bot import translate_wwdc_videos
    from dotenv import load_dotenv
    load_dotenv()
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    if videos := craw_videos():
        translate_wwdc_videos(videos, max_concurrent=10)

    # translate_wwdc_videos("2025", [
    #     "102",
        # https://developer.apple.com/cn/videos/play/wwdc2025/252
        # https://developer.apple.com/cn/videos/play/wwdc2025/265
        # ])