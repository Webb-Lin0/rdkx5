from __future__ import annotations

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal


class WorkerSignals(QObject):
    success = pyqtSignal(object)
    error = pyqtSignal(str)


class JsonWorker(QRunnable):
    def __init__(self, run_fn):
        super().__init__()
        self.run_fn = run_fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.success.emit(self.run_fn())
        except Exception as exc:
            self.signals.error.emit(str(exc))

