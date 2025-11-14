"""
Custom exceptions with helpful error messages and suggestions.
"""

from typing import Optional


class ThreadCrumbError(Exception):
    """Base exception for ThreadCrumb with helpful messages."""

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        details: Optional[str] = None
    ):
        """
        Initialize error with message and optional suggestion.

        Args:
            message: Error message
            suggestion: Helpful suggestion for fixing the error
            details: Additional technical details
        """
        self.message = message
        self.suggestion = suggestion
        self.details = details
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message with suggestion."""
        parts = [f"❌ Error: {self.message}"]

        if self.details:
            parts.append(f"\nDetails: {self.details}")

        if self.suggestion:
            parts.append(f"\n💡 Suggestion: {self.suggestion}")

        return "\n".join(parts)


class SlackAuthError(ThreadCrumbError):
    """Slack authentication error."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion=(
                "Check your Slack credentials:\n"
                "  1. Run 'threadcrumb auth' to re-authenticate\n"
                "  2. Verify your app has the correct OAuth scopes\n"
                "  3. Check if your token has expired"
            ),
            details=details
        )


class SlackAPIError(ThreadCrumbError):
    """Slack API error."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        suggestion = "Check the Slack API documentation: https://api.slack.com/methods"

        if error_code == "rate_limited":
            suggestion = (
                "You're being rate limited by Slack.\n"
                "  1. Increase 'rate_limit_delay' in your config\n"
                "  2. Process fewer channels at once\n"
                "  3. Wait a few minutes before retrying"
            )
        elif error_code == "channel_not_found":
            suggestion = (
                "Channel not found.\n"
                "  1. Run 'threadcrumb list-channels' to see available channels\n"
                "  2. Check the channel name or ID is correct\n"
                "  3. Verify your app has access to this channel"
            )
        elif error_code == "not_in_channel":
            suggestion = (
                "Your bot is not in this channel.\n"
                "  1. Invite the bot to the channel in Slack\n"
                "  2. Or use a user token instead of bot token"
            )

        super().__init__(
            message=message,
            suggestion=suggestion,
            details=f"Error code: {error_code}" if error_code else None
        )


class ConfluenceAuthError(ThreadCrumbError):
    """Confluence authentication error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        suggestion = (
            "Check your Confluence credentials:\n"
            "  1. Verify your API token is correct\n"
            "  2. For Cloud: use email as username\n"
            "  3. For Server: use username (not email)\n"
            "  4. Generate a new API token at:\n"
            "     https://id.atlassian.com/manage-profile/security/api-tokens"
        )

        if status_code == 403:
            suggestion = (
                "Permission denied.\n"
                "  1. Check you have edit permissions in the space\n"
                "  2. Verify the space key is correct\n"
                "  3. Try creating a page manually to confirm access"
            )

        super().__init__(
            message=message,
            suggestion=suggestion,
            details=f"HTTP {status_code}" if status_code else None
        )


class ConfluenceConnectionError(ThreadCrumbError):
    """Confluence connection error."""

    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion=(
                "Check your Confluence connection:\n"
                "  1. Verify the base URL is correct\n"
                "     Cloud: https://yourcompany.atlassian.net\n"
                "     Server: http://confluence.company.com:8090\n"
                "  2. Check your network connection\n"
                "  3. Verify Confluence is accessible from your location\n"
                "  4. Run with --dry-run to test without creating pages"
            ),
            details=f"URL: {url}" if url else None
        )


class AIServiceError(ThreadCrumbError):
    """AI service error."""

    def __init__(self, message: str, provider: str = "bedrock"):
        suggestions = {
            "bedrock": (
                "Check your AWS Bedrock setup:\n"
                "  1. Verify AWS credentials: aws sts get-caller-identity\n"
                "  2. Check Bedrock model access in your region\n"
                "  3. Verify you have Bedrock permissions\n"
                "  4. Try with --no-ai to skip AI processing"
            ),
            "openai": (
                "Check your OpenAI setup:\n"
                "  1. Verify your API key is valid\n"
                "  2. Check your account has available credits\n"
                "  3. Try with --no-ai to skip AI processing"
            )
        }

        super().__init__(
            message=message,
            suggestion=suggestions.get(provider, "Check your AI provider configuration"),
            details=f"Provider: {provider}"
        )


class ConfigurationError(ThreadCrumbError):
    """Configuration error."""

    def __init__(self, message: str, config_path: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion=(
                "Fix your configuration:\n"
                "  1. Run 'threadcrumb config-init' to create default config\n"
                "  2. Edit ~/.threadcrumb/config.yaml\n"
                "  3. Or set environment variables (see README)\n"
                "  4. Use command-line options to override config"
            ),
            details=f"Config file: {config_path}" if config_path else None
        )


class ValidationError(ThreadCrumbError):
    """Input validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion="Check your input parameters and try again",
            details=f"Field: {field}" if field else None
        )


class ProcessingError(ThreadCrumbError):
    """Content processing error."""

    def __init__(self, message: str, channel: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion=(
                "Try these steps:\n"
                "  1. Check if the channel has messages\n"
                "  2. Try with --no-cache to fetch fresh data\n"
                "  3. Exclude this channel and process others\n"
                "  4. Check logs for more details"
            ),
            details=f"Channel: {channel}" if channel else None
        )


class ExportError(ThreadCrumbError):
    """Export error."""

    def __init__(self, message: str, format: Optional[str] = None):
        super().__init__(
            message=message,
            suggestion=(
                "Try these steps:\n"
                "  1. Check output directory permissions\n"
                "  2. Ensure enough disk space\n"
                "  3. Try a different output format\n"
                "  4. Check if files are locked/in use"
            ),
            details=f"Format: {format}" if format else None
        )


def format_error_with_context(
    error: Exception,
    context: Optional[str] = None
) -> str:
    """
    Format any exception with additional context.

    Args:
        error: Exception to format
        context: Additional context information

    Returns:
        Formatted error message
    """
    if isinstance(error, ThreadCrumbError):
        # Already has nice formatting
        return str(error)

    # Format generic exception
    message = f"❌ Error: {str(error)}"

    if context:
        message += f"\nContext: {context}"

    message += "\n\n💡 Tip: Check the logs for more details (use --verbose for debug info)"

    return message
