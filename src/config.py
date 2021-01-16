import os

from environs import Env

# load .env file into os.environ
env = Env()
env.read_env()

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ROOT_PATH = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, ".data")

DEBUG = env.bool("DEBUG", False)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"json": {"()": "pythonjsonlogger.jsonlogger.JsonFormatter"}},
    "handlers": {"main": {"class": "logging.StreamHandler", "formatter": "json"}},
}
