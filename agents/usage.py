"""Helpers for extracting Bedrock token usage from LangChain agent runs."""


def sum_usage(messages: list) -> tuple[int, int]:
    """Sum input/output tokens across all AIMessages in an agent run."""
    total_in = 0
    total_out = 0
    for m in messages or []:
        meta = getattr(m, "usage_metadata", None) or {}
        total_in += meta.get("input_tokens", 0) or 0
        total_out += meta.get("output_tokens", 0) or 0
    return total_in, total_out
