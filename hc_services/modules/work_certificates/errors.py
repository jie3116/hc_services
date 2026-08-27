from __future__ import annotations


class ApiError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(ApiError):
    status_code = 400
    code = "validation_error"


class ForbiddenError(ApiError):
    status_code = 403
    code = "forbidden"


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


class ConflictError(ApiError):
    status_code = 409
    code = "invalid_state"


class BusinessRuleError(ApiError):
    status_code = 422
    code = "business_rule_violation"
