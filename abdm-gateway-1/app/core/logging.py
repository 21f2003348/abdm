import sys 
from loguru import logger 

def configure_logging(log_level: str = "INFO"):
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False
    )