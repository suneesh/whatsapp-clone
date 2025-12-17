"""Comprehensive error handling and logging utilities."""

import logging
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .exceptions import (
    WhatsAppClientError,
    AuthenticationError,
    ValidationError,
    ConnectionError,
    CryptographyError,
    StorageError,
)


class LogLevel(str, Enum):
    """Logging level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorHandler:
    """Centralized error handling and logging."""

    # Singleton instance
    _instance: Optional["ErrorHandler"] = None

    def __new__(cls) -> "ErrorHandler":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize error handler."""
        if self._initialized:
            return

        self._initialized = True
        self.logger = logging.getLogger("whatsapp_client")
        self.error_history: list[Dict[str, Any]] = []
        self.max_history = 1000
        self.log_level = LogLevel.INFO
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level.value))

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        # Add handler if not already present
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.DEBUG)

    def set_log_level(self, level: LogLevel) -> None:
        """
        Set logging level.

        Args:
            level: LogLevel to set
        """
        self.log_level = level
        for handler in self.logger.handlers:
            handler.setLevel(getattr(logging, level.value))
        self.logger.setLevel(logging.DEBUG)

    def add_file_handler(self, log_file: str) -> None:
        """
        Add file logging handler.

        Args:
            log_file: Path to log file
        """
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[str] = None,
        severity: LogLevel = LogLevel.ERROR,
    ) -> None:
        """
        Handle and log an exception.

        Args:
            exception: Exception to handle
            context: Context information (function name, operation, etc.)
            severity: Log severity level
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "type": type(exception).__name__,
            "message": str(exception),
            "context": context,
            "severity": severity.value,
            "traceback": traceback.format_exc(),
        }

        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history:
            self.error_history.pop(0)

        # Log based on exception type
        if isinstance(exception, (AuthenticationError, ValidationError)):
            self.logger.warning(
                f"[{context}] {type(exception).__name__}: {exception}"
            )
        elif isinstance(exception, (ConnectionError, CryptographyError)):
            self.logger.error(
                f"[{context}] {type(exception).__name__}: {exception}"
            )
        elif isinstance(exception, StorageError):
            self.logger.error(
                f"[{context}] {type(exception).__name__}: {exception}"
            )
        else:
            self.logger.critical(
                f"[{context}] Unexpected error: {type(exception).__name__}: {exception}"
            )

    def log_debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def log_critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def get_error_history(
        self, count: int = 10, severity: Optional[LogLevel] = None
    ) -> list[Dict[str, Any]]:
        """
        Get recent error history.

        Args:
            count: Number of errors to return
            severity: Filter by severity level

        Returns:
            List of error dictionaries
        """
        history = self.error_history[-count:] if count else self.error_history
        if severity:
            history = [e for e in history if e["severity"] == severity.value]
        return history

    def clear_error_history(self) -> None:
        """Clear error history."""
        self.error_history.clear()

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of errors.

        Returns:
            Summary dictionary with error counts by type and severity
        """
        summary = {
            "total_errors": len(self.error_history),
            "by_type": {},
            "by_severity": {},
        }

        for error in self.error_history:
            # Count by type
            error_type = error["type"]
            summary["by_type"][error_type] = summary["by_type"].get(error_type, 0) + 1

            # Count by severity
            severity = error["severity"]
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

        return summary


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    return _error_handler


def configure_logging(
    log_level: LogLevel = LogLevel.INFO, log_file: Optional[str] = None
) -> None:
    """
    Configure logging globally.

    Args:
        log_level: Logging level
        log_file: Optional log file path
    """
    handler = get_error_handler()
    handler.set_log_level(log_level)
    if log_file:
        handler.add_file_handler(log_file)


# Convenience logging functions
def log_debug(message: str, **kwargs: Any) -> None:
    """Log debug message."""
    _error_handler.log_debug(message, **kwargs)


def log_info(message: str, **kwargs: Any) -> None:
    """Log info message."""
    _error_handler.log_info(message, **kwargs)


def log_warning(message: str, **kwargs: Any) -> None:
    """Log warning message."""
    _error_handler.log_warning(message, **kwargs)


def log_error(message: str, **kwargs: Any) -> None:
    """Log error message."""
    _error_handler.log_error(message, **kwargs)


def log_critical(message: str, **kwargs: Any) -> None:
    """Log critical message."""
    _error_handler.log_critical(message, **kwargs)


def handle_exception(
    exception: Exception,
    context: Optional[str] = None,
    severity: LogLevel = LogLevel.ERROR,
) -> None:
    """
    Handle and log an exception.

    Args:
        exception: Exception to handle
        context: Context information
        severity: Log severity level
    """
    _error_handler.handle_exception(exception, context, severity)
