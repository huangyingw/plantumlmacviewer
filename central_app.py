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

from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
    QEvent,
    QCoreApplication,
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
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer
import os
import glob

# 使用 pyobjc 导入 AppKit
from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps

setup_logging()
logging.info("central_app.py 日志系统初始化完成")


class CentralApp(QApplication):
    def __init__(self, argv):
        logging.debug("开始初始化 CentralApp")
        super().__init__(argv)
        self.windows = []
        self.fileWindowMap = {}
        self.observers = {}
        self.socketThread = None
        logging.debug("CentralApp 初始化完成")

    def start(self):
        logging.debug("准备启动套接字监听线程")
        self.socketThread = threading.Thread(target=self.listenToSocket)
        self.socketThread.daemon = True
        self.socketThread.start()
        logging.debug("套接字监听线程启动完成")

    def createNewWindow(self, filePath):
        logging.debug(f"创建新窗口，文件路径：{filePath}")
        new_window = UMLViewer(self)
        self.windows.append(new_window)
        new_window.show()
        new_window.raise_()
        new_window.activateWindow()
        new_window.loadAndDisplayUML(filePath)
        self.fileWindowMap[filePath] = new_window
        self.startFileWatcher(filePath, new_window)
        return new_window

    def listenToSocket(self):
        host = "localhost"
        port = 12345

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            logging.info(f"Listening on {host}:{port}")

            while True:
                try:
                    conn, addr = s.accept()
                    with conn:
                        logging.info(f"Connected by {addr}")
                        data = conn.recv(4096).decode().strip()
                        file_paths = data.split("\n")
                        logging.info(f"Received file paths: {file_paths}")
                        for file_path in file_paths:
                            QCoreApplication.postEvent(
                                self, OpenWindowEvent([file_path])
                            )
                except Exception as e:
                    logging.error(f"Socket error: {str(e)}")

    def customEvent(self, event):
        logging.debug(f"customEvent triggered with event type: {event.type()}")
        if event.type() == OpenWindowEvent.EVENT_TYPE:
            for filePath in event.filePaths:
                try:
                    self.openOrActivateWindow(filePath)
                except Exception as e:
                    logging.error(
                        f"Error opening or activating window for {filePath}: {str(e)}"
                    )

    def openOrActivateWindow(self, filePath):
        logging.debug(f"openOrActivateWindow called with filePath: {filePath}")
        try:
            if filePath and not filePath.startswith("fugitive:///"):
                filePath = os.path.abspath(filePath)

            if filePath in self.fileWindowMap:
                window = self.fileWindowMap[filePath]
                logging.info(f"Activating existing window for {filePath}")
                window.raise_()
                window.activateWindow()
                QCoreApplication.processEvents()
            else:
                self.createNewWindow(filePath)

        except Exception as e:
            logging.error(f"Error in openOrActivateWindow: {str(e)}")

    def startFileWatcher(self, filePath, viewer):
        logging.debug(f"startFileWatcher called with filePath: {filePath}")
        if not filePath.startswith("fugitive:///"):
            filePath = os.path.abspath(filePath)
        directory = os.path.dirname(filePath)

        if directory in self.observers:
            event_handler = FileChangeHandler(viewer, filePath)
            self.observers[directory].schedule(
                event_handler, directory, recursive=False
            )
        else:
            observer = Observer()
            self.observers[directory] = observer
            event_handler = FileChangeHandler(viewer, filePath)
            observer.schedule(event_handler, directory, recursive=False)
            observer.start()

    def exec_(self):
        logging.info("Entering main event loop")
        try:
            return super().exec_()
        except Exception as e:
            logging.critical(f"Unhandled exception in main loop: {str(e)}")
            return 1


class UMLViewer(QMainWindow):
    focusSignal = pyqtSignal()

    def setFocusToApp(self, appName):
        try:
            ws = NSWorkspace.sharedWorkspace()
            running_apps = ws.runningApplications()
            for app in running_apps:
                if app.localizedName() == appName:
                    app.activateWithOptions_(
                        NSApplicationActivateIgnoringOtherApps
                    )
                    break
        except Exception as e:
            logging.error(f"Error setting focus to app {appName}: {str(e)}")

    def __init__(self, centralApp):
        logging.debug("开始初始化 UMLViewer")
        super().__init__()
        self.centralApp = centralApp
        self.previousApp = None
        self.initUI()
        self.focusSignal.connect(self.postFocusProcessing)
        logging.debug("UMLViewer 初始化完成")

    def initUI(self):
        logging.debug("开始初始化 UI")
        self.setWindowTitle("PlantUML Viewer")
        self.setGeometry(100, 100, 800, 600)
        logging.debug("UI 初始化完成")

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
        screen = QApplication.desktop().primaryScreen()
        rect = QApplication.desktop().screenGeometry(screen)
        self.setGeometry(rect)

    def setupShortcuts(self):
        # 打开文件快捷键
        self.openFileShortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.openFileShortcut.activated.connect(self.openFile)
        logging.debug("Open file shortcut (Ctrl+O) set up")

        # 关闭窗口快捷键
        self.closeWindowShortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.closeWindowShortcut.activated.connect(self.close)
        logging.debug("Close window shortcut (Ctrl+W) set up")

        # 添加复制窗口截图到剪贴板的快捷键（Command+C）
        self.copyShortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copyShortcut.activated.connect(self.copyWindowToClipboard)
        logging.debug("Copy window shortcut (Command+C) set up")

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
        try:
            self.raise_()
            self.activateWindow()
            QApplication.processEvents()
            if self.previousApp:
                self.setFocusToApp(self.previousApp)
            self.previousApp = None
        except Exception as e:
            logging.error(f"Error in postFocusProcessing: {str(e)}")

    def getActiveAppName(self):
        ws = NSWorkspace.sharedWorkspace()
        frontmostApp = ws.frontmostApplication()
        return frontmostApp.localizedName()

    def copyWindowToClipboard(self):
        try:
            logging.info("开始复制窗口截图到剪贴板")
            # 截取当前窗口的截图
            pixmap = self.grab()
            if pixmap.isNull():
                logging.error("截图失败，pixmap 为空")
                return

            # 获取系统剪贴板
            clipboard = QApplication.clipboard()
            # 将截图复制到剪贴板
            clipboard.setPixmap(pixmap, mode=clipboard.Clipboard)
            logging.info("窗口截图已复制到剪贴板")
        except Exception as e:
            logging.exception(f"复制窗口截图到剪贴板时发生异常: {e}")

    def closeEvent(self, event):
        logging.debug("Close event triggered")
        # Remove this window from the centralApp's windows list
        if self in self.centralApp.windows:
            self.centralApp.windows.remove(self)

        # Remove this window from the fileWindowMap
        for file_path, window in list(self.centralApp.fileWindowMap.items()):
            if window == self:
                del self.centralApp.fileWindowMap[file_path]

        # Accept the close event
        event.accept()


def main():
    logging.info("central_app.py 开始执行")
    try:
        app = CentralApp(sys.argv)
        app.start()  # 只启动套接字监听线程，不创建初始窗口
        return app.exec_()
    except Exception as e:
        logging.exception(f"发生未处理的异常: {str(e)}")
        return 1
    finally:
        logging.info("central_app.py 执行结束")


if __name__ == "__main__":
    sys.exit(main())
