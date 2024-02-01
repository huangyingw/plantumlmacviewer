from .central_app import CentralApp
import sys


def main():
    setup_logging()
    app = CentralApp(sys.argv)
    app.openNewWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
