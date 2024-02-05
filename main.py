from central_app import CentralApp
from logger import setup_logging
import sys


def main():
    setup_logging()
    app = CentralApp(sys.argv)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
