import logging
import os


def setup_logging():
    # 获取当前文件的绝对路径
    current_file_path = os.path.abspath(__file__)
    # 获取当前文件所在的目录
    current_dir = os.path.dirname(current_file_path)
    # 创建日志文件路径，位于当前目录下
    log_file = os.path.join(current_dir, "plantumlviewerserver.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(message)s",
    )
