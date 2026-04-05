import logging


def setup_logging():
    logger = logging.getLogger("huntfact")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"huntfact.{name}")
