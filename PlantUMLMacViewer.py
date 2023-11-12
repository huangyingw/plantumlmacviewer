import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence
from PyQt5.QtCore import Qt
import plantuml


class UMLViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("PlantUML Viewer")
        self.setGeometry(100, 100, 800, 600)

        # 容纳UML图像的滚动区域
        self.scrollArea = QScrollArea(self)
        self.setCentralWidget(self.scrollArea)

        # UML图像标签
        self.imageLabel = QLabel()
        self.scrollArea.setWidget(self.imageLabel)

        # 设置快捷键
        self.setupShortcuts()

    def setupShortcuts(self):
        # 设置快捷键以打开文件
        self.openFileShortcut = QKeySequence("Ctrl+O")
        self.addAction(self.openFileShortcut, self.openFile)

    def addAction(self, shortcut, function):
        # 创建动作并绑定快捷键
        action = self.scrollArea.addAction(shortcut)
        action.setShortcut(shortcut)
        action.triggered.connect(function)

    def openFile(self):
        # 使用文件对话框打开文件
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "PlantUML files (*.puml)"
        )
        if filePath:
            self.loadAndDisplayUML(filePath)

    def loadAndDisplayUML(self, filePath):
        # 渲染PlantUML图表
        uml_image = plantuml.PlantUML(
            url="http://www.plantuml.com/plantuml/img/"
        )
        img = uml_image.processes_file(filePath)
        image = QImage.fromData(img)
        pixmap = QPixmap.fromImage(image)
        self.imageLabel.setPixmap(pixmap)

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
