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

class Configuration(TypedDict):
    """Configurable parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    year: str
    video_id: str

    base_url: str
    model: str
    api_key: str

async def crawl_wwdc_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Generate markdown content from WWDC video data."""
    task = WWDCTask(
        year=config['configurable']["year"], 
        video_id=config['configurable']["video_id"]
        )
    markdown = await asyncio.to_thread(lambda: task.run())
    # markdown = await loop.run_in_executor(None, task.run)  # Clean up caches asynchronously
    return {
        "markdown": markdown
    }

async def translate_markdown(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Translate markdown content."""
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


graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node(crawl_wwdc_markdown)
    .add_node(translate_markdown)
    .add_node(save_markdown)
    .add_edge("__start__", "crawl_wwdc_markdown")
    .add_edge("crawl_wwdc_markdown", "translate_markdown")
    .add_edge("translate_markdown", "save_markdown")
    .add_edge("save_markdown", "__end__")
    .compile(name="WWDC Translator Graph")
)

