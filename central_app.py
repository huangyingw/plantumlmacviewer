from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QLabel,
    QShortcut,
    QFileDialog,
    QSizePolicy,
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QCoreApplication
from watchdog.observers import Observer
import sys
import threading
import socket
import os
from .events import OpenWindowEvent
from .file_change_handler import FileChangeHandler
from .logger import setup_logging

# CentralApp 类和 UMLViewer 类的代码从原文件中提取

if __name__ == "__main__":
    from main import main

    main()
