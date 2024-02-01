from central_app import CentralApp
from logger import setup_logging
import sys


def main():
    setup_logging()
    app = CentralApp(sys.argv)
    app.openNewWindow()  # 打开初始窗口
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
