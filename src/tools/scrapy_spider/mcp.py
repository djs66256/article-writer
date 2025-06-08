from mcp.server.fastmcp import FastMCP
from typing import Annotated
from pydantic import Field

mcp = FastMCP("scrapy_spider")

@mcp.tool
def fetch_wwdc_video_detail(
    video_id: Annotated[str, Field(description="The ID of the WWDC video")],
    year: Annotated[str, Field(description="The year of the WWDC video")] = "2025",
    ) -> str:
    """Fetches the WWDC video detail information."""

@mcp.tool
def fetch_apple_document(
    document_urls: Annotated[list[str], Field(description="List of Apple document URLs")],
    ):
    """Fetches the Apple document information."""


if __name__ == "__main__":
    mcp.run(transport='stdio')