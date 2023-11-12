import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QShortcut,
    QScrollArea,
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

    def loadAndDisplayUML(self, filePath):
        # 创建 PlantUML 实例
        uml_image = plantuml.PlantUML(url="http://www.plantuml.com/plantuml/img/")

        # 处理文件并获取图像数据
        img_data = uml_image.processes_file(filePath)

        # 检查返回的数据是否为字节类型
        if isinstance(img_data, bytes):
            # 如果是字节数据，转换为 QImage
            image = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(image)
            self.imageLabel.setPixmap(pixmap)
        else:
            # 如果不是字节数据，打印错误信息或进行错误处理
            print("Failed to load or process the PlantUML file.")

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
