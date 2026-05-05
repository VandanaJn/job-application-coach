from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from agents.answer_coach import create_agent, SYSTEM_PROMPT, CoachingResponse

QUESTION = "Tell me about a time you led a complex project."
RESUME = "Software engineer with 5 years Python experience. Led backend systems at Acme."
JD = "Senior Python engineer to build scalable APIs and mentor junior developers."
USER_MEMORY = "User tends to skip measurable outcomes. Strong on technical details."


def _make_mock_model(response_text: str = "Great start! Can you add the outcome?"):
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CoachingResponse(
        response=response_text,
        is_complete=False,
    )
    mock_model.with_structured_output.return_value = mock_structured
    return mock_model


def _first_turn_messages(question: str, user_answer: str) -> list:
    return [
        HumanMessage(content=f"Question: {question}\n\nMy answer: {user_answer}"),
    ]


def test_create_agent_returns_callable():
    model = _make_mock_model()
    agent = create_agent(model, [], SYSTEM_PROMPT)
    assert callable(agent)


def test_agent_returns_coaching_response():
    model = _make_mock_model()
    agent = create_agent(model, [], SYSTEM_PROMPT)
    messages = _first_turn_messages(QUESTION, "I once led a team of three.")
    result = agent(messages)
    assert isinstance(result, CoachingResponse)


def test_agent_response_has_text():
    model = _make_mock_model("Can you quantify the impact?")
    agent = create_agent(model, [], SYSTEM_PROMPT)
    messages = _first_turn_messages(QUESTION, "I once led a team.")
    result = agent(messages)
    assert result.response == "Can you quantify the impact?"


def test_agent_uses_system_prompt():
    model = _make_mock_model()
    agent = create_agent(model, [], SYSTEM_PROMPT)
    messages = _first_turn_messages(QUESTION, "I led a team.")
    agent(messages)

    call_args = model.with_structured_output.return_value.invoke.call_args
    sent_messages = call_args[0][0]
    assert sent_messages[0].content == SYSTEM_PROMPT


def test_agent_sends_all_messages_to_llm():
    model = _make_mock_model()
    agent = create_agent(model, [], SYSTEM_PROMPT)
    messages = [
        HumanMessage(content=f"Question: {QUESTION}\n\nMy answer: I led a backend migration."),
        AIMessage(content="Good start! What was the outcome?"),
        HumanMessage(content="We reduced latency by 40%."),
    ]
    agent(messages)

    call_args = model.with_structured_output.return_value.invoke.call_args
    sent_messages = call_args[0][0]
    # System + all 3 conversation messages
    assert len(sent_messages) == 4


def test_agent_uses_structured_output_schema():
    model = _make_mock_model()
    create_agent(model, [], SYSTEM_PROMPT)
    model.with_structured_output.assert_called_once_with(CoachingResponse)


def test_agent_is_complete_false_by_default():
    model = _make_mock_model()
    agent = create_agent(model, [], SYSTEM_PROMPT)
    messages = _first_turn_messages(QUESTION, "I led a team.")
    result = agent(messages)
    assert result.is_complete is False


def test_agent_is_complete_true_when_model_says_so():
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = CoachingResponse(
        response="Excellent STAR answer! Let's move to the next question.",
        is_complete=True,
    )
    mock_model.with_structured_output.return_value = mock_structured

    agent = create_agent(mock_model, [], SYSTEM_PROMPT)
    messages = _first_turn_messages(QUESTION, "Detailed STAR answer here.")
    result = agent(messages)
    assert result.is_complete is True


def test_agent_passes_user_memory_in_system_prompt():
    model = _make_mock_model()
    system_prompt_with_memory = SYSTEM_PROMPT + f"\n\nUser coaching notes: {USER_MEMORY}"
    agent = create_agent(model, [], system_prompt_with_memory)
    messages = _first_turn_messages(QUESTION, "I led a team.")
    agent(messages)

    call_args = model.with_structured_output.return_value.invoke.call_args
    system_msg = call_args[0][0][0]
    assert USER_MEMORY in system_msg.content


def test_build_answer_coach_agent_returns_callable():
    from unittest.mock import patch
    with patch("agents.answer_coach.ChatBedrockConverse"):
        from agents.answer_coach import build_answer_coach_agent
        agent = build_answer_coach_agent()
        assert callable(agent)
