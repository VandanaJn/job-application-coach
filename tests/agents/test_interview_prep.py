from unittest.mock import MagicMock, patch
from graph.state import InterviewQuestion
from agents.interview_prep import build_interview_prep_agent, SYSTEM_PROMPT, InterviewQuestions

RESUME = "Software engineer with 5 years Python experience. Led backend systems at Acme."
JD = "Senior Python engineer to build scalable APIs and mentor junior developers."


def _sample_questions(n: int) -> list[InterviewQuestion]:
    return [
        InterviewQuestion(question=f"Question {i}?", category="technical")
        for i in range(n)
    ]


def _mock_agent(questions: list[InterviewQuestion]) -> MagicMock:
    agent = MagicMock()
    agent.invoke.return_value = {"structured_response": InterviewQuestions(questions=questions)}
    return agent


def _patch_factory(questions: list[InterviewQuestion]):
    """Patches ChatBedrockConverse + create_agent to return a stub agent.
    Returns (mock_create_agent, mock_agent) for assertions."""
    mock_agent = _mock_agent(questions)
    return patch("agents.interview_prep.ChatBedrockConverse"), patch(
        "agents.interview_prep.create_agent", return_value=mock_agent
    ), mock_agent


def test_build_returns_callable():
    p_model, p_create, _ = _patch_factory(_sample_questions(5))
    with p_model, p_create:
        run = build_interview_prep_agent()
        assert callable(run)


def test_run_returns_interview_questions():
    p_model, p_create, _ = _patch_factory(_sample_questions(5))
    with p_model, p_create:
        run = build_interview_prep_agent()
        result = run(RESUME, JD)
        assert isinstance(result, InterviewQuestions)


def test_run_passes_resume_and_jd_in_message():
    p_model, p_create, mock_agent = _patch_factory(_sample_questions(5))
    with p_model, p_create:
        run = build_interview_prep_agent()
        run(RESUME, JD)

    sent = mock_agent.invoke.call_args[0][0]
    user_text = sent["messages"][0]["content"]
    assert RESUME in user_text
    assert JD in user_text


def test_create_agent_called_with_system_prompt():
    p_model, p_create, _ = _patch_factory(_sample_questions(5))
    with p_model, p_create as mock_create:
        build_interview_prep_agent()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["system_prompt"] == SYSTEM_PROMPT


def test_create_agent_uses_tool_strategy_response_format():
    from langchain.agents.structured_output import ToolStrategy
    p_model, p_create, _ = _patch_factory(_sample_questions(5))
    with p_model, p_create as mock_create:
        build_interview_prep_agent()
        kwargs = mock_create.call_args.kwargs
        assert isinstance(kwargs["response_format"], ToolStrategy)


def test_create_agent_called_with_no_tools():
    p_model, p_create, _ = _patch_factory(_sample_questions(5))
    with p_model, p_create as mock_create:
        build_interview_prep_agent()
        kwargs = mock_create.call_args.kwargs
        assert kwargs["tools"] == []


def test_run_requests_configured_num_questions():
    p_model, p_create, mock_agent = _patch_factory(_sample_questions(3))
    with p_model, p_create:
        run = build_interview_prep_agent(num_questions=3)
        run(RESUME, JD)

    sent = mock_agent.invoke.call_args[0][0]
    user_text = sent["messages"][0]["content"]
    assert "3" in user_text


def test_default_num_questions_is_five():
    p_model, p_create, mock_agent = _patch_factory(_sample_questions(5))
    with p_model, p_create:
        run = build_interview_prep_agent()
        run(RESUME, JD)

    sent = mock_agent.invoke.call_args[0][0]
    user_text = sent["messages"][0]["content"]
    assert "5" in user_text


def test_returns_correct_question_count():
    questions = _sample_questions(5)
    p_model, p_create, _ = _patch_factory(questions)
    with p_model, p_create:
        run = build_interview_prep_agent()
        result = run(RESUME, JD)
        assert len(result.questions) == 5


def test_question_has_text_and_category():
    questions = [InterviewQuestion(question="Tell me about yourself?", category="behavioral")]
    p_model, p_create, _ = _patch_factory(questions)
    with p_model, p_create:
        run = build_interview_prep_agent(num_questions=1)
        result = run(RESUME, JD)
        assert result.questions[0].question == "Tell me about yourself?"
        assert result.questions[0].category == "behavioral"
