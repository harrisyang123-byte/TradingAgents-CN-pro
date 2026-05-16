"""Helpers for structured output binding with graceful fallback.

Allows agents to use Pydantic models for structured output when the LLM
supports it, with automatic fallback to free-text when not supported.
"""

from typing import Any, TypeVar
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

T = TypeVar("T", bound=BaseModel)


def bind_structured(llm: ChatOpenAI, schema: type[T]) -> ChatOpenAI:
    """Bind a Pydantic schema as structured output on the LLM.

    This uses tool_use under the hood — the schema is formatted as a tool
    that the LLM can call to produce structured output.

    Args:
        llm: The ChatOpenAI instance to bind with.
        schema: A Pydantic BaseModel subclass defining the output structure.

    Returns:
        A new ChatOpenAI instance with the schema bound.
    """
    return llm.with_structured_output(schema, method="function_calling")


def invoke_structured_or_freetext(
    llm: ChatOpenAI,
    messages: list,
    schema: type[T],
) -> dict[str, Any] | str:
    """Try structured output; fall back to free-text if unsupported.

    Attempts to invoke the LLM with structured output binding. If the LLM
    does not support tool_use / function_calling, catches the error and
    falls back to a plain text invocation.

    Args:
        llm: The ChatOpenAI instance.
        messages: The message history to send.
        schema: The Pydantic schema to attempt binding with.

    Returns:
        Parsed schema dict on success, or raw text string on fallback.
    """
    try:
        bound = bind_structured(llm, schema)
        result = bound.invoke(messages)
        if isinstance(result, BaseModel):
            return result.model_dump()
        return result
    except (NotImplementedError, AttributeError, TypeError):
        return llm.invoke(messages).content
