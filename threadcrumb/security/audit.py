"""
Audit logging for compliance and security tracking.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class AuditLevel(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEventType(str, Enum):
    """Types of audit events."""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    ENCRYPTION_ENABLED = "encryption_enabled"
    ENCRYPTION_DISABLED = "encryption_disabled"
    CONFIG_CHANGED = "config_changed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class AuditEvent:
    """Represents an audit event."""

    timestamp: str
    event_type: AuditEventType
    level: AuditLevel
    message: str
    user: Optional[str] = None
    workspace_id: Optional[str] = None
    channel_id: Optional[str] = None
    resource: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Logs audit events for compliance and security."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        min_level: AuditLevel = AuditLevel.INFO,
        enable_console: bool = False
    ):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file
            min_level: Minimum level to log
            enable_console: Whether to also log to console
        """
        self.log_file = log_file or (Path.home() / ".threadcrumb" / "audit.log")
        self.min_level = min_level
        self.enable_console = enable_console

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Track events in memory for reporting
        self.events: List[AuditEvent] = []

    def log(
        self,
        event_type: AuditEventType,
        message: str,
        level: AuditLevel = AuditLevel.INFO,
        user: Optional[str] = None,
        workspace_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        resource: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            level: Severity level
            user: User identifier
            workspace_id: Slack workspace ID
            channel_id: Slack channel ID
            resource: Resource identifier
            metadata: Additional metadata
            error: Error message if applicable
        """
        # Check minimum level
        level_order = {
            AuditLevel.INFO: 0,
            AuditLevel.WARNING: 1,
            AuditLevel.ERROR: 2,
            AuditLevel.CRITICAL: 3
        }

        if level_order[level] < level_order[self.min_level]:
            return

        event = AuditEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            level=level,
            message=message,
            user=user,
            workspace_id=workspace_id,
            channel_id=channel_id,
            resource=resource,
            metadata=metadata,
            error=error
        )

        # Store in memory
        self.events.append(event)

        # Write to file
        try:
            with open(self.log_file, 'a') as f:
                f.write(event.to_json() + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

        # Log to console if enabled
        if self.enable_console:
            log_message = f"[AUDIT] [{level.value.upper()}] {event_type.value}: {message}"
            if level == AuditLevel.CRITICAL or level == AuditLevel.ERROR:
                logger.error(log_message)
            elif level == AuditLevel.WARNING:
                logger.warning(log_message)
            else:
                logger.info(log_message)

    def log_auth_success(self, user: str, workspace_id: str):
        """Log successful authentication."""
        self.log(
            event_type=AuditEventType.AUTH_SUCCESS,
            message=f"User authenticated successfully",
            level=AuditLevel.INFO,
            user=user,
            workspace_id=workspace_id
        )

    def log_auth_failure(self, user: str, error: str):
        """Log failed authentication."""
        self.log(
            event_type=AuditEventType.AUTH_FAILURE,
            message=f"Authentication failed",
            level=AuditLevel.WARNING,
            user=user,
            error=error
        )

    def log_data_access(self, resource: str, user: str = None, channel_id: str = None):
        """Log data access."""
        self.log(
            event_type=AuditEventType.DATA_ACCESS,
            message=f"Data accessed: {resource}",
            level=AuditLevel.INFO,
            user=user,
            channel_id=channel_id,
            resource=resource
        )

    def log_data_export(
        self,
        format: str,
        channel_count: int,
        thread_count: int,
        user: str = None
    ):
        """Log data export operation."""
        self.log(
            event_type=AuditEventType.DATA_EXPORT,
            message=f"Exported {channel_count} channels ({thread_count} threads) in {format} format",
            level=AuditLevel.INFO,
            user=user,
            metadata={
                "format": format,
                "channel_count": channel_count,
                "thread_count": thread_count
            }
        )

    def log_pii_detected(self, pii_type: str, count: int, channel_id: str = None):
        """Log PII detection."""
        self.log(
            event_type=AuditEventType.PII_DETECTED,
            message=f"Detected {count} instances of {pii_type}",
            level=AuditLevel.WARNING,
            channel_id=channel_id,
            metadata={
                "pii_type": pii_type,
                "count": count
            }
        )

    def log_pii_redacted(self, redaction_count: int, channel_id: str = None):
        """Log PII redaction."""
        self.log(
            event_type=AuditEventType.PII_REDACTED,
            message=f"Redacted {redaction_count} PII instances",
            level=AuditLevel.INFO,
            channel_id=channel_id,
            metadata={
                "redaction_count": redaction_count
            }
        )

    def log_error(self, error_message: str, resource: str = None):
        """Log an error."""
        self.log(
            event_type=AuditEventType.ERROR_OCCURRED,
            message="Error occurred during operation",
            level=AuditLevel.ERROR,
            resource=resource,
            error=error_message
        )

    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        level: Optional[AuditLevel] = None,
        since: Optional[str] = None
    ) -> List[AuditEvent]:
        """
        Retrieve audit events with optional filtering.

        Args:
            event_type: Filter by event type
            level: Filter by severity level
            since: Filter events after this timestamp (ISO format)

        Returns:
            List of matching audit events
        """
        events = self.events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if level:
            events = [e for e in events if e.level == level]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return events

    def generate_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Generate an audit report.

        Args:
            output_path: Optional path to save report as JSON

        Returns:
            Report dictionary with statistics
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(self.events),
            "events_by_type": {},
            "events_by_level": {},
            "recent_errors": []
        }

        # Count by type
        for event in self.events:
            event_type_str = event.event_type.value
            if event_type_str not in report["events_by_type"]:
                report["events_by_type"][event_type_str] = 0
            report["events_by_type"][event_type_str] += 1

            # Count by level
            level_str = event.level.value
            if level_str not in report["events_by_level"]:
                report["events_by_level"][level_str] = 0
            report["events_by_level"][level_str] += 1

            # Track recent errors
            if event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
                report["recent_errors"].append({
                    "timestamp": event.timestamp,
                    "message": event.message,
                    "error": event.error
                })

        # Keep only 10 most recent errors
        report["recent_errors"] = report["recent_errors"][-10:]

        # Save to file if requested
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Audit report saved to: {output_path}")

        return report

    def clear(self):
        """Clear in-memory events (does not affect log file)."""
        self.events = []
        logger.info("Cleared audit event cache")
