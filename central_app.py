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
from events import OpenWindowEvent
from file_change_handler import FileChangeHandler
from logger import setup_logging
import logging


class CentralApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.windows = []  # 存储所有打开的窗口
        self.fileWindowMap = {}  # 文件路径到窗口的映射
        self.observers = {}  # 目录到 Observer 的映射

        # 启动套接字监听线程
        socketThread = threading.Thread(target=self.listenToSocket)
        socketThread.daemon = True
        socketThread.start()

    def listenToSocket(self):
        host = "localhost"  # 或者其他适合您需求的主机地址
        port = 12345  # 选择一个适合的端口号

        # 创建套接字
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()

            logging.info(f"Listening on {host}:{port}")

            while True:
                # 等待连接
                conn, addr = s.accept()
                with conn:
                    logging.info(f"Connected by {addr}")

                    # 接收数据
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break

                        file_path = data.decode().strip()
                        logging.info(f"Received file path: {file_path}")

                        # 总是发送 OpenWindowEvent
                        QCoreApplication.postEvent(
                            self, OpenWindowEvent(file_path)
                        )

    def customEvent(self, event):
        if event.type() == OpenWindowEvent.EVENT_TYPE:
            filePath = event.filePath
            if filePath in self.fileWindowMap:
                window = self.fileWindowMap[filePath]
                window.raise_()
                window.activateWindow()
            else:
                self.openNewWindow(filePath)

    def openNewWindow(self, filePath=None):
        # 确保路径是规范化的
        if filePath and not filePath.startswith("fugitive:///"):
            filePath = os.path.abspath(filePath)

        # 如果文件已经打开，激活对应的窗口
        if filePath in self.fileWindowMap:
            window = self.fileWindowMap[filePath]
            logging.info(f"Activating existing window for {filePath}")
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

        # 新增代码：激活并将新窗口置于前台
        new_window.raise_()
        new_window.activateWindow()

    def startFileWatcher(self, filePath, viewer):
        if not filePath.startswith("fugitive:///"):
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
    focusSignal = pyqtSignal()

    def __init__(self, centralApp):
        super().__init__()
        self.centralApp = centralApp
        self.initUI()
        self.focusSignal.connect(self.postFocusProcessing)

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
        if not filePath.startswith("fugitive:///"):
            # 确保路径是规范化的
            filePath = os.path.abspath(filePath)
            self.centralApp.openNewWindow(filePath)

    def loadAndDisplayUML(self, filePath):
        temp_png_path = None
        temp_dir = None
        error_occurred = False

        try:
            self.previousApp = self.getActiveAppName()
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
            logging.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, check=True, capture_output=True)
            logging.info(f"PlantUML Output: {result.stdout}")

            # 统一的图像加载和显示逻辑
            self.displayImage(temp_png_path)

        except subprocess.CalledProcessError as e:
            logging.exception(f"Error during subprocess execution: {e}")
            self.imageLabel.setText("Error generating UML diagram.")
            error_occurred = True
            # 即使出现异常，也尝试执行 displayImage
            self.displayImage(temp_png_path)

        finally:
            # 删除临时 PNG 文件和目录
            if temp_png_path and os.path.exists(temp_png_path):
                try:
                    os.unlink(temp_png_path)
                except Exception as e:
                    logging.info(f"Error removing temp file: {e}")

            # 删除临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception as e:
                    logging.info(f"Error removing temp dir: {e}")

            # 发射信号
            self.focusSignal.emit()
            if error_occurred:
                return

    def displayImage(self, imagePath):
        logging.info(f"Loading PNG file: {imagePath}")
        self.imageLabel.clear()  # 清空现有图像
        image = QImage(imagePath)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.imageLabel.setPixmap(pixmap)
            logging.info("Image updated successfully.")
        else:
            self.imageLabel.setText(f"Failed to load the generated image.")
            logging.info("Failed to load the generated image.")

    def postFocusProcessing(self):
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()
        self.setFocusToApp(self.previousApp)

    def getActiveAppName(self):
        # 获取当前活动的应用程序的名称
        ws = AppKit.NSWorkspace.sharedWorkspace()
        frontmostApp = ws.frontmostApplication()
        return frontmostApp.localizedName()

    def setFocusToApp(self, appName):
        # 将焦点设置到指定的应用程序
        ws = AppKit.NSWorkspace.sharedWorkspace()
        for app in ws.runningApplications():
            if app.localizedName() == appName:
                app.activateWithOptions_(
                    AppKit.NSApplicationActivateIgnoringOtherApps
                )
                break

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
