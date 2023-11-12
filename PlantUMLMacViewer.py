from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QShortcut,
    QScrollArea,
    QFileDialog,
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt, QTemporaryFile
import plantuml
import subprocess
import os


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, viewer, filePath):
        super().__init__()
        self.viewer = viewer
        self.filePath = filePath

    def on_modified(self, event):
        # 当监控的文件被修改时，调用 viewer 的 loadAndDisplayUML 方法
        if event.src_path == self.filePath:
            self.viewer.loadAndDisplayUML(self.filePath)


class UMLViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("PlantUML Viewer")

        # 容纳UML图像的滚动区域
        self.scrollArea = QScrollArea(self)
        self.setCentralWidget(self.scrollArea)

        # UML图像标签
        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)  # 居中对齐
        self.imageLabel.setScaledContents(True)  # 允许图像根据标签大小缩放
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setWidgetResizable(True)  # 允许滚动区域适应内容大小

        # 设置快捷键
        self.setupShortcuts()

        # 窗口最大化
        self.showMaximized()

    def setupShortcuts(self):
        # 使用 QShortcut 设置快捷键
        self.openFileShortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.openFileShortcut.activated.connect(self.openFile)

    def openFile(self):
        # 使用文件对话框打开文件
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "PlantUML files (*.puml)"
        )
        if filePath:
            self.loadAndDisplayUML(filePath)
            self.startFileWatcher(filePath)

    def startFileWatcher(self, filePath):
        # 设置文件监控
        self.event_handler = FileChangeHandler(self, filePath)
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler, os.path.dirname(filePath), recursive=False
        )
        self.observer.start()

    def loadAndDisplayUML(self, filePath):
        plantuml_jar_path = "/usr/local/Cellar/plantuml/1.2023.12/libexec/plantuml.jar"  # 替换为您的 PlantUML jar 文件路径

        # 获取 PNG 文件的输出路径
        output_png_path = filePath.replace(".puml", ".png")
        print(f"Expected PNG file at: {output_png_path}")

        # 构造 PlantUML 命令
        command = ["java", "-jar", plantuml_jar_path, "-tpng", filePath]
        print(f"Running command: {' '.join(command)}")

        # 执行命令
        subprocess.run(command)

        # 加载生成的 PNG 文件
        print(f"Loading PNG file: {output_png_path}")
        pixmap = QPixmap(output_png_path)
        if not pixmap.isNull():
            print("PNG file loaded successfully, updating the label.")
            self.imageLabel.setPixmap(pixmap)
        else:
            print("Failed to generate or load the PlantUML image.")

    def keyPressEvent(self, event):
        # 处理快捷键事件
        if event.key() == Qt.Key_Plus:
            # 缩放代码
            pass
        elif event.key() == Qt.Key_Minus:
            # 缩放代码
            pass
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = UMLViewer()
    viewer.show()
    sys.exit(app.exec_())
