import logging
import os
import sys


PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_OUTPUT_DIR = os.path.join(PACKAGE_DIR, "output")

logger = logging.getLogger("news_agent")


def setup_logging(level=logging.INFO):
    root = logging.getLogger("news_agent")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)


def safe_print(text):
    sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
    sys.stdout.buffer.flush()
