from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from agents.answer_coach import build_answer_coach_agent, SYSTEM_PROMPT, CoachingResponse

QUESTION = "Tell me about a time you led a complex project."
USER_MEMORY = "User tends to skip measurable outcomes. Strong on technical details."


def _mock_agent(response_text: str = "Great start! Can you add the outcome?", is_complete: bool = False) -> MagicMock:
    agent = MagicMock()
    agent.invoke.return_value = {
        "structured_response": CoachingResponse(response=response_text, is_complete=is_complete),
    }
    return agent


def _patch_factory(mock_agent: MagicMock):
    return patch("agents.answer_coach.ChatBedrockConverse"), patch(
        "agents.answer_coach.create_agent", return_value=mock_agent
    )


def _first_turn_messages(question: str, user_answer: str) -> list:
    return [HumanMessage(content=f"Question: {question}\n\nMy answer: {user_answer}")]


def test_build_returns_callable():
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        assert callable(run)


def test_run_returns_coaching_response():
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        messages = _first_turn_messages(QUESTION, "I once led a team of three.")
        result = run(messages)
        assert isinstance(result, CoachingResponse)


def test_response_text_is_passed_through():
    agent = _mock_agent("Can you quantify the impact?")
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        messages = _first_turn_messages(QUESTION, "I once led a team.")
        result = run(messages)
        assert result.response == "Can you quantify the impact?"


def test_create_agent_called_with_system_prompt():
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create as mock_create:
        build_answer_coach_agent()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["system_prompt"] == SYSTEM_PROMPT


def test_create_agent_uses_tool_strategy_response_format():
    from langchain.agents.structured_output import ToolStrategy
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create as mock_create:
        build_answer_coach_agent()
        kwargs = mock_create.call_args.kwargs
        assert isinstance(kwargs["response_format"], ToolStrategy)


def test_create_agent_called_with_no_tools():
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create as mock_create:
        build_answer_coach_agent()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["tools"] == []


def test_create_agent_includes_summarization_middleware():
    from langchain.agents.middleware import SummarizationMiddleware
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create as mock_create:
        build_answer_coach_agent()
        kwargs = mock_create.call_args.kwargs
        middleware = kwargs.get("middleware", [])
        assert any(isinstance(m, SummarizationMiddleware) for m in middleware)


def test_run_forwards_all_messages():
    mock_agent = _mock_agent()
    p_model, p_create = _patch_factory(mock_agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        messages = [
            HumanMessage(content=f"Question: {QUESTION}\n\nMy answer: I led a backend migration."),
            AIMessage(content="Good start! What was the outcome?"),
            HumanMessage(content="We reduced latency by 40%."),
        ]
        run(messages)

    sent = mock_agent.invoke.call_args[0][0]
    assert sent["messages"] == messages


def test_is_complete_false_by_default():
    agent = _mock_agent(is_complete=False)
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        result = run(_first_turn_messages(QUESTION, "I led a team."))
        assert result.is_complete is False


def test_is_complete_true_when_agent_says_so():
    agent = _mock_agent("Excellent STAR answer! Let's move on.", is_complete=True)
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create:
        run = build_answer_coach_agent()
        result = run(_first_turn_messages(QUESTION, "Detailed STAR answer here."))
        assert result.is_complete is True


def test_user_memory_appears_in_system_prompt():
    agent = _mock_agent()
    p_model, p_create = _patch_factory(agent)
    with p_model, p_create as mock_create:
        build_answer_coach_agent(user_memory=USER_MEMORY)
        kwargs = mock_create.call_args.kwargs
        assert USER_MEMORY in kwargs["system_prompt"]
        assert SYSTEM_PROMPT in kwargs["system_prompt"]
