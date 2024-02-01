from PyQt5.QtCore import QEvent


class OpenWindowEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, filePaths):
        super().__init__(OpenWindowEvent.EVENT_TYPE)
        self.filePaths = filePaths  # filePaths 现在是一个列表
