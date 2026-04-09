"""
Stream que redireciona sys.stdout/sys.stderr para a GUI via Qt signals.

Usado pelo AutomationWorker durante a execução: tudo que a automação
imprime com print() aparece no QPlainTextEdit da aba Executar.
"""

import sys
from PySide6.QtCore import QObject, Signal


class LogStream(QObject):
    """Substitui sys.stdout: cada write() emite um signal line(str)."""

    line = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer = ""

    def write(self, text):
        if not text:
            return
        # Acumula até encontrar newline, depois emite linha por linha
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.line.emit(line)

    def flush(self):
        if self._buffer:
            self.line.emit(self._buffer)
            self._buffer = ""

    def isatty(self):
        return False


class StdoutRedirector:
    """Context manager que substitui sys.stdout/sys.stderr por um LogStream."""

    def __init__(self, log_stream: LogStream):
        self.log_stream = log_stream
        self._old_stdout = None
        self._old_stderr = None

    def __enter__(self):
        self._old_stdout = sys.stdout
        self._old_stderr = sys.stderr
        sys.stdout = self.log_stream
        sys.stderr = self.log_stream
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.log_stream.flush()
        except Exception:
            pass
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr
        return False
