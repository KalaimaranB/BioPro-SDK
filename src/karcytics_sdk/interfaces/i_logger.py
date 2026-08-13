from typing import Protocol, runtime_checkable


@runtime_checkable
class ILogger(Protocol):
    """Abstract interface for logging."""

    def debug(self, msg: str) -> None:
        """Log a debug message."""
        ...

    def info(self, msg: str) -> None:
        """Log an informational message."""
        ...

    def warning(self, msg: str) -> None:
        """Log a warning message."""
        ...

    def error(self, msg: str, exception: Exception | None = None) -> None:
        """Log an error message, optionally with an exception trace."""
        ...

    def exception(self, msg: str) -> None:
        """Log an exception message."""
        ...
