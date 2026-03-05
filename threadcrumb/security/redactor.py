"""
Content redaction for removing or masking PII.
"""

import logging
from enum import Enum
from typing import Dict

from .pii_detector import PIIDetector, PIIMatch, PIIType

logger = logging.getLogger(__name__)


class RedactionStrategy(str, Enum):
    """Strategies for redacting PII."""
    MASK = "mask"  # Replace with asterisks
    REMOVE = "remove"  # Remove entirely
    HASH = "hash"  # Replace with hash
    PLACEHOLDER = "placeholder"  # Replace with [TYPE] placeholder


class ContentRedactor:
    """Redacts PII from content using configurable strategies."""

    # Default redaction placeholders
    PLACEHOLDERS = {
        PIIType.EMAIL: "[EMAIL]",
        PIIType.PHONE: "[PHONE]",
        PIIType.SSN: "[SSN]",
        PIIType.CREDIT_CARD: "[CREDIT_CARD]",
        PIIType.IP_ADDRESS: "[IP_ADDRESS]",
        PIIType.API_KEY: "[API_KEY]",
        PIIType.AWS_KEY: "[AWS_KEY]",
        PIIType.GITHUB_TOKEN: "[GITHUB_TOKEN]",
        PIIType.PASSWORD: "[PASSWORD]",
        PIIType.URL: "[URL]",
        PIIType.DATE_OF_BIRTH: "[DOB]",
    }

    def __init__(
        self,
        detector: PIIDetector = None,
        default_strategy: RedactionStrategy = RedactionStrategy.PLACEHOLDER,
        strategy_overrides: Dict[PIIType, RedactionStrategy] = None
    ):
        """
        Initialize content redactor.

        Args:
            detector: PII detector to use
            default_strategy: Default redaction strategy
            strategy_overrides: Per-type strategy overrides
        """
        self.detector = detector or PIIDetector()
        self.default_strategy = default_strategy
        self.strategy_overrides = strategy_overrides or {}

    def redact(self, text: str, preserve_structure: bool = True) -> str:
        """
        Redact all PII from text.

        Args:
            text: Text to redact
            preserve_structure: Whether to preserve text length/structure

        Returns:
            Redacted text
        """
        matches = self.detector.detect(text)

        if not matches:
            return text

        # Process matches in reverse order to preserve offsets
        result = text
        for match in reversed(matches):
            strategy = self.strategy_overrides.get(match.pii_type, self.default_strategy)
            replacement = self._get_replacement(match, strategy, preserve_structure)

            result = result[:match.start] + replacement + result[match.end:]

        return result

    def _get_replacement(
        self,
        match: PIIMatch,
        strategy: RedactionStrategy,
        preserve_structure: bool
    ) -> str:
        """Get replacement string for a PII match based on strategy."""

        if strategy == RedactionStrategy.MASK:
            if preserve_structure:
                # Preserve first/last chars for readability
                value_len = len(match.value)
                if value_len <= 4:
                    return "*" * value_len
                return match.value[0] + ("*" * (value_len - 2)) + match.value[-1]
            else:
                return "*" * len(match.value)

        elif strategy == RedactionStrategy.REMOVE:
            return ""

        elif strategy == RedactionStrategy.HASH:
            import hashlib
            hash_value = hashlib.sha256(match.value.encode()).hexdigest()[:8]
            return f"[{match.pii_type.value.upper()}:{hash_value}]"

        elif strategy == RedactionStrategy.PLACEHOLDER:
            return self.PLACEHOLDERS.get(match.pii_type, "[REDACTED]")

        return "[REDACTED]"

    def scan_and_report(self, text: str) -> Dict[str, any]:
        """
        Scan text and generate a PII report without redacting.

        Args:
            text: Text to scan

        Returns:
            Report dictionary with PII statistics
        """
        matches = self.detector.detect(text)

        report = {
            "total_matches": len(matches),
            "contains_pii": len(matches) > 0,
            "matches_by_type": {},
            "positions": []
        }

        for match in matches:
            pii_type_str = match.pii_type.value

            if pii_type_str not in report["matches_by_type"]:
                report["matches_by_type"][pii_type_str] = 0

            report["matches_by_type"][pii_type_str] += 1

            report["positions"].append({
                "type": pii_type_str,
                "start": match.start,
                "end": match.end,
                "length": match.end - match.start
            })

        return report

    def redact_message(self, message: Dict) -> Dict:
        """
        Redact PII from a Slack message object.

        Args:
            message: Slack message dictionary

        Returns:
            Message with redacted content
        """
        redacted = message.copy()

        # Redact text field
        if "text" in redacted:
            redacted["text"] = self.redact(redacted["text"])

        # Redact attachments
        if "attachments" in redacted:
            for attachment in redacted["attachments"]:
                if "text" in attachment:
                    attachment["text"] = self.redact(attachment["text"])
                if "title" in attachment:
                    attachment["title"] = self.redact(attachment["title"])
                if "pretext" in attachment:
                    attachment["pretext"] = self.redact(attachment["pretext"])

        # Redact blocks
        if "blocks" in redacted:
            for block in redacted["blocks"]:
                if block.get("type") == "section" and "text" in block:
                    if "text" in block["text"]:
                        block["text"]["text"] = self.redact(block["text"]["text"])

        return redacted
