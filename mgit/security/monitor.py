"""Security monitoring and event tracking for mgit.

This module provides security monitoring capabilities including
event logging, anomaly detection, and security audit trails.
"""

import time
import logging
import threading
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json

from .logging import SecurityLogger

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Represents a security event."""

    timestamp: datetime
    event_type: str
    severity: str
    source: str
    details: Dict[str, Any]
    user_context: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None


@dataclass
class SecurityMetrics:
    """Security metrics tracking."""

    failed_auth_attempts: int = 0
    successful_auth_attempts: int = 0
    api_calls_made: int = 0
    validation_failures: int = 0
    credential_exposures: int = 0
    suspicious_activities: int = 0
    rate_limit_hits: int = 0

    def reset(self):
        """Reset all metrics to zero."""
        self.failed_auth_attempts = 0
        self.successful_auth_attempts = 0
        self.api_calls_made = 0
        self.validation_failures = 0
        self.credential_exposures = 0
        self.suspicious_activities = 0
        self.rate_limit_hits = 0


class SecurityMonitor:
    """Security monitoring and event tracking system."""

    def __init__(self, max_events: int = 10000, retention_hours: int = 24):
        """Initialize security monitor.

        Args:
            max_events: Maximum number of events to keep in memory
            retention_hours: Hours to retain events
        """
        self.max_events = max_events
        self.retention_hours = retention_hours
        self.events: deque = deque(maxlen=max_events)
        self.metrics = SecurityMetrics()
        self.lock = threading.Lock()

        # Rate limiting tracking
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
        self.rate_limit_windows = {
            "api_calls": (60, 100),  # 100 calls per minute
            "auth_attempts": (300, 10),  # 10 attempts per 5 minutes
            "validation_failures": (60, 20),  # 20 failures per minute
        }

        # Anomaly detection patterns
        self.suspicious_patterns = {
            "rapid_auth_failures": {"threshold": 5, "window": 60},
            "excessive_api_calls": {"threshold": 200, "window": 300},
            "repeated_validation_failures": {"threshold": 10, "window": 120},
        }

        # Known suspicious indicators
        self.suspicious_indicators = {
            "suspicious_user_agents": ["curl", "wget", "python-requests", "httpie"],
            "suspicious_paths": ["..", "~/", "/etc/", "/proc/", "C:\\Windows"],
            "credential_keywords": ["password", "token", "secret", "key", "auth"],
        }

        self.security_logger = SecurityLogger("security_monitor")

    def log_event(
        self,
        event_type: str,
        severity: str,
        source: str,
        details: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        remediation: Optional[str] = None,
    ) -> None:
        """Log a security event.

        Args:
            event_type: Type of security event
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
            source: Source component that generated the event
            details: Event details
            user_context: Optional user context information
            remediation: Optional remediation suggestions
        """
        with self.lock:
            event = SecurityEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                severity=severity,
                source=source,
                details=details,
                user_context=user_context,
                remediation=remediation,
            )

            self.events.append(event)

            # Update metrics
            self._update_metrics(event_type)

            # Check for anomalies
            self._check_anomalies(event)

            # Log to security logger
            self.security_logger.log_security_event(event_type, str(details), severity)

    def log_authentication_attempt(
        self,
        provider: str,
        organization: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication attempt.

        Args:
            provider: Provider name
            organization: Organization name
            success: Whether authentication succeeded
            details: Additional details
        """
        event_details = {
            "provider": provider,
            "organization": organization,
            "success": success,
            **(details or {}),
        }

        severity = "INFO" if success else "WARNING"
        event_type = "authentication_success" if success else "authentication_failure"

        # Check rate limiting for auth attempts
        self._check_rate_limit("auth_attempts", f"{provider}:{organization}")

        self.log_event(event_type, severity, "auth", event_details)

    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time: float,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log API call.

        Args:
            method: HTTP method
            url: Request URL (should be pre-masked)
            status_code: Response status code
            response_time: Response time in seconds
            user_agent: Request user agent
        """
        event_details = {
            "method": method,
            "url": url,
            "status_code": status_code,
            "response_time": response_time,
            "user_agent": user_agent,
        }

        # Determine severity based on status code
        if status_code >= 500:
            severity = "ERROR"
        elif status_code >= 400:
            severity = "WARNING"
        else:
            severity = "INFO"

        # Check for suspicious patterns
        if self._is_suspicious_api_call(method, url, user_agent):
            severity = "WARNING"
            event_details["suspicious"] = True

        # Check rate limiting
        self._check_rate_limit("api_calls", "global")

        self.log_event("api_call", severity, "api", event_details)

    def log_validation_failure(self, input_type: str, value: str, reason: str) -> None:
        """Log input validation failure.

        Args:
            input_type: Type of input that failed validation
            value: Input value (should be pre-masked if sensitive)
            reason: Reason for validation failure
        """
        event_details = {"input_type": input_type, "value": value, "reason": reason}

        # Check if this indicates a potential attack
        severity = "WARNING"
        if any(
            indicator in value.lower()
            for indicator in self.suspicious_indicators["suspicious_paths"]
        ):
            severity = "ERROR"
            event_details["potential_attack"] = True

        # Check rate limiting
        self._check_rate_limit("validation_failures", input_type)

        self.log_event("validation_failure", severity, "validation", event_details)

    def log_credential_exposure(
        self, context: str, credential_type: str, exposure_method: str
    ) -> None:
        """Log potential credential exposure.

        Args:
            context: Context where exposure occurred
            credential_type: Type of credential exposed
            exposure_method: How the credential was exposed
        """
        event_details = {
            "context": context,
            "credential_type": credential_type,
            "exposure_method": exposure_method,
        }

        self.log_event(
            "credential_exposure",
            "CRITICAL",
            "security",
            event_details,
            remediation="Review logs and rotate affected credentials immediately",
        )

    def log_suspicious_activity(
        self, activity_type: str, details: Dict[str, Any], severity: str = "WARNING"
    ) -> None:
        """Log suspicious activity.

        Args:
            activity_type: Type of suspicious activity
            details: Activity details
            severity: Event severity
        """
        self.log_event(
            "suspicious_activity",
            severity,
            "security",
            {"activity_type": activity_type, **details},
        )

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the specified time period.

        Args:
            hours: Hours to look back

        Returns:
            Security summary dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent_events = [
                event for event in self.events if event.timestamp > cutoff_time
            ]

            # Count events by type and severity
            event_counts = defaultdict(int)
            severity_counts = defaultdict(int)

            for event in recent_events:
                event_counts[event.event_type] += 1
                severity_counts[event.severity] += 1

            # Calculate metrics
            metrics_dict = {
                "failed_auth_attempts": self.metrics.failed_auth_attempts,
                "successful_auth_attempts": self.metrics.successful_auth_attempts,
                "api_calls_made": self.metrics.api_calls_made,
                "validation_failures": self.metrics.validation_failures,
                "credential_exposures": self.metrics.credential_exposures,
                "suspicious_activities": self.metrics.suspicious_activities,
                "rate_limit_hits": self.metrics.rate_limit_hits,
            }

            return {
                "time_period_hours": hours,
                "total_events": len(recent_events),
                "events_by_type": dict(event_counts),
                "events_by_severity": dict(severity_counts),
                "metrics": metrics_dict,
                "security_score": self._calculate_security_score(recent_events),
                "recommendations": self._get_security_recommendations(recent_events),
            }

    def get_recent_events(
        self,
        count: int = 100,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[SecurityEvent]:
        """Get recent security events.

        Args:
            count: Maximum number of events to return
            event_type: Optional filter by event type
            severity: Optional filter by severity

        Returns:
            List of recent security events
        """
        with self.lock:
            events = list(self.events)

            # Apply filters
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            if severity:
                events = [e for e in events if e.severity == severity]

            # Return most recent events
            return events[-count:]

    def export_events(self, file_path: Path, hours: int = 24) -> None:
        """Export security events to file.

        Args:
            file_path: Path to export file
            hours: Hours of events to export
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent_events = [
                event for event in self.events if event.timestamp > cutoff_time
            ]

            # Convert events to serializable format
            serializable_events = []
            for event in recent_events:
                serializable_events.append(
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type,
                        "severity": event.severity,
                        "source": event.source,
                        "details": event.details,
                        "user_context": event.user_context,
                        "remediation": event.remediation,
                    }
                )

            # Write to file
            with open(file_path, "w") as f:
                json.dump(
                    {
                        "export_timestamp": datetime.now().isoformat(),
                        "time_period_hours": hours,
                        "event_count": len(serializable_events),
                        "events": serializable_events,
                    },
                    f,
                    indent=2,
                )

    def cleanup_old_events(self) -> None:
        """Remove old events beyond retention period."""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        with self.lock:
            # Convert deque to list, filter, and recreate deque
            current_events = list(self.events)
            recent_events = [
                event for event in current_events if event.timestamp > cutoff_time
            ]
            self.events = deque(recent_events, maxlen=self.max_events)

    def _update_metrics(self, event_type: str) -> None:
        """Update security metrics based on event type."""
        if event_type == "authentication_failure":
            self.metrics.failed_auth_attempts += 1
        elif event_type == "authentication_success":
            self.metrics.successful_auth_attempts += 1
        elif event_type == "api_call":
            self.metrics.api_calls_made += 1
        elif event_type == "validation_failure":
            self.metrics.validation_failures += 1
        elif event_type == "credential_exposure":
            self.metrics.credential_exposures += 1
        elif event_type == "suspicious_activity":
            self.metrics.suspicious_activities += 1
        elif event_type == "rate_limit_exceeded":
            self.metrics.rate_limit_hits += 1

    def _check_rate_limit(self, limit_type: str, identifier: str) -> bool:
        """Check if rate limit is exceeded.

        Args:
            limit_type: Type of rate limit to check
            identifier: Identifier for the rate limit (e.g., IP, user)

        Returns:
            True if rate limit exceeded
        """
        if limit_type not in self.rate_limit_windows:
            return False

        window_seconds, max_requests = self.rate_limit_windows[limit_type]
        current_time = time.time()
        key = f"{limit_type}:{identifier}"

        # Clean old entries
        self.rate_limits[key] = [
            timestamp
            for timestamp in self.rate_limits[key]
            if current_time - timestamp < window_seconds
        ]

        # Add current request
        self.rate_limits[key].append(current_time)

        # Check if limit exceeded
        if len(self.rate_limits[key]) > max_requests:
            self.log_event(
                "rate_limit_exceeded",
                "WARNING",
                "monitor",
                {
                    "limit_type": limit_type,
                    "identifier": identifier,
                    "requests_in_window": len(self.rate_limits[key]),
                    "max_allowed": max_requests,
                    "window_seconds": window_seconds,
                },
            )
            return True

        return False

    def _check_anomalies(self, event: SecurityEvent) -> None:
        """Check for anomalous patterns in events."""
        current_time = time.time()

        for pattern_name, config in self.suspicious_patterns.items():
            threshold = config["threshold"]
            window = config["window"]

            # Count matching events in time window
            cutoff_time = datetime.now() - timedelta(seconds=window)
            matching_events = [
                e
                for e in self.events
                if e.timestamp > cutoff_time
                and self._event_matches_pattern(e, pattern_name)
            ]

            if len(matching_events) >= threshold:
                self.log_suspicious_activity(
                    f"anomaly_{pattern_name}",
                    {
                        "pattern": pattern_name,
                        "events_in_window": len(matching_events),
                        "threshold": threshold,
                        "window_seconds": window,
                    },
                    "ERROR",
                )

    def _event_matches_pattern(self, event: SecurityEvent, pattern: str) -> bool:
        """Check if event matches anomaly pattern."""
        if pattern == "rapid_auth_failures":
            return event.event_type == "authentication_failure"
        elif pattern == "excessive_api_calls":
            return event.event_type == "api_call"
        elif pattern == "repeated_validation_failures":
            return event.event_type == "validation_failure"
        return False

    def _is_suspicious_api_call(
        self, method: str, url: str, user_agent: Optional[str]
    ) -> bool:
        """Check if API call is suspicious."""
        if user_agent:
            for suspicious_ua in self.suspicious_indicators["suspicious_user_agents"]:
                if suspicious_ua.lower() in user_agent.lower():
                    return True

        # Check for suspicious patterns in URL
        for suspicious_path in self.suspicious_indicators["suspicious_paths"]:
            if suspicious_path in url:
                return True

        return False

    def _calculate_security_score(self, events: List[SecurityEvent]) -> int:
        """Calculate security score (0-100) based on recent events."""
        if not events:
            return 100

        score = 100

        # Deduct points for various event types
        for event in events:
            if event.severity == "CRITICAL":
                score -= 10
            elif event.severity == "ERROR":
                score -= 5
            elif event.severity == "WARNING":
                score -= 2

            # Additional deductions for specific event types
            if event.event_type == "credential_exposure":
                score -= 20
            elif event.event_type == "authentication_failure":
                score -= 3
            elif event.event_type == "suspicious_activity":
                score -= 10

        return max(0, score)

    def _get_security_recommendations(self, events: List[SecurityEvent]) -> List[str]:
        """Get security recommendations based on recent events."""
        recommendations = []

        # Count event types
        event_counts = defaultdict(int)
        for event in events:
            event_counts[event.event_type] += 1

        # Generate recommendations
        if event_counts["authentication_failure"] > 5:
            recommendations.append(
                "High number of authentication failures detected. Review access patterns and consider implementing rate limiting."
            )

        if event_counts["credential_exposure"] > 0:
            recommendations.append(
                "Credential exposure detected. Rotate affected credentials immediately and review security practices."
            )

        if event_counts["validation_failure"] > 10:
            recommendations.append(
                "Multiple validation failures detected. Review input validation and consider implementing stricter controls."
            )

        if event_counts["suspicious_activity"] > 3:
            recommendations.append(
                "Suspicious activities detected. Review security logs and consider implementing additional monitoring."
            )

        if not recommendations:
            recommendations.append(
                "No significant security issues detected. Continue monitoring."
            )

        return recommendations


# Global security monitor instance
_security_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor


def log_security_event(
    event_type: str, severity: str, source: str, details: Dict[str, Any], **kwargs
) -> None:
    """Log security event using global monitor."""
    monitor = get_security_monitor()
    monitor.log_event(event_type, severity, source, details, **kwargs)
