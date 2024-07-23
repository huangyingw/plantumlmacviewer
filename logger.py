import logging
import os


def setup_logging():
    # 获取日志文件的路径
    log_dir = os.path.expanduser("~/")
    log_file = os.path.join(log_dir, "plantumlmacviewer.log")

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,  # 将日志级别设置为DEBUG以捕获所有日志
        format="%(asctime)s %(levelname)s:%(message)s",
    )
