"""stream_structured_reply — force a Pydantic model as a tool and stream
its first field. Mirrors the swift-learning-agent helper verbatim."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers.openai_tools import JsonOutputKeyToolsParser
from langchain_openai import ChatOpenAI


async def stream_structured_reply(
    llm: ChatOpenAI,
    response_model: type[BaseModel],
    messages: list[BaseMessage],
) -> dict[str, Any]:
    tool_name = response_model.__name__
    parser = JsonOutputKeyToolsParser(
        key_name=tool_name,
        first_tool_only=True,
    ).with_config({"run_name": "user_reply", "tags": ["user_reply"]})

    chain = llm.bind_tools([response_model], tool_choice=tool_name) | parser

    result: dict[str, Any] | None = None
    async for chunk in chain.astream(messages):
        result = chunk
    return result or {}
