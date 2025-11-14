"""Tests for security module (PII detection, redaction, encryption, audit)."""

import pytest
from pathlib import Path
from threadcrumb.security import (
    PIIDetector,
    PIIType,
    ContentRedactor,
    RedactionStrategy,
    DataEncryptor,
    AuditLogger,
    AuditEventType,
    AuditLevel
)


class TestPIIDetector:
    """Test PII detection functionality."""

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "Contact me at john.doe@example.com or jane@test.org"
        matches = detector.detect(text)

        assert len(matches) == 2
        assert all(m.pii_type == PIIType.EMAIL for m in matches)
        assert "john.doe@example.com" in [m.value for m in matches]

    def test_detect_phone(self):
        """Test phone number detection."""
        detector = PIIDetector()
        text = "Call me at (555) 123-4567 or 555-987-6543"
        matches = detector.detect(text)

        assert len(matches) >= 2
        assert any(m.pii_type == PIIType.PHONE for m in matches)

    def test_detect_ssn(self):
        """Test SSN detection."""
        detector = PIIDetector()
        text = "My SSN is 123-45-6789"
        matches = detector.detect(text)

        assert len(matches) >= 1
        assert any(m.pii_type == PIIType.SSN for m in matches)

    def test_detect_credit_card(self):
        """Test credit card detection."""
        detector = PIIDetector()
        # Valid test credit card numbers
        text = "Card: 4532-1234-5678-9010"
        matches = detector.detect(text)

        assert any(m.pii_type == PIIType.CREDIT_CARD for m in matches)

    def test_detect_api_key(self):
        """Test API key detection."""
        detector = PIIDetector()
        text = "api_key=abc123def456ghi789jkl012"
        matches = detector.detect(text)

        assert any(m.pii_type == PIIType.API_KEY for m in matches)

    def test_detect_aws_key(self):
        """Test AWS key detection."""
        detector = PIIDetector()
        text = "Access key: AKIAIOSFODNN7EXAMPLE"
        matches = detector.detect(text)

        assert any(m.pii_type == PIIType.AWS_KEY for m in matches)

    def test_contains_pii(self):
        """Test PII presence check."""
        detector = PIIDetector()

        assert detector.contains_pii("Contact: john@example.com")
        assert not detector.contains_pii("No sensitive data here")

    def test_get_pii_count_by_type(self):
        """Test PII counting."""
        detector = PIIDetector()
        text = "Email: test@example.com, Phone: (555) 123-4567, another@test.com"
        counts = detector.get_pii_count_by_type(text)

        assert counts[PIIType.EMAIL] >= 2
        assert counts[PIIType.PHONE] >= 1


class TestContentRedactor:
    """Test content redaction functionality."""

    def test_redact_with_placeholder(self):
        """Test placeholder redaction strategy."""
        detector = PIIDetector()
        redactor = ContentRedactor(
            detector=detector,
            default_strategy=RedactionStrategy.PLACEHOLDER
        )

        text = "Email me at john@example.com"
        redacted = redactor.redact(text)

        assert "[EMAIL]" in redacted
        assert "john@example.com" not in redacted

    def test_redact_with_mask(self):
        """Test masking redaction strategy."""
        detector = PIIDetector()
        redactor = ContentRedactor(
            detector=detector,
            default_strategy=RedactionStrategy.MASK
        )

        text = "Contact: test@example.com"
        redacted = redactor.redact(text, preserve_structure=True)

        assert "test@example.com" not in redacted
        assert "*" in redacted  # Should contain asterisks

    def test_redact_with_hash(self):
        """Test hash redaction strategy."""
        detector = PIIDetector()
        redactor = ContentRedactor(
            detector=detector,
            default_strategy=RedactionStrategy.HASH
        )

        text = "My email is john@example.com"
        redacted = redactor.redact(text)

        assert "[EMAIL:" in redacted  # Hash format
        assert "john@example.com" not in redacted

    def test_redact_with_removal(self):
        """Test removal redaction strategy."""
        detector = PIIDetector()
        redactor = ContentRedactor(
            detector=detector,
            default_strategy=RedactionStrategy.REMOVE
        )

        text = "Email: test@example.com here"
        redacted = redactor.redact(text)

        assert "test@example.com" not in redacted
        assert len(redacted) < len(text)

    def test_redact_message(self):
        """Test redacting Slack message."""
        detector = PIIDetector()
        redactor = ContentRedactor(detector=detector)

        message = {
            "text": "Contact john@example.com",
            "user": "U123",
            "attachments": [
                {"text": "Phone: (555) 123-4567"}
            ]
        }

        redacted = redactor.redact_message(message)

        assert "[EMAIL]" in redacted["text"]
        assert "[PHONE]" in redacted["attachments"][0]["text"]

    def test_scan_and_report(self):
        """Test PII scanning report."""
        detector = PIIDetector()
        redactor = ContentRedactor(detector=detector)

        text = "Email: test@example.com, Phone: (555) 123-4567"
        report = redactor.scan_and_report(text)

        assert report["contains_pii"] is True
        assert report["total_matches"] >= 2
        assert "email" in report["matches_by_type"]


class TestDataEncryptor:
    """Test encryption functionality."""

    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption."""
        encryptor = DataEncryptor()

        original = "sensitive data"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt_to_string(encrypted)

        assert encrypted != original.encode()
        assert decrypted == original

    def test_encrypt_decrypt_bytes(self):
        """Test bytes encryption and decryption."""
        encryptor = DataEncryptor()

        original = b"binary data"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)

        assert encrypted != original
        assert decrypted == original

    def test_encrypt_decrypt_file(self, tmp_path):
        """Test file encryption and decryption."""
        encryptor = DataEncryptor()

        # Create test file
        input_file = tmp_path / "test.txt"
        input_file.write_text("secret content")

        # Encrypt
        encrypted_file = encryptor.encrypt_file(input_file)
        assert encrypted_file.exists()
        assert encrypted_file.read_bytes() != input_file.read_bytes()

        # Decrypt
        decrypted_file = encryptor.decrypt_file(encrypted_file)
        assert decrypted_file.read_text() == "secret content"

    def test_key_generation(self):
        """Test encryption key generation."""
        key = DataEncryptor.generate_key()

        assert isinstance(key, bytes)
        assert len(key) > 0

        # Key should be usable
        encryptor = DataEncryptor(key=key)
        encrypted = encryptor.encrypt("test")
        assert encrypted is not None

    def test_save_load_key(self, tmp_path):
        """Test key persistence."""
        encryptor = DataEncryptor()
        key_file = tmp_path / "test.key"

        # Save key
        encryptor.save_key(key_file)
        assert key_file.exists()

        # Load key and use it
        loaded_encryptor = DataEncryptor(key_file=key_file)
        test_data = "test string"

        encrypted = encryptor.encrypt(test_data)
        decrypted = loaded_encryptor.decrypt_to_string(encrypted)

        assert decrypted == test_data


class TestAuditLogger:
    """Test audit logging functionality."""

    def test_log_event(self, tmp_path):
        """Test basic event logging."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log(
            event_type=AuditEventType.AUTH_SUCCESS,
            message="Test authentication",
            level=AuditLevel.INFO,
            user="testuser"
        )

        assert log_file.exists()
        content = log_file.read_text()
        assert "auth_success" in content
        assert "testuser" in content

    def test_log_auth_success(self, tmp_path):
        """Test authentication success logging."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log_auth_success(user="user@example.com", workspace_id="T123")

        content = log_file.read_text()
        assert "auth_success" in content
        assert "user@example.com" in content
        assert "T123" in content

    def test_log_pii_detected(self, tmp_path):
        """Test PII detection logging."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log_pii_detected(pii_type="email", count=3, channel_id="C123")

        content = log_file.read_text()
        assert "pii_detected" in content
        assert "email" in content

    def test_get_events(self, tmp_path):
        """Test event retrieval."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log_auth_success(user="user1", workspace_id="T1")
        logger.log_auth_failure(user="user2", error="Invalid token")
        logger.log_data_export(format="markdown", channel_count=5, thread_count=50)

        # Filter by event type
        auth_events = logger.get_events(event_type=AuditEventType.AUTH_SUCCESS)
        assert len(auth_events) == 1
        assert auth_events[0].user == "user1"

        # Filter by level
        warning_events = logger.get_events(level=AuditLevel.WARNING)
        assert len(warning_events) >= 1

    def test_generate_report(self, tmp_path):
        """Test audit report generation."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file)

        logger.log_auth_success(user="user1", workspace_id="T1")
        logger.log_data_export(format="html", channel_count=10, thread_count=100)
        logger.log_error("Test error")

        report = logger.generate_report()

        assert report["total_events"] == 3
        assert "auth_success" in report["events_by_type"]
        assert "data_export" in report["events_by_type"]
        assert len(report["recent_errors"]) >= 1

    def test_min_level_filtering(self, tmp_path):
        """Test minimum level filtering."""
        log_file = tmp_path / "audit.log"
        logger = AuditLogger(log_file=log_file, min_level=AuditLevel.WARNING)

        # This should be logged (WARNING level)
        logger.log_pii_detected(pii_type="email", count=1)

        # This should NOT be logged (INFO level)
        logger.log_auth_success(user="user", workspace_id="T1")

        events = logger.get_events()
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.PII_DETECTED
