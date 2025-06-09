import asyncio
import aiofiles
import os
from typing import Any, Dict, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.prompts import get_prompt, AgentType
from src.tools.scrapy_spider.wwdc_task import WWDCTask

class State(BaseModel):
    """
    State for the WWDC translator agent.
    """
    markdown: str | None = Field(None, description="The generated markdown content from the video.")
    translated_markdown: str | None = Field(None, description="The translated markdown content.")
    rewrited_markdown: str | None = Field(None, description="The rewritten markdown content.")

class Configuration(TypedDict):
    """Configurable parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    year: str
    video_id: str
    use_cache: bool = True

    base_url: str
    model: str
    api_key: str

OUTPUT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'output', 'wwdc')
def _get_markdown_path(year: str, video_id: str) -> str:
    return os.path.join(OUTPUT_BASE_DIR, year, f'{video_id}.md')

async def _get_markdown_cache(year: str, video_id: str) -> str | None:
    markdown_path = _get_markdown_path(year, video_id)
    if os.path.exists(markdown_path):
        async with aiofiles.open(markdown_path, 'r') as f:
            if markdown := await f.read():
                return markdown
    return None

def _get_translated_markdown_path(year: str, video_id: str) -> str:
    return os.path.join(OUTPUT_BASE_DIR, year, f'{video_id}_zh.md')

async def _get_translated_markdown_cache(year: str, video_id: str) -> str | None:
    markdown_path = _get_translated_markdown_path(year, video_id)
    if os.path.exists(markdown_path):
        async with aiofiles.open(markdown_path, 'r') as f:
            if markdown := await f.read():
                return markdown
    return None

def _get_rewrited_markdown_path(year: str, video_id: str) -> str:
    return os.path.join(OUTPUT_BASE_DIR, year, f'{video_id}_zh_rewrite.md')

async def _get_rewrited_markdown_cache(year: str, video_id: str) -> str | None:
    markdown_path = _get_rewrited_markdown_path(year, video_id)
    if os.path.exists(markdown_path):
        async with aiofiles.open(markdown_path, 'r') as f:
            if markdown := await f.read():
                return markdown
    return None

async def crawl_wwdc_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Generate markdown content from WWDC video data."""

    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    if config['configurable']["use_cache"]:
        if markdown := await _get_markdown_cache(year, video_id):
            return {
                "markdown": markdown
            }

    task = WWDCTask(
        year=year, 
        video_id=video_id
        )
    markdown = await asyncio.to_thread(lambda: task.run())
    # markdown = await loop.run_in_executor(None, task.run)  # Clean up caches asynchronously
    return {
        "markdown": markdown
    }

async def translate_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Translate markdown content."""
    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    if config['configurable']["use_cache"]:
        if translated_markdown := await _get_translated_markdown_cache(year, video_id):
            return {
                "markdown": state.markdown,
                "translated_markdown": translated_markdown
            }

    prompt = await get_prompt(AgentType.WWDC_TRANSLATOR)
    model = ChatOpenAI(
        model=config['configurable']["model"],
        base_url=config['configurable']["base_url"],
        api_key=config['configurable']["api_key"]
    )

    agent = create_react_agent(model=model, tools=[], prompt=prompt)
    
    if markdown := state.markdown:
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": markdown
            }]
        })
        translated_markdown = response["messages"][-1].content
        return {
            "markdown": markdown,
            "translated_markdown": translated_markdown
        }
    else:
        raise ValueError("No markdown content available for translation.")

async def rewrite_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Rewrite markdown content."""
    prompt = await get_prompt(AgentType.WRITER)
    model = ChatOpenAI(
        model=config['configurable']["model"],
        base_url=config['configurable']["base_url"],
        api_key=config['configurable']["api_key"]
    )
    agent = create_react_agent(model=model, tools=[], prompt=prompt)

    if translated_markdown := state.translated_markdown:
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": translated_markdown
            }]
        })
        rewrited_markdown = response["messages"][-1].content
        return {
            "markdown": state.markdown,
            "translated_markdown": translated_markdown,
            "rewrited_markdown": rewrited_markdown
        }
    else:
        raise ValueError("No markdown content available for translation.")

async def save_markdown(state: State, config: RunnableConfig):
    currentdir = os.path.dirname(os.path.abspath(__file__))
    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    outputdir = os.path.join(currentdir, '..', '..', 'output', 'wwdc', year)
    if not os.path.exists(outputdir):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, os.makedirs, outputdir)
    async with aiofiles.open(os.path.join(outputdir, f'{video_id}.md'), 'w') as f:
        await f.write(state.markdown)

    async with aiofiles.open(os.path.join(outputdir, f'{video_id}_zh.md'), 'w') as f:
        await f.write(state.translated_markdown)

    async with aiofiles.open(os.path.join(outputdir, f'{video_id}_zh_rewrite.md'), 'w') as f:
        await f.write(state.rewrited_markdown)


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node(crawl_wwdc_markdown)
    .add_node(translate_markdown)
    .add_node(rewrite_markdown)
    .add_node(save_markdown)
    .add_edge("__start__", "crawl_wwdc_markdown")
    .add_edge("crawl_wwdc_markdown", "translate_markdown")
    .add_edge("translate_markdown", "rewrite_markdown")
    .add_edge("rewrite_markdown", "save_markdown")
    .add_edge("save_markdown", "__end__")
    .compile(name="WWDC Translator Graph")
)

