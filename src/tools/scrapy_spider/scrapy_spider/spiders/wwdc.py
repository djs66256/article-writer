import scrapy
import json

class WWDCSpider(scrapy.Spider):
    name = 'wwdc'
    base_url = 'https://developer.apple.com/videos/play'
    
    async def start(self):
        wwdc_year = getattr(self, 'wwdc', 2025)
        video_id = getattr(self, 'vid', None)

        if video_id is None:
            raise ValueError('Missing video ID')
        
        self.video_id = video_id
        start_url = f'{self.base_url}/wwdc{wwdc_year}/{video_id}'
        yield scrapy.Request(start_url, self.parse)

    def parse(self, response):
        data = {}
        # detail info
        detail_info = response.css('.details')
        if detail_info:
            title = detail_info.css('h1::text').get()
            description = detail_info.css('p::text').get()
            chapters = [{
                'start_time': chapter_item.css('::attr(data-start-time)').get(),
                'end_time': chapter_item.css('::attr(data-chapter-end-time)').get(),
                'length': chapter_item.css('::attr(data-chapter-lenght)').get(),
                'index': chapter_item.css('::attr(data-chapter-index)').get(),
                'title': chapter_item.css('a::text').get(),
            } for chapter_item in detail_info.css(".chapter-list").css(".chapter-item")]
            data["detail"] = {
                "title": title,
                "description": description,
                "chapters": chapters
            }
        
        related_videos_info = detail_info.css(".links .video a")
        if related_videos_info:
            related_videos = [{
                'title': related_video_info.css('::text').get(),
                'url': response.urljoin(related_video_info.css('::attr(href)').get())
            } for related_video_info in related_videos_info]
            data["related_videos"] = related_videos

        transcript = response.css('.transcript')
        if transcript:
            transcript_items = [{
                'start_time': transcript_item.css('::attr(data-start)').get()
                    or transcript_item.css('::attr(data-start-time)').get(),
                'end_time': transcript_item.css('::attr(data-end-time)').get(),
                'text': transcript_item.css('::text').get()
            } for transcript_item in transcript.css(".sentence")]
            data["transcript"] = transcript_items

        sample_codes = response.css('.sample-code')
        if sample_codes:
            sample_codes_items = [{
                'start_time': sample_code.css('::attr(data-start-time)').get(),
                'description': sample_code.css('a::text').get(),
                'code': ''.join(sample_code.css('code ::text').getall())
            } for sample_code in sample_codes.css(".sample-code-main-container")]
            data["sample_codes"] = sample_codes_items

        print(json.dumps(data, indent=2, ensure_ascii=False))
        yield data

        return
        # 提取WWDC视频链接
        for video in response.css('section.video'):
            yield {
                'title': video.css('h3::text').get().strip(),
                'url': response.urljoin(video.css('a::attr(href)').get()),
                'description': video.css('p::text').get().strip(),
                'date': video.css('time::attr(datetime)').get(),
                'video_id': self.video_id
            }
        
        # 跟进分页链接
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)