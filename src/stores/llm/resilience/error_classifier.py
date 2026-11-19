
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ErrorType(Enum):
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    MODEL_NOT_FOUND = "model_not_found"
    BAD_REQUEST = "bad_request"
    UNKNOWN = "unknown"


@dataclass
class ErrorClassification:
    error_type: ErrorType
    is_retryable: bool
    should_fallback: bool
    status_code: Optional[int] = None


class ErrorClassifier:

    RETRYABLE_STATUS_CODES = {
        408, 429, 500, 502, 503, 504
    }

    @classmethod
    def classify(cls, error: Exception) -> ErrorClassification:

        status_code = getattr(error, "status_code", None)
        error_name = type(error).__name__.lower()
        error_message = str(error).lower()

        # 1. Retryable HTTP errors
        if status_code in cls.RETRYABLE_STATUS_CODES:

            if status_code == 429:
                error_type = ErrorType.RATE_LIMIT

            elif status_code == 408:
                error_type = ErrorType.TIMEOUT

            else:
                error_type = ErrorType.SERVER_ERROR

            return ErrorClassification(
                error_type=error_type,
                is_retryable=True,
                should_fallback=True,
                status_code=status_code,
            )

        # 2. Model not found: no retry, but try another provider
        if status_code == 404:
            model_not_found = (
                "model" in error_message
                and (
                    "not found" in error_message
                    or "does not exist" in error_message
                    or "no such model" in error_message
                )
            )

            if model_not_found:
                return ErrorClassification(
                    error_type=ErrorType.MODEL_NOT_FOUND,
                    is_retryable=False,
                    should_fallback=True,
                    status_code=status_code,
                )

            return ErrorClassification(
                error_type=ErrorType.BAD_REQUEST,
                is_retryable=False,
                should_fallback=False,
                status_code=status_code,
            )

        # 3. Permanent authentication errors
        if status_code == 401:
            return ErrorClassification(
                error_type=ErrorType.AUTHENTICATION,
                is_retryable=False,
                should_fallback=False,
                status_code=status_code,
            )

        if status_code == 403:
            return ErrorClassification(
                error_type=ErrorType.PERMISSION,
                is_retryable=False,
                should_fallback=False,
                status_code=status_code,
            )

        # 4. Other invalid requests
        if status_code in {400, 422}:
            return ErrorClassification(
                error_type=ErrorType.BAD_REQUEST,
                is_retryable=False,
                should_fallback=False,
                status_code=status_code,
            )

        # 5. Exception type classification
        if "timeout" in error_name:
            return ErrorClassification(
                error_type=ErrorType.TIMEOUT,
                is_retryable=True,
                should_fallback=True,
            )

        if "connection" in error_name:
            return ErrorClassification(
                error_type=ErrorType.CONNECTION,
                is_retryable=True,
                should_fallback=True,
            )

        # 6. Unknown errors: do not retry or fallback automatically
        return ErrorClassification(
            error_type=ErrorType.UNKNOWN,
            is_retryable=False,
            should_fallback=False,
            status_code=status_code,
        )
