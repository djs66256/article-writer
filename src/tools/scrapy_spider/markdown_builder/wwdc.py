from typing import Any, Dict, List, Union
from math import inf
from .MarkdownBuilder import MarkdownBuilder

def _parse_float(value: str, default: float = 0) -> float:
    """
    Parses a string to an integer, returning a default value if parsing fails.
    """
    try:
        return float(value)
    except:
        return default

def build_wwdc_markdown(input: Dict[str, Any]):
    """
    Builds a markdown string from the given input data.
    
    ```markdown
    # {title}
    {description}
    # Transcript
    {transcript + code}
    # Related videos
    {related_videos}
    # Documents
    {documents}
    ```
    """

    mdbuilder = MarkdownBuilder()

    # title and description
    if detail := input.get("detail"):
        title = detail.get('title', '')
        description = detail.get('description', '')
        mdbuilder.add_heading(title)
        mdbuilder.add_paragraph(description)

    # transcript and code
    if transcript := input["transcript"]:
        mdbuilder.add_heading('Transcript')
        codes = input.get("sample_codes", [])
        def find_code_in_range(start_time: float, end_time: float) -> map|None:
            for code in codes:
                time = _parse_float(code['start_time'])
                if time >= start_time and time < end_time:
                    return code
            return None
        
        def chapter_in(time: float) -> map|None:
            for chapter in input.get("detail", {}).get("chapters", []):
                chapter_start = _parse_float(chapter['start_time'])
                chapter_end = _parse_float(chapter.get('end_time', inf))
                if time >= chapter_start and time <= chapter_end:
                    # The time range is within the chapter
                    return chapter
            return None
        
        prev_time = 0
        chapter_index = -1
        for sentence in transcript:
            time = _parse_float(sentence['start_time'])
            if chapter := chapter_in(time):
                if index := chapter.get('index', None):
                    if index != chapter_index:
                        chapter_index = index
                        mdbuilder.add_heading(chapter.get('title', ''), level=2)
            if code := find_code_in_range(prev_time, time):
                if description := code.get('description', None):
                    mdbuilder.add_block(f'> {description}')
                if codeblock := code.get('code', None):
                    mdbuilder.add_code_block(codeblock, language=code.get('language', None))
            mdbuilder.add_text(sentence.get('text', ''))
            prev_time = time

        if code := find_code_in_range(prev_time, inf):
            mdbuilder.add_code_block(code.get('code', None), language=code.get('language', None))

    # related videos
    if related_videos := input.get("related_videos", []):
        mdbuilder.add_heading('Related Videos')
        for video in related_videos:
            title = video.get('title', '')
            url = video.get('url', '')
            mdbuilder.add_block(mdbuilder.build_link(title, url), newline='\n')

    # documents
    if documents := input.get("documents", []):
        mdbuilder.add_heading('Documents')
        for document in documents:
            title = document.get('title', '')
            url = document.get('url', '')
            mdbuilder.add_block(mdbuilder.build_link(title, url), newline='\n')

    return mdbuilder.get_markdown()


if __name__ == '__main__':
    import json
    with open('../output/wwdc/2024/10217.jsonl', 'r') as f:
        data = f.read().split('\n')[0]
        wwdc = json.loads(data)

        # print(wwdc)
        md = build_wwdc_markdown(wwdc)
        print(md)