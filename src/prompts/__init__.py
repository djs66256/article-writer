import os
import aiofiles
from enum import Enum

class AgentType(Enum):
    WWDC_TRANSLATOR = "wwdc_translator"
    WRITER = "writer"
    PODCAST_SCRIPT_WRITER = "podcast_script_writer"


async def get_prompt(agent_type: AgentType, **argv) -> str:
    if agent_type == AgentType.WWDC_TRANSLATOR \
        or agent_type == AgentType.WRITER \
        or agent_type == AgentType.PODCAST_SCRIPT_WRITER:
        curdir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(curdir, f'{agent_type.value}.md')
        async with aiofiles.open(prompt_path, 'r', encoding='utf-8') as file:
            prompt = await file.read()
            return prompt
    else:
        return "You a helpful assistant."