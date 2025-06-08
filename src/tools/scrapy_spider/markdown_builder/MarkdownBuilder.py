

class MarkdownBuilder:
    def __init__(self):
        self.markdown_content = ""

    def add_heading(self, text, level=1):
        self.add_block(f"{'#' * level} {text}")

    def build_link(self, text, url):
        return f"[{text}]({url})"

    def add_paragraph(self, text):
        self.add_block(text)

    def add_list(self, items):
        for item in items:
            self.add_block(f"- {item}", newline='\n')

    def add_code_block(self, code, language=None):
        if language:
            self.add_block(f'```{language}\n{code}\n```')
        else:
            self.add_block(f'```\n{code}\n```')

    def add_block(self, block: str, newline='\n\n'):
        block = block.strip()
        if not block.endswith('\n'):
            block += newline
        if not self.markdown_content.endswith('\n'):
            self.markdown_content += newline
        self.markdown_content += block

    def add_text(self, text: str):
        self.markdown_content += text

    def get_markdown(self):
        return self.markdown_content.strip()