import logging
import os

def setup_logging():
    log_file = os.path.expanduser("~/application.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(message)s",
    )
