from botocore.exceptions import ClientError
from langchain.agents.middleware import ModelRetryMiddleware

from agents.retry import bedrock_retry_middleware, is_transient_bedrock_error


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "boom"}},
        "InvokeModel",
    )


def test_throttling_is_transient():
    assert is_transient_bedrock_error(_client_error("ThrottlingException")) is True


def test_service_unavailable_is_transient():
    assert is_transient_bedrock_error(_client_error("ServiceUnavailableException")) is True


def test_internal_server_error_is_transient():
    assert is_transient_bedrock_error(_client_error("InternalServerException")) is True


def test_validation_error_is_not_transient():
    # Validation errors won't fix themselves on retry
    assert is_transient_bedrock_error(_client_error("ValidationException")) is False


def test_access_denied_is_not_transient():
    assert is_transient_bedrock_error(_client_error("AccessDeniedException")) is False


def test_non_client_error_is_not_transient():
    assert is_transient_bedrock_error(ValueError("something else")) is False


def test_factory_returns_model_retry_middleware():
    mw = bedrock_retry_middleware()
    assert isinstance(mw, ModelRetryMiddleware)


def test_factory_default_max_retries():
    mw = bedrock_retry_middleware()
    assert mw.max_retries == 3


def test_factory_custom_max_retries():
    mw = bedrock_retry_middleware(max_retries=5)
    assert mw.max_retries == 5


def test_factory_reraises_on_failure():
    # on_failure="error" so the orchestrator's exception handler can
    # convert exhausted retries into the session's error state.
    mw = bedrock_retry_middleware()
    assert mw.on_failure == "error"
