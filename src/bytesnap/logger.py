from datetime import datetime
from enum import Enum
import sys
from typing import TextIO

from bytesnap.singleton import Singleton


class LoggerLevel(Enum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


class Logger(metaclass=Singleton):


    def __init__(self, to_stdout: bool, to_stderr: bool, file: TextIO = None) -> None:
        self.to_stdout = to_stdout
        self.to_stderr = to_stderr
        self.file = file
        self.level = LoggerLevel.DEBUG
        self.level_string = "DEBUG"


    def set_level(self, level: LoggerLevel) -> None:
        self.level = level
        if level.value == 1:
            self.level_string = "DEBUG"
        elif level.value == 2:
            self.level_string = "INFO"
        elif level.value == 3:
            self.level_string = "WARNING"
        else:
            self.level_string = "ERROR"


    def log_message(self, level: LoggerLevel, msg: str) -> None:
        if level.value >= self.level.value:
            time_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            txt = f'[{time_string}][{self.level_string}] {msg}\n'
            if self.to_stdout:
                sys.stdout.write(txt)
            if self.to_stderr:
                sys.stderr.write(txt)
            if self.file is not None:
                self.file.write(txt)


    @staticmethod
    def log(where: tuple[int, int] | None, level: LoggerLevel, msg: str) -> None:
        if where is None:
            Logger().log_message(level, f'{msg}')    
        else:
            Logger().log_message(level, f'at line {where[0]}, column {where[1]}: {msg}')
