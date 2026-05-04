from unittest.mock import MagicMock, patch
from graph.state import InterviewQuestion
from agents.interview_prep import create_agent, SYSTEM_PROMPT, InterviewQuestions

RESUME = "Software engineer with 5 years Python experience. Led backend systems at Acme."
JD = "Senior Python engineer to build scalable APIs and mentor junior developers."


def _make_mock_model(questions: list[InterviewQuestion]):
    mock_model = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = InterviewQuestions(questions=questions)
    mock_model.with_structured_output.return_value = mock_structured
    return mock_model


def _sample_questions(n: int) -> list[InterviewQuestion]:
    return [
        InterviewQuestion(question=f"Question {i}?", category="technical")
        for i in range(n)
    ]


def test_create_agent_returns_callable():
    model = _make_mock_model(_sample_questions(5))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    assert callable(agent)


def test_agent_returns_interview_questions():
    model = _make_mock_model(_sample_questions(5))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    result = agent(RESUME, JD)
    assert isinstance(result, InterviewQuestions)


def test_agent_calls_llm_with_resume_and_jd():
    model = _make_mock_model(_sample_questions(5))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    agent(RESUME, JD)

    call_args = model.with_structured_output.return_value.invoke.call_args
    messages_text = " ".join(m.content for m in call_args[0][0])
    assert RESUME in messages_text
    assert JD in messages_text


def test_agent_uses_system_prompt():
    model = _make_mock_model(_sample_questions(5))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    agent(RESUME, JD)

    call_args = model.with_structured_output.return_value.invoke.call_args
    first_message = call_args[0][0][0]
    assert first_message.content == SYSTEM_PROMPT


def test_agent_requests_correct_num_questions():
    model = _make_mock_model(_sample_questions(3))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    agent(RESUME, JD, num_questions=3)

    call_args = model.with_structured_output.return_value.invoke.call_args
    messages_text = " ".join(m.content for m in call_args[0][0])
    assert "3" in messages_text


def test_agent_uses_structured_output_schema():
    model = _make_mock_model(_sample_questions(5))
    create_agent(model, [], SYSTEM_PROMPT)
    model.with_structured_output.assert_called_once_with(InterviewQuestions)


def test_default_num_questions_is_five():
    model = _make_mock_model(_sample_questions(5))
    agent = create_agent(model, [], SYSTEM_PROMPT)
    agent(RESUME, JD)

    call_args = model.with_structured_output.return_value.invoke.call_args
    messages_text = " ".join(m.content for m in call_args[0][0])
    assert "5" in messages_text


def test_agent_returns_correct_question_count():
    questions = _sample_questions(5)
    model = _make_mock_model(questions)
    agent = create_agent(model, [], SYSTEM_PROMPT)
    result = agent(RESUME, JD)
    assert len(result.questions) == 5


def test_question_has_text_and_category():
    questions = [InterviewQuestion(question="Tell me about yourself?", category="behavioral")]
    model = _make_mock_model(questions)
    agent = create_agent(model, [], SYSTEM_PROMPT)
    result = agent(RESUME, JD, num_questions=1)
    assert result.questions[0].question == "Tell me about yourself?"
    assert result.questions[0].category == "behavioral"
