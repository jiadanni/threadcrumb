"""
PII (Personally Identifiable Information) detection.

Detects various types of sensitive information in text.
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Pattern

logger = logging.getLogger(__name__)


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    PASSWORD = "password"
    URL = "url"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PIIMatch:
    """Represents a detected PII instance."""
    pii_type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0


class PIIDetector:
    """Detects PII in text using pattern matching."""

    # Regular expression patterns for different PII types
    PATTERNS: Dict[PIIType, Pattern] = {
        PIIType.EMAIL: re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),
        PIIType.PHONE: re.compile(
            r'(?:\b|[\s(])(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        ),
        PIIType.SSN: re.compile(
            r'\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b'
        ),
        PIIType.CREDIT_CARD: re.compile(
            r'\b(?:\d{4}[- ]?){3}\d{4}\b'
        ),
        PIIType.IP_ADDRESS: re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ),
        PIIType.AWS_KEY: re.compile(
            r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'
        ),
        PIIType.GITHUB_TOKEN: re.compile(
            r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255}\b'
        ),
        PIIType.API_KEY: re.compile(
            r'\b(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})["\']?',
            re.IGNORECASE
        ),
        PIIType.PASSWORD: re.compile(
            r'\b(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{6,})["\']?',
            re.IGNORECASE
        ),
        PIIType.URL: re.compile(
            r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
        ),
        PIIType.DATE_OF_BIRTH: re.compile(
            r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b'
        ),
    }

    def __init__(self, enabled_types: List[PIIType] = None, case_sensitive: bool = False):
        """
        Initialize PII detector.

        Args:
            enabled_types: List of PII types to detect (default: all)
            case_sensitive: Whether matching should be case-sensitive
        """
        self.enabled_types = enabled_types or list(PIIType)
        self.case_sensitive = case_sensitive

    def detect(self, text: str) -> List[PIIMatch]:
        """
        Detect all PII instances in text.

        Args:
            text: Text to scan for PII

        Returns:
            List of detected PII matches
        """
        matches = []

        for pii_type in self.enabled_types:
            pattern = self.PATTERNS.get(pii_type)
            if not pattern:
                continue

            for match in pattern.finditer(text):
                pii_match = PIIMatch(
                    pii_type=pii_type,
                    value=match.group(0),
                    start=match.start(),
                    end=match.end()
                )
                matches.append(pii_match)

        # Sort by position in text
        matches.sort(key=lambda m: m.start)

        return matches

    def contains_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if PII detected, False otherwise
        """
        return len(self.detect(text)) > 0

    def get_pii_count_by_type(self, text: str) -> Dict[PIIType, int]:
        """
        Count PII instances by type.

        Args:
            text: Text to scan

        Returns:
            Dictionary mapping PII types to counts
        """
        matches = self.detect(text)
        counts = {pii_type: 0 for pii_type in self.enabled_types}

        for match in matches:
            counts[match.pii_type] += 1

        return counts

    def validate_credit_card(self, number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.

        Args:
            number: Credit card number string

        Returns:
            True if valid, False otherwise
        """
        # Remove spaces and dashes
        number = re.sub(r'[\s-]', '', number)

        if not number.isdigit():
            return False

        # Luhn algorithm
        total = 0
        reverse_digits = number[::-1]

        for i, digit in enumerate(reverse_digits):
            n = int(digit)
            if i % 2 == 1:
                n = n * 2
                if n > 9:
                    n = n - 9
            total += n

        return total % 10 == 0
