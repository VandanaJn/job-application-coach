"""Bedrock-aware retry middleware for LangChain agents.

Bedrock throttles aggressively under sustained load and surfaces a few
transient server-side failure codes that resolve on retry. Anything
else (validation errors, missing model access) won't fix itself and is
left for the caller to handle.
"""
from botocore.exceptions import ClientError
from langchain.agents.middleware import ModelRetryMiddleware

# Codes that Bedrock returns for transient failures worth retrying.
# Validation / access errors are intentionally excluded — they won't
# succeed on a second attempt.
_TRANSIENT_BEDROCK_CODES = frozenset({
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
    "ModelStreamErrorException",
    "ModelErrorException",
    "InternalServerException",
})


def is_transient_bedrock_error(exc: Exception) -> bool:
    if not isinstance(exc, ClientError):
        return False
    code = exc.response.get("Error", {}).get("Code", "")
    return code in _TRANSIENT_BEDROCK_CODES


def bedrock_retry_middleware(max_retries: int = 3) -> ModelRetryMiddleware:
    return ModelRetryMiddleware(
        max_retries=max_retries,
        retry_on=is_transient_bedrock_error,
        backoff_factor=2.0,
        initial_delay=1.0,
        max_delay=20.0,
        on_failure="error",
    )
