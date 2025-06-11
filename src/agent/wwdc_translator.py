import asyncio
import aiofiles
import os
from enum import Enum
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
    podcast_script: str | None = Field(None, description="The podcast script.")

class Configuration(BaseModel):
    """Configurable parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """
    year: str = Field(..., description="The year of the WWDC video.")
    video_id: str = Field(..., description="The ID of the WWDC video.")
    use_cache: bool = Field(True, description="Whether to use cache.")

    base_url: str = Field(..., description="The base URL of the OpenAI API.")
    model: str = Field(..., description="The model to use.")
    api_key: str = Field(..., description="The API key to use.")

class CacheType(Enum):
    ORIGINAL_MARKDOWN = "original_markdown"
    TRANSLATED_MARKDOWN = "translated_markdown"
    REWRITED_MARKDOWN = "rewrited_markdown"
    PODCAST_SCRIPT = "podcast_script"

    def file_postfix(self) -> str:
        if self == CacheType.ORIGINAL_MARKDOWN:
            return ".md"
        elif self == CacheType.TRANSLATED_MARKDOWN:
            return "_zh.md"
        elif self == CacheType.REWRITED_MARKDOWN:
            return "_zh_rewrite.md"
        elif self == CacheType.PODCAST_SCRIPT:
            return "_podcast.json"

OUTPUT_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'output', 'wwdc')

async def get_cache(year: str, video_id: str, type: CacheType) -> str | None:
    path = os.path.join(OUTPUT_BASE_DIR, year, f'{video_id}{type.file_postfix()}')
    if os.path.exists(path):
        async with aiofiles.open(path, 'r') as f:
            if content := await f.read():
                return content
    return None

async def save_cache(year: str, video_id: str, type: CacheType, content: str):
    # ensure output dir exists
    outputdir = os.path.join(OUTPUT_BASE_DIR, year)
    if not os.path.exists(outputdir):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, os.makedirs, outputdir)
    # save cache
    path = os.path.join(OUTPUT_BASE_DIR, year, f'{video_id}{type.file_postfix()}')
    async with aiofiles.open(path, 'w') as f:
        await f.write(content)

def get_llm_model(config: Configuration) -> ChatOpenAI:
    return ChatOpenAI(
        model=config['configurable']["model"],
        base_url=config['configurable']["base_url"],
        api_key=config['configurable']["api_key"]
    )

# Nodes:

async def crawl_wwdc_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Generate markdown content from WWDC video data."""

    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    if config['configurable']["use_cache"]:
        if markdown := await get_cache(year, video_id, CacheType.ORIGINAL_MARKDOWN):
            return {
                "markdown": markdown
            }

    task = WWDCTask(year=year, video_id=video_id)
    if markdown := await asyncio.to_thread(lambda: task.run()):
        await save_cache(year, video_id, CacheType.ORIGINAL_MARKDOWN, markdown)
        return {
            "markdown": markdown
        }
    else:
        raise ValueError("No markdown content available for translation.")

async def translate_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Translate markdown content."""
    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]

    if config['configurable']["use_cache"]:
        if translated_markdown := await get_cache(year, video_id, CacheType.TRANSLATED_MARKDOWN):
            return {
                **state.model_dump(),
                "translated_markdown": translated_markdown
            }

    prompt = await get_prompt(AgentType.WWDC_TRANSLATOR)
    model = get_llm_model(config)
    agent = create_react_agent(model=model, tools=[], prompt=prompt)
    
    if markdown := state.markdown:
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": markdown
            }]
        })
        translated_markdown = response["messages"][-1].content
        await save_cache(year, video_id, CacheType.TRANSLATED_MARKDOWN, translated_markdown)
        return {
            **state.model_dump(),
            "translated_markdown": translated_markdown
        }
    else:
        raise ValueError("No markdown content available for translation.")

async def rewrite_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Rewrite markdown content."""
    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    if config['configurable']["use_cache"]:
        if rewrited_markdown := await get_cache(year, video_id, CacheType.REWRITED_MARKDOWN):
            return {
                **state.model_dump(),
                "rewrited_markdown": rewrited_markdown
            }

    prompt = await get_prompt(AgentType.WRITER)
    model = get_llm_model(config)
    agent = create_react_agent(model=model, tools=[], prompt=prompt)

    if translated_markdown := state.translated_markdown:
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": translated_markdown
            }]
        })
        rewrited_markdown = response["messages"][-1].content
        await save_cache(year, video_id, CacheType.REWRITED_MARKDOWN, rewrited_markdown)
        return {
            **state.model_dump(),
            "rewrited_markdown": rewrited_markdown
        }
    else:
        raise ValueError("No markdown content available for translation.")

async def write_podcast_script(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Write podcast script."""
    year=config['configurable']["year"]
    video_id=config['configurable']["video_id"]
    if config['configurable']["use_cache"]:
        if podcast_script := await get_cache(year, video_id, CacheType.PODCAST_SCRIPT):
            return {
                **state.model_dump(),
                "podcast_script": podcast_script
            }
    prompt = await get_prompt(AgentType.PODCAST_SCRIPT_WRITER)
    model = get_llm_model(config)
    agent = create_react_agent(model=model, tools=[], prompt=prompt)
    if markdown := state.translated_markdown:
        response = await agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": markdown
            }]
        })
        podcast_script = response["messages"][-1].content
        await save_cache(year, video_id, CacheType.PODCAST_SCRIPT, podcast_script)
        return {
            **state.model_dump(),
            "podcast_script": podcast_script
        }
    else:
        raise ValueError("No markdown content available for translation.")

# async def save_markdown(state: State, config: RunnableConfig):
#     currentdir = os.path.dirname(os.path.abspath(__file__))
#     year=config['configurable']["year"]
#     video_id=config['configurable']["video_id"]
#     outputdir = os.path.join(currentdir, '..', '..', 'output', 'wwdc', year)
#     if not os.path.exists(outputdir):
#         loop = asyncio.get_running_loop()
#         await loop.run_in_executor(None, os.makedirs, outputdir)
#     async with aiofiles.open(os.path.join(outputdir, f'{video_id}.md'), 'w') as f:
#         await f.write(state.markdown)

#     async with aiofiles.open(os.path.join(outputdir, f'{video_id}_zh.md'), 'w') as f:
#         await f.write(state.translated_markdown)

#     async with aiofiles.open(os.path.join(outputdir, f'{video_id}_zh_rewrite.md'), 'w') as f:
#         await f.write(state.rewrited_markdown)


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node(crawl_wwdc_markdown)
    .add_node(translate_markdown)
    .add_node(rewrite_markdown)
    .add_node(write_podcast_script)
    .add_edge("__start__", "crawl_wwdc_markdown")
    .add_edge("crawl_wwdc_markdown", "translate_markdown")
    .add_edge("translate_markdown", "rewrite_markdown")
    .add_edge("rewrite_markdown", "__end__")
    # .add_edge("write_podcast_script", "__end__")
    .compile(name="WWDC Translator Graph")
)
