from PyQt5.QtCore import QEvent


class OpenWindowEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, filePath):
        super().__init__(OpenWindowEvent.EVENT_TYPE)
        self.filePath = filePath
