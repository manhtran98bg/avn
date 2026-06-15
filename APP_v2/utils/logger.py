from utils.pattern import Singleton
import logging

class ScreenFormatter(logging.Formatter):
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    YELLOW = "\x1b[33;20m"
    GREEN = "\x1b[32;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    format = f"{GREEN}%(asctime)s{RESET} - ""{0}%(levelname)s"\
        f"{RESET} [%(pathname)s:%(lineno)d - %(funcName)s()] -> "\
        "{0}%(message)s"f"{RESET}"

    FORMATS = {
        logging.DEBUG: format.format(GREY),
        logging.INFO: format.format(BLUE),
        logging.WARNING: format.format(YELLOW),
        logging.ERROR: format.format(RED),
        logging.CRITICAL: format.format(BOLD_RED)
    }

    def format(self, record: logging.LogRecord):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class FileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        FORMAT = "[%(asctime)s (%(pathname)s:%(lineno)d - %(funcName)s())] %(levelname)s -> %(message)s"
        return logging.Formatter(FORMAT).format(record)

class Logger(logging.Logger, metaclass=Singleton):
    """
    Create logger object for the first time to use
    """
        
    def __init__(self, level: str = 'info', to_screen: bool = True,
                 to_file: bool = False, file_name: str = None) -> None:
        """
        level: debug, info, warn, error, fatal
        file_name: required if to_file is True
        """
        super().__init__("")
        lvl_text = ["debug", "info", "warn", "error", "fatal"]
        lvl_int = [logging.DEBUG, logging.INFO, logging.WARN, logging.ERROR, logging.FATAL]
        lvl_val = lvl_int[lvl_text.index(level)]

        if to_screen:
            h = logging.StreamHandler()
            h.setLevel(lvl_val)
            h.setFormatter(ScreenFormatter())
            self.addHandler(h)
        if to_file:
            h = logging.FileHandler(file_name)
            h.setLevel(lvl_val)
            h.setFormatter(FileFormatter())
            self.addHandler(h)