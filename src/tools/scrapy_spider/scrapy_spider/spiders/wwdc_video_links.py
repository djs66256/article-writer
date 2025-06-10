from typing import override
import scrapy
import json

class WWDCVideoLinksSpider(scrapy.Spider):
    name = "wwdc_video_links"
    base_url = "https://developer.apple.com/cn/videos"

    async def start(self):
        wwdc_year = getattr(self, 'wwdc', 2025)
        url = f'{self.base_url}/wwdc{wwdc_year}'
        print(url)
        yield scrapy.Request(url, self.parse)


    def parse(self, response):
        list = response.css(".main-content .vc-collection a")
        data = [
            {
                'title': item.css('.vc-card__title::text').get(),
                'title-en': item.css('.vc-card__title::attr(data-filter-title-en)').get(),
                'description': item.css('.vc-card__keywords::attr(data-filter-description)').get(),
                'description-en': item.css('.vc-card__keywords::attr(data-filter-description-en)').get(),
                'platform': item.css('.vc-card__keywords::attr(data-filter-platform)').get(),
                'url': response.urljoin(item.css('::attr(href)').get()),
                'category': item.css('::attr(data-category)').get(),
                'image': item.css('img::attr(src)').get(),
                'duration': item.css('.vc-card__duration::text').get(),
            }
            for item in list
        ]
        yield {'videos': data}