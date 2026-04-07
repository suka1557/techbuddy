import os
from loguru import logger

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[2]  # .../techbuddy
logger.info(f"Base path: {ROOT_PATH}")

from configs.config import Config
from utils.download_whisper import download_whisper_model

# Load configuration
config = Config.from_yaml(os.path.join(ROOT_PATH, "src", "backend","configs/dev.yaml"))

# Load Model configuration
model_cfg = config.get("model", {})
model_name = model_cfg.get("model_name", "ggml-base.en.bin")
model_dir = model_cfg.get("model_dir", os.path.join(ROOT_PATH, "src", "backend", "models"))
#Download model if not already present
model_path = download_whisper_model(model_dir, model_name)
logger.info(f"Model ready at: {model_path}")