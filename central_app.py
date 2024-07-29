from PyQt5.QtWidgets import (
    QDesktopWidget,
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
import tempfile
import threading
import socket
import os
from events import OpenWindowEvent
from file_change_handler import FileChangeHandler
from logger import setup_logging
import logging
import AppKit
import subprocess
import os
import glob


class CentralApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        logging.debug("CentralApp initialized")
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
                    data = b""
                    while True:
                        packet = conn.recv(4096)
                        if not packet:
                            break
                        data += packet

                    file_paths = (
                        data.decode().strip().split("\n")
                    )  # 分割接收到的文件路径
                    logging.info(f"Received file paths: {file_paths}")
                    QCoreApplication.postEvent(
                        self, OpenWindowEvent(file_paths)
                    )

    def customEvent(self, event):
        logging.debug(f"customEvent triggered with event type: {event.type()}")
        if event.type() == OpenWindowEvent.EVENT_TYPE:
            for filePath in event.filePaths:  # 循环遍历文件路径列表
                if filePath in self.fileWindowMap:
                    window = self.fileWindowMap[filePath]
                    window.raise_()
                    window.activateWindow()
                else:
                    self.openNewWindow(filePath)

    def openNewWindow(self, filePath=None):
        logging.debug(f"openNewWindow called with filePath: {filePath}")
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
        logging.debug(f"startFileWatcher called with filePath: {filePath}")
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
        logging.debug("UMLViewer initialized")
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

        # 将窗口放置在当前显示器上
        self.move_to_current_screen()

        # 窗口最大化
        self.showMaximized()

    def move_to_current_screen(self):
        main_window = (
            self.centralApp.windows[0] if self.centralApp.windows else None
        )
        if main_window:
            screen = QApplication.desktop().screenNumber(main_window)
        else:
            screen = QApplication.desktop().primaryScreen()

        rect = QApplication.desktop().screenGeometry(screen)
        self.setGeometry(rect)

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
        temp_dir = None
        try:
            self.previousApp = self.getActiveAppName()
            self.setFocusPolicy(Qt.NoFocus)
            # 在加载 UML 之前，设置窗口标题为文件名
            self.setWindowTitle(os.path.basename(filePath))
            plantuml_jar_path = self.get_plantuml_jar_path()

            temp_dir = tempfile.mkdtemp()
            base_name = os.path.basename(filePath)
            png_name = (
                base_name.replace(".puml", "").replace(" ", "_") + ".png"
            )
            temp_png_path = os.path.join(temp_dir, png_name)

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
            result = subprocess.run(command, capture_output=True, text=True)
            logging.info(f"PlantUML return code: {result.returncode}")
            logging.info(f"PlantUML Output: {result.stdout}")
            logging.info(f"PlantUML Error Output: {result.stderr}")
            logging.info(f"Temp directory contents: {os.listdir(temp_dir)}")

            # 查找生成的PNG文件
            generated_files = [
                f for f in os.listdir(temp_dir) if f.endswith(".png")
            ]
            if not generated_files:
                raise FileNotFoundError(f"No PNG file generated in {temp_dir}")

            actual_png_path = os.path.join(temp_dir, generated_files[0])
            logging.info(f"Found generated PNG file: {actual_png_path}")

            if os.path.getsize(actual_png_path) == 0:
                raise ValueError(
                    f"Generated PNG file is empty: {actual_png_path}"
                )

            self.displayImage(actual_png_path)

        except subprocess.CalledProcessError as e:
            logging.exception(f"Error during subprocess execution: {e}")
            self.imageLabel.setText(f"Error generating UML diagram: {e}")
        except FileNotFoundError as e:
            logging.exception(f"File not found: {e}")
            self.imageLabel.setText(f"Error: {e}")
        except ValueError as e:
            logging.exception(f"Invalid file: {e}")
            self.imageLabel.setText(f"Error: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error: {e}")
            self.imageLabel.setText(f"An unexpected error occurred: {e}")
        finally:
            self.focusSignal.emit()
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logging.error(f"Error removing temp dir: {e}")

    def get_plantuml_jar_path(self):
        plantuml_base_path = "/usr/local/Cellar/plantuml/"
        latest_version_path = max(
            glob.glob(os.path.join(plantuml_base_path, "*/")),
            key=os.path.getmtime,
        )
        return os.path.join(latest_version_path, "libexec/plantuml.jar")

    def displayImage(self, imagePath):
        logging.info(f"Loading PNG file: {imagePath}")
        self.imageLabel.clear()  # 清空现有图像
        image = QImage(imagePath)
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.imageLabel.setPixmap(pixmap)
            logging.info("Image updated successfully.")
        else:
            error_msg = f"Failed to load the generated image: {imagePath}"
            logging.error(error_msg)
            self.imageLabel.setText(error_msg)

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
