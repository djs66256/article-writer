from os import path, remove
import subprocess
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
if __name__ == "__main__":
    from scrapy_spider.spiders.wwdc import WWDCSpider
    from markdown_builder import build_wwdc_markdown
else:
    from .scrapy_spider.spiders.wwdc import WWDCSpider
    from .markdown_builder import build_wwdc_markdown

class WWDCTask:
    CURRENT_DIR = path.dirname(path.abspath(__file__))
    OUTPUT_BASE_DIR = path.join(CURRENT_DIR, "output", "wwdc")
    
    def __init__(self, year: str, video_id: str):
        self.year = year
        self.video_id = video_id

    @property
    def crawl_file_path(self) -> str:
        return path.join(self.OUTPUT_BASE_DIR, self.year, f"{self.video_id}.jsonl")
    
    @property
    def markdown_file_path(self) -> str:
        return path.join(self.OUTPUT_BASE_DIR, self.year, f"{self.video_id}.md")
    
    def remove_caches(self):
        if path.exists(self.crawl_file_path):
            try:
                remove(self.crawl_file_path)
            except Exception as e:
                print(f"Error removing file {self.crawl_file_path}: {e}")
        if path.exists(self.markdown_file_path):
            try:
                remove(self.markdown_file_path)
            except Exception as e:
                print(f"Error removing file {self.markdown_file_path}: {e}")

    def crawl(self):

        command = [
            "scrapy", "crawl", "wwdc",
            "-a", f"wwdc={self.year}",
            "-a", f"vid={self.video_id}",
            "-o", self.crawl_file_path,
            "--loglevel", "ERROR"
        ]
        res = subprocess.run(
            command, 
            cwd=self.CURRENT_DIR, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, 
            text=True)
        if res.returncode != 0:
            raise res.stderr
        return
        settings = get_project_settings()
        settings.set('LOG_LEVEL', 'WARNING')
        settings.set('FEEDS', {
            self.crawl_file_path: {  # 输出文件路径
                'format': 'jsonlines',  # 输出格式（jsonlines, json, csv 等）
                'encoding': 'utf8',     # 编码方式
                'overwrite': True,      # 是否覆盖已有文件
                'indent': 0             # JSON 缩进（可选）
            }
        })
        # settings.set('FEED_FORMAT', 'jsonlines')
        # settings.set('FEED_URI', self.crawl_file_path)
        print(f"Crawling {self.year} {self.video_id}, writing to {self.crawl_file_path}")
        process = CrawlerProcess(settings)
        process.crawl(WWDCSpider, wwdc=self.year, vid=self.video_id)
        process.start()

    def _read_crawled_data(self) -> dict|None:
        with open(self.crawl_file_path, 'r', encoding='utf-8') as file:
            data = file.read().strip()
            if data:
                try:
                    return json.loads(data)
                except:
                    return None
        return None

    def _write_markdown(self, markdown: str):
        with open(self.markdown_file_path, 'w', encoding='utf-8') as file:
            file.write(markdown)

    def generate_markdown(self) -> str|None:
        if data := self._read_crawled_data():
            markdown = build_wwdc_markdown(data)
            self._write_markdown(markdown)
            return markdown
        return None
    
    def run(self) -> str | None:
        print(f"Starting WWDC task for year {self.year} and video ID {self.video_id}...")
        self.remove_caches()
        self.crawl()
        markdown = self.generate_markdown()
        print(f"Markdown generated at {self.markdown_file_path}")
        return markdown


if __name__ == "__main__":
    # Example usage
    task = WWDCTask(year="2024", video_id="10217")
    # print(task.OUTPUT_BASE_DIR)
    task.remove_caches()
    task.crawl()
    task.generate_markdown()
    # Further processing can be done here, such as reading crawled data and generating markdown.