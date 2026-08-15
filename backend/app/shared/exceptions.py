from __future__ import annotations


class PlatformError(Exception):
    status_code = 500
    code = "platform_error"
    public_message = "An internal error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.public_message)


class BotNotFoundError(PlatformError):
    status_code = 404
    code = "bot_not_found"
    public_message = "Bot was not found."


class BotAlreadyExistsError(PlatformError):
    status_code = 409
    code = "bot_already_exists"
    public_message = "Bot already exists."


class BotDisabledError(PlatformError):
    status_code = 403
    code = "bot_disabled"
    public_message = "Bot is disabled."


class BotUnavailableError(PlatformError):
    status_code = 503
    code = "bot_unavailable"
    public_message = "Bot is temporarily unavailable."


class InvalidTelegramSecretError(PlatformError):
    status_code = 401
    code = "invalid_telegram_secret"
    public_message = "Invalid Telegram webhook secret."


class UserBlockedError(PlatformError):
    status_code = 403
    code = "user_blocked"
    public_message = "User is not permitted to use this bot."


class DuplicateUpdateError(PlatformError):
    status_code = 200
    code = "duplicate_update"
    public_message = "Update was already accepted."


class UpdateAttemptsExhaustedError(DuplicateUpdateError):
    code = "update_attempts_exhausted"
    public_message = "Update retry limit was reached."


class TelegramAPIError(PlatformError):
    status_code = 502
    code = "telegram_api_error"
    public_message = "Telegram API request failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        telegram_error_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.telegram_error_code = telegram_error_code
        self.retry_after = retry_after


class UserStateConflictError(PlatformError):
    status_code = 409
    code = "user_state_conflict"
    public_message = "User state changed concurrently."


class DatabaseUnavailableError(PlatformError):
    status_code = 503
    code = "database_unavailable"
    public_message = "Database is unavailable."


class InvalidBotModuleError(PlatformError):
    status_code = 422
    code = "invalid_bot_module"
    public_message = "Bot module registration is invalid."


class InvalidUpdateError(PlatformError):
    status_code = 422
    code = "invalid_telegram_update"
    public_message = "Telegram update payload is invalid."


class InvalidAdminAPIKeyError(PlatformError):
    status_code = 401
    code = "invalid_admin_api_key"
    public_message = "Invalid admin API key."


class AuthenticationRequiredError(PlatformError):
    status_code = 401
    code = "authentication_required"
    public_message = "Authentication is required."


class InvalidTelegramInitDataError(PlatformError):
    status_code = 401
    code = "invalid_telegram_init_data"
    public_message = "Telegram authentication data is invalid or expired."


class SessionExpiredError(PlatformError):
    status_code = 401
    code = "session_expired"
    public_message = "Authentication session is invalid or expired."
