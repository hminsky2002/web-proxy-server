import logging as logger
from datetime import datetime

file_name = datetime.now().strftime("%Y-%m-%d")
logger.basicConfig(
    filename=f"/{file_name}.log",
    encoding="utf-8",
    filemode="a",
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logger.INFO,
)