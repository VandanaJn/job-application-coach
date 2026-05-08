from unittest.mock import MagicMock, patch
from graph.state import InterviewQuestion
from agents.interview_prep import InterviewPrepResult

INITIAL_STATE = {
    "session_id": "sess-1",
    "user_id": "default",
    "job_id": "job-1",
    "resume_text": "Software engineer with 5 years Python experience.",
    "job_description": "Senior Python engineer to build scalable APIs.",
    "num_questions": 3,
    "questions": None,
    "status": "running",
    "error": None,
}

MOCK_QUESTIONS = [InterviewQuestion(question=f"Q{i}?", category="technical") for i in range(3)]


def _mock_agent_builder(questions=MOCK_QUESTIONS, input_tokens=100, output_tokens=50):
    result = InterviewPrepResult(
        questions=questions,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    mock_agent = MagicMock(return_value=result)
    return MagicMock(return_value=mock_agent)


def test_graph_completes_successfully():
    with patch("graph.orchestrator.build_interview_prep_agent", _mock_agent_builder()):
        from graph.orchestrator import build_graph
        result = build_graph().invoke(INITIAL_STATE)
    assert result["status"] == "completed"


def test_graph_returns_questions():
    with patch("graph.orchestrator.build_interview_prep_agent", _mock_agent_builder()):
        from graph.orchestrator import build_graph
        result = build_graph().invoke(INITIAL_STATE)
    assert result["questions"] == MOCK_QUESTIONS


def test_graph_returns_token_usage():
    with patch("graph.orchestrator.build_interview_prep_agent", _mock_agent_builder(input_tokens=120, output_tokens=80)):
        from graph.orchestrator import build_graph
        result = build_graph().invoke(INITIAL_STATE)
    assert result["input_tokens"] == 120
    assert result["output_tokens"] == 80


def test_graph_passes_num_questions_to_agent():
    mock_builder = _mock_agent_builder()
    with patch("graph.orchestrator.build_interview_prep_agent", mock_builder):
        from graph.orchestrator import build_graph
        build_graph().invoke(INITIAL_STATE)
    mock_builder.assert_called_once_with(3)


def test_graph_passes_resume_and_jd_to_agent():
    mock_builder = _mock_agent_builder()
    with patch("graph.orchestrator.build_interview_prep_agent", mock_builder):
        from graph.orchestrator import build_graph
        build_graph().invoke(INITIAL_STATE)
    mock_agent = mock_builder.return_value
    mock_agent.assert_called_once_with(
        INITIAL_STATE["resume_text"],
        INITIAL_STATE["job_description"],
    )


def test_graph_sets_error_status_on_failure():
    mock_builder = MagicMock(side_effect=Exception("Bedrock timeout"))
    with patch("graph.orchestrator.build_interview_prep_agent", mock_builder):
        from graph.orchestrator import build_graph
        result = build_graph().invoke(INITIAL_STATE)
    assert result["status"] == "error"
    assert "Bedrock timeout" in result["error"]
