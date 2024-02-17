import json
import os
import inquirer
from inquirer.themes import GreenPassion
from pprint import pprint
from pathlib import Path
from bytesnap.generator_cpp import GeneratorCPP
from bytesnap.logger import Logger, LoggerLevel


LOCAL_CFG = '.bytesnap.cfg'
PROJECT_NAME = 'project name'
VERSION_STRING = 'version string'
DESCRIPTION = 'description'
AUTHOR = 'author'
SOURCE_IDL = 'source idl'
OUTPUT_DIR = 'output dir'
BOOST_DIR = 'boost dir'
MAX_MESSAGE_SIZE = 'max message size'


def read_local_cfg() -> dict[str, str] | None:
    path = Path(LOCAL_CFG)
    if not path.exists():
        return None
    with open(LOCAL_CFG, 'r') as file:
        return json.load(file)


def save_local_cfg(cfg: dict[str, str]) -> None:
    with open(LOCAL_CFG, 'w') as file:
        json.dump(cfg, file)


if __name__ == "__main__":
    Logger(True, False).set_level(LoggerLevel.INFO)

    this_path = os.path.dirname(os.path.realpath(__file__))

    cfg = read_local_cfg()

    questions = [
        inquirer.Text(PROJECT_NAME, message="Project name", default=None if cfg is None else cfg[PROJECT_NAME]),
        inquirer.Text(VERSION_STRING, message="Version string", default=None if cfg is None else cfg[VERSION_STRING]),
        inquirer.Text(DESCRIPTION, message="Description", default=None if cfg is None else cfg[DESCRIPTION]),
        inquirer.Text(AUTHOR, message="Author", default=None if cfg is None else cfg[AUTHOR]),
        inquirer.Path(SOURCE_IDL, message="Source IDL file", path_type=inquirer.Path.FILE, 
                        exists=True, normalize_to_absolute_path=True, default=None if cfg is None else cfg[SOURCE_IDL]),
        inquirer.Path(OUTPUT_DIR, message="Output dir", path_type=inquirer.Path.DIRECTORY,
                        exists=True, normalize_to_absolute_path=True, default=None if cfg is None else cfg[OUTPUT_DIR]),
        inquirer.Path(BOOST_DIR, message="Boost dir", path_type=inquirer.Path.DIRECTORY,
                        exists=True, normalize_to_absolute_path=True, default=None if cfg is None else cfg[BOOST_DIR]),
        inquirer.Text(MAX_MESSAGE_SIZE, message="Maximum size of the message in bytes", 
                      default=None if cfg is None else cfg[MAX_MESSAGE_SIZE],
                      validate=lambda answers, max_msg_size: max_msg_size.isdigit()),
    ]

    answers = inquirer.prompt(questions, theme=GreenPassion())
    save_local_cfg(answers)

    try:
        idl_path = Path(answers[SOURCE_IDL]).resolve()
        output_path = Path(answers[OUTPUT_DIR]).resolve()
        boost_path = Path(answers[BOOST_DIR]).resolve()

        gen = GeneratorCPP(
            project=answers[PROJECT_NAME],
            version=answers[VERSION_STRING],
            description=answers[DESCRIPTION],
            author=answers[AUTHOR],
            rpc_version='0.1.0'
        )
        gen.generate(
            idl_path,
            output_path,
            boost_path,
            answers[MAX_MESSAGE_SIZE]
        )
    except TypeError:
        exit
