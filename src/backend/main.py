import os
from loguru import logger

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[2]  # .../techbuddy
logger.info(f"Base path: {ROOT_PATH}")

from configs.config import Config
config = Config.from_yaml(os.path.join(ROOT_PATH, "src", "backend","configs/dev.yaml"))
model_cfg = config.get("model", {})