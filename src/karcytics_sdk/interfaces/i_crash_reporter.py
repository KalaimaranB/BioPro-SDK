from typing import Protocol, runtime_checkable


@runtime_checkable
class ICrashReporter(Protocol):
    """Abstract interface for reporting errors to the Hub's diagnostic engine.

    Implemented today by both the Hub's real `karcytics.core.diagnostics.
    DiagnosticEngine` (in-process plugins reach it indirectly via their own
    logger and the AutoReportHandler) and `karcytics_sdk.plugin.
    runtime_services.DiagnosticsForwarder` (isolated plugins, which have no
    other route back to the Hub's diagnostics engine at all). Call from
    inside the `except:` block handling `exception` so a real traceback is
    captured, not just the exception's message.
    """

    def report_error(
        self,
        message: str,
        exception: BaseException | None = None,
        plugin_id: str | None = None,
        fatal: bool = False,
    ) -> None:
        """Report an error to the Hub's diagnostic engine."""
        ...
