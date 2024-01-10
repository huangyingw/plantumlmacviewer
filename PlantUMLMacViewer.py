from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QScrollArea,
    QShortcut,
    QSizePolicy,
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


class CentralApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.windows = []  # 存储所有打开的窗口
        self.fileWindowMap = {}  # 文件路径到窗口的映射
        self.observers = {}  # 目录到 Observer 的映射

    def openNewWindow(self, filePath=None):
        # 确保路径是规范化的
        if filePath:
            filePath = os.path.abspath(filePath)

        # 如果文件已经打开，激活对应的窗口
        if filePath in self.fileWindowMap:
            window = self.fileWindowMap[filePath]
            print(f"Activating existing window for {filePath}")
            window.raise_()
            window.activateWindow()
            QApplication.processEvents()  # 处理事件队列
            return

        # 创建新窗口并将其添加到窗口列表和文件映射中
        new_window = UMLViewer(self)
        self.windows.append(new_window)
        if filePath:
            self.fileWindowMap[filePath] = new_window
            new_window.loadAndDisplayUML(filePath)
            self.startFileWatcher(filePath, new_window)
        new_window.show()

    def startFileWatcher(self, filePath, viewer):
        # 确保路径是规范化的
        filePath = os.path.abspath(filePath)
        # 获取目录路径
        directory = os.path.dirname(filePath)

        # 检查此目录是否已经有一个监控器，如果有，只需添加事件处理器，而不是创建新的监控器
        if directory in self.observers:
            # 为已存在的监控器添加事件处理器
            event_handler = FileChangeHandler(viewer, filePath)
            self.observers[directory].schedule(
                event_handler, directory, recursive=False
            )
        else:
            # 创建新的 Observer
            observer = Observer()
            self.observers[directory] = observer
            event_handler = FileChangeHandler(viewer, filePath)
            observer.schedule(event_handler, directory, recursive=False)
            observer.start()


class UMLViewer(QMainWindow):
    def __init__(self, centralApp):
        super().__init__()
        self.centralApp = centralApp
        self.initUI()

    def initUI(self):
        self.setWindowTitle("PlantUML Viewer")

        # 容纳UML图像的滚动区域
        self.scrollArea = QScrollArea(self)
        self.setCentralWidget(self.scrollArea)

        # UML图像标签
        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)  # 居中对齐

        # 设置图像的尺寸策略，使其能够根据可用空间自动调整大小
        self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
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
        # 修改 openFile 方法以支持在新窗口中打开文件
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "PlantUML files (*.puml)"
        )
        if filePath:
            # 确保路径是规范化的
            filePath = os.path.abspath(filePath)
            self.centralApp.openNewWindow(filePath)

    def loadAndDisplayUML(self, filePath):
        self.setFocusPolicy(Qt.NoFocus)
        # 在加载 UML 之前，设置窗口标题为文件名
        self.setWindowTitle(os.path.basename(filePath))
        plantuml_jar_path = "/usr/local/Cellar/plantuml/1.2023.13/libexec/plantuml.jar"  # 替换为您的 PlantUML jar 文件路径

        # 使用临时文件来保存生成的 PNG
        temp_dir = tempfile.mkdtemp()  # 创建临时目录
        temp_png_path = os.path.join(
            temp_dir, os.path.basename(filePath).replace(".puml", ".png")
        )

        # 更新 PlantUML 命令以使用临时目录
        command = [
            "java",
            "-jar",
            plantuml_jar_path,
            "-tpng",
            "-o",
            temp_dir,
            filePath,
        ]
        print(f"Running command: {' '.join(command)}")

        # 执行命令
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            # 在这里可以添加更多的用户通知逻辑，如弹出对话框
            return
        except Exception as e:
            print(f"Unexpected error: {e}")
            # 同样可以添加用户通知逻辑
            return

        print(f"Loading PNG file: {temp_png_path}")
        self.imageLabel.clear()  # 清空现有图像
        image = QImage(temp_png_path)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.imageLabel.setPixmap(pixmap)
            print("Image updated successfully.")
        else:
            print("Failed to load the image.")

            # 清理临时文件
            os.unlink(temp_png_path)
            os.rmdir(temp_dir)

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
    app = CentralApp(sys.argv)
    app.openNewWindow()  # 打开初始窗口
    sys.exit(app.exec_())
