from langchain_core.messages import AIMessage, HumanMessage

from agents.usage import sum_usage


def _ai_with_usage(input_tokens: int, output_tokens: int) -> AIMessage:
    msg = AIMessage(content="ok")
    msg.usage_metadata = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
    return msg


def test_sum_usage_empty_list():
    assert sum_usage([]) == (0, 0)


def test_sum_usage_none():
    assert sum_usage(None) == (0, 0)


def test_sum_usage_single_message():
    assert sum_usage([_ai_with_usage(50, 20)]) == (50, 20)


def test_sum_usage_across_multiple_messages():
    messages = [_ai_with_usage(50, 20), _ai_with_usage(70, 30)]
    assert sum_usage(messages) == (120, 50)


def test_sum_usage_skips_messages_without_metadata():
    messages = [
        HumanMessage(content="hi"),  # no usage_metadata
        _ai_with_usage(40, 10),
        AIMessage(content="ok"),  # AIMessage but no usage attached
    ]
    assert sum_usage(messages) == (40, 10)


def test_sum_usage_treats_none_values_as_zero():
    msg = AIMessage(content="ok")
    msg.usage_metadata = {"input_tokens": None, "output_tokens": None}
    assert sum_usage([msg]) == (0, 0)
