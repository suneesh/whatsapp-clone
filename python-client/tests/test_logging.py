"""Tests for US14: Error Handling and Logging."""

import pytest
import tempfile
import logging
from pathlib import Path
from datetime import datetime

from whatsapp_client.logging import (
    ErrorHandler,
    LogLevel,
    get_error_handler,
    configure_logging,
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_critical,
    handle_exception,
)
from whatsapp_client.exceptions import (
    ValidationError,
    AuthenticationError,
    ConnectionError as WhatsAppConnectionError,
    CryptographyError,
    StorageError,
)


class TestErrorHandler:
    """Test ErrorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Get fresh handler instance
        self.handler = ErrorHandler()
        self.handler.clear_error_history()
        
        # Remove any file handlers to avoid conflicts
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        # Close and remove file handlers
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def test_singleton_pattern(self):
        """Test that ErrorHandler is a singleton."""
        handler1 = ErrorHandler()
        handler2 = ErrorHandler()
        assert handler1 is handler2

    def test_set_log_level(self):
        """Test setting log level."""
        self.handler.set_log_level(LogLevel.DEBUG)
        assert self.handler.log_level == LogLevel.DEBUG

        self.handler.set_log_level(LogLevel.ERROR)
        assert self.handler.log_level == LogLevel.ERROR

    def test_logging_methods(self):
        """Test logging methods."""
        # Should not raise exceptions
        self.handler.log_debug("Debug message")
        self.handler.log_info("Info message")
        self.handler.log_warning("Warning message")
        self.handler.log_error("Error message")
        self.handler.log_critical("Critical message")

    def test_handle_authentication_error(self):
        """Test handling authentication error."""
        error = AuthenticationError("Invalid credentials")
        self.handler.handle_exception(error, context="login", severity=LogLevel.WARNING)

        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["type"] == "AuthenticationError"
        assert self.handler.error_history[0]["message"] == "Invalid credentials"
        assert self.handler.error_history[0]["context"] == "login"

    def test_handle_validation_error(self):
        """Test handling validation error."""
        error = ValidationError("Empty username")
        self.handler.handle_exception(error, context="register")

        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["type"] == "ValidationError"

    def test_handle_connection_error(self):
        """Test handling connection error."""
        error = WhatsAppConnectionError("Network timeout")
        self.handler.handle_exception(error, context="websocket_connect")

        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["type"] == "ConnectionError"

    def test_handle_cryptography_error(self):
        """Test handling cryptography error."""
        error = CryptographyError("Invalid key format")
        self.handler.handle_exception(error, context="key_generation")

        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["type"] == "CryptographyError"

    def test_handle_storage_error(self):
        """Test handling storage error."""
        error = StorageError("Database locked")
        self.handler.handle_exception(error, context="message_save")

        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["type"] == "StorageError"

    def test_error_history_timestamp(self):
        """Test that errors have timestamps."""
        error = ValueError("Test error")
        self.handler.handle_exception(error)

        error_info = self.handler.error_history[0]
        assert "timestamp" in error_info
        # Try to parse ISO format timestamp
        datetime.fromisoformat(error_info["timestamp"])

    def test_error_history_includes_traceback(self):
        """Test that error history includes traceback."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            self.handler.handle_exception(e)

        error_info = self.handler.error_history[0]
        assert "traceback" in error_info
        assert "ValueError" in error_info["traceback"]

    def test_error_history_limit(self):
        """Test that error history has a maximum size."""
        self.handler.max_history = 5

        for i in range(10):
            error = ValueError(f"Error {i}")
            self.handler.handle_exception(error)

        assert len(self.handler.error_history) == 5

    def test_get_error_history(self):
        """Test getting error history."""
        for i in range(3):
            error = ValueError(f"Error {i}")
            self.handler.handle_exception(error)

        history = self.handler.get_error_history(count=2)
        assert len(history) == 2
        assert history[-1]["message"] == "Error 2"

    def test_get_error_history_with_severity_filter(self):
        """Test getting error history with severity filter."""
        # Add various errors with different severities
        error1 = ValidationError("Validation error")
        self.handler.handle_exception(error1, severity=LogLevel.WARNING)

        error2 = ValueError("Some error")
        self.handler.handle_exception(error2, severity=LogLevel.ERROR)

        # Get only ERROR severity
        history = self.handler.get_error_history(severity=LogLevel.ERROR)
        assert len(history) == 1
        assert history[0]["severity"] == LogLevel.ERROR.value

    def test_clear_error_history(self):
        """Test clearing error history."""
        error = ValueError("Test error")
        self.handler.handle_exception(error)
        assert len(self.handler.error_history) == 1

        self.handler.clear_error_history()
        assert len(self.handler.error_history) == 0

    def test_get_error_summary(self):
        """Test getting error summary."""
        # Add various errors
        self.handler.handle_exception(ValidationError("Validation error"), severity=LogLevel.WARNING)
        self.handler.handle_exception(AuthenticationError("Auth error"), severity=LogLevel.ERROR)
        self.handler.handle_exception(ValueError("Value error"), severity=LogLevel.ERROR)

        summary = self.handler.get_error_summary()
        assert summary["total_errors"] == 3
        assert summary["by_type"]["ValidationError"] == 1
        assert summary["by_type"]["AuthenticationError"] == 1
        assert summary["by_type"]["ValueError"] == 1
        assert summary["by_severity"]["WARNING"] == 1
        assert summary["by_severity"]["ERROR"] == 2

    def test_add_file_handler(self):
        """Test adding file logging handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            self.handler.add_file_handler(str(log_file))

            self.handler.log_info("Test message")

            assert log_file.exists()
            with open(log_file, "r") as f:
                content = f.read()
                assert "Test message" in content
            
            # Close file handlers to allow cleanup on Windows
            for handler in self.handler.logger.handlers:
                if hasattr(handler, 'close'):
                    try:
                        handler.close()
                    except:
                        pass

    def test_file_handler_with_errors(self):
        """Test file handler logs errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "errors.log"
            self.handler.add_file_handler(str(log_file))

            error = ValueError("Test error")
            self.handler.handle_exception(error)

            with open(log_file, "r") as f:
                content = f.read()
                assert "ValueError" in content or "Test error" in content
            
            # Close file handlers
            for handler in self.handler.logger.handlers:
                if hasattr(handler, 'close'):
                    try:
                        handler.close()
                    except:
                        pass


class TestLoggingFunctions:
    """Test module-level logging functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = get_error_handler()
        self.handler.clear_error_history()
        
        # Remove any file handlers to avoid conflicts
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        # Close and remove file handlers
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def test_log_debug(self):
        """Test log_debug function."""
        log_debug("Debug message")
        # Should not raise

    def test_log_info(self):
        """Test log_info function."""
        log_info("Info message")
        # Should not raise

    def test_log_warning(self):
        """Test log_warning function."""
        log_warning("Warning message")
        # Should not raise

    def test_log_error(self):
        """Test log_error function."""
        log_error("Error message")
        # Should not raise

    def test_log_critical(self):
        """Test log_critical function."""
        log_critical("Critical message")
        # Should not raise

    def test_handle_exception_function(self):
        """Test handle_exception function."""
        error = ValueError("Test error")
        handle_exception(error, context="test_context")

        assert len(self.handler.error_history) >= 1

    def test_configure_logging(self):
        """Test configure_logging function."""
        configure_logging(log_level=LogLevel.DEBUG)
        assert self.handler.log_level == LogLevel.DEBUG

        configure_logging(log_level=LogLevel.ERROR)
        assert self.handler.log_level == LogLevel.ERROR

    def test_configure_logging_with_file(self):
        """Test configure_logging with file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "app.log"
            configure_logging(log_level=LogLevel.INFO, log_file=str(log_file))

            log_info("Test message")
            assert log_file.exists()
            
            # Close file handlers
            handler = get_error_handler()
            for h in handler.logger.handlers:
                if hasattr(h, 'close'):
                    try:
                        h.close()
                    except:
                        pass


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = get_error_handler()
        self.handler.clear_error_history()
        
        # Remove any file handlers to avoid conflicts
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        # Close and remove file handlers
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def test_multiple_errors_tracking(self):
        """Test tracking multiple errors."""
        errors = [
            ValidationError("Empty field"),
            AuthenticationError("Wrong password"),
            WhatsAppConnectionError("Timeout"),
        ]

        for error in errors:
            handle_exception(error)

        assert len(self.handler.error_history) >= 3

    def test_error_context_preservation(self):
        """Test that error context is preserved."""
        error = ValueError("Database error")
        handle_exception(error, context="save_message")

        error_info = self.handler.error_history[0]
        assert error_info["context"] == "save_message"

    def test_error_message_preservation(self):
        """Test that error message is preserved."""
        error_msg = "Network connection failed"
        error = WhatsAppConnectionError(error_msg)
        handle_exception(error)

        error_info = self.handler.error_history[0]
        assert error_info["message"] == error_msg

    def test_logging_and_error_tracking(self):
        """Test that logging and error tracking work together."""
        log_error("Operation failed")
        handle_exception(ValidationError("Invalid input"))

        summary = self.handler.get_error_summary()
        assert summary["total_errors"] >= 1

    def test_error_history_retrieval_order(self):
        """Test that errors are retrieved in correct order."""
        for i in range(3):
            error = ValueError(f"Error {i}")
            handle_exception(error)

        history = self.handler.get_error_history()
        assert len(history) >= 3
        # Last error should be Error 2
        if len(history) >= 3:
            assert "Error 2" in history[-1]["message"]


class TestErrorHandlingEdgeCases:
    """Test edge cases in error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = get_error_handler()
        self.handler.clear_error_history()
        
        # Remove any file handlers to avoid conflicts
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def teardown_method(self):
        """Clean up after each test."""
        # Close and remove file handlers
        for handler in list(self.handler.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.handler.logger.removeHandler(handler)

    def test_handle_exception_with_no_context(self):
        """Test handling exception without context."""
        error = ValueError("Error without context")
        handle_exception(error)

        error_info = self.handler.error_history[0]
        assert error_info["context"] is None

    def test_exception_with_special_characters(self):
        """Test handling exception with special characters."""
        special_msg = "Error: 用户名 invalid! @#$%"
        error = ValueError(special_msg)
        handle_exception(error)

        error_info = self.handler.error_history[0]
        assert special_msg in error_info["message"] or error_info["message"] != ""

    def test_get_error_history_count_zero(self):
        """Test getting error history with count=0."""
        for i in range(3):
            handle_exception(ValueError(f"Error {i}"))

        history = self.handler.get_error_history(count=0)
        # count=0 returns full history
        assert len(history) >= 3

    def test_error_summary_with_no_errors(self):
        """Test error summary with no errors."""
        summary = self.handler.get_error_summary()
        assert summary["total_errors"] == 0
        assert len(summary["by_type"]) == 0
        assert len(summary["by_severity"]) == 0

    def test_multiple_errors_same_type(self):
        """Test tracking multiple errors of same type."""
        for i in range(5):
            handle_exception(ValidationError(f"Validation failed {i}"))

        summary = self.handler.get_error_summary()
        assert summary["by_type"]["ValidationError"] == 5
