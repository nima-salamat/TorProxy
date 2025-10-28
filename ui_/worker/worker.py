from PySide6.QtCore import Signal, QObject, QRunnable, Slot
from .utils import QRWorkerSignals

    
class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = QRWorkerSignals()

    
    @Slot()
    def run(self):
        
        try:
            self.signals.started.emit()
            result = self.fn(*self.args, **self.kwargs)      
            result = "" if result == None else result
            self.signals.finished.emit(str(result))
        except Exception as e:
            self.signals.error.emit(str(e))
            
            