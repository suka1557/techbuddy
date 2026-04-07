from __future__ import annotations

from pathlib import Path
import urllib.request
from urllib.error import HTTPError, URLError
from loguru import logger


_DEFAULT_SRC = "https://huggingface.co/ggerganov/whisper.cpp"
_DEFAULT_PFX = "resolve/main/ggml"
_TDRZ_SRC = "https://huggingface.co/akashmjn/tinydiarize-whisper.cpp"
_TDRZ_PFX = "resolve/main/ggml"

_MODELS = {
	"tiny",
	"tiny.en",
	"tiny-q5_1",
	"tiny.en-q5_1",
	"tiny-q8_0",
	"base",
	"base.en",
	"base-q5_1",
	"base.en-q5_1",
	"base-q8_0",
	"small",
	"small.en",
	"small.en-tdrz",
	"small-q5_1",
	"small.en-q5_1",
	"small-q8_0",
	"medium",
	"medium.en",
	"medium-q5_0",
	"medium.en-q5_0",
	"medium-q8_0",
	"large-v1",
	"large-v2",
	"large-v2-q5_0",
	"large-v2-q8_0",
	"large-v3",
	"large-v3-q5_0",
	"large-v3-turbo",
	"large-v3-turbo-q5_0",
	"large-v3-turbo-q8_0",
}


def available_models() -> list[str]:
	return sorted(_MODELS)


def download_whisper_model(target_dir: str | Path, model_name: str) -> Path:
	if model_name not in _MODELS:
		raise ValueError(
			f"Invalid model '{model_name}'. Choose from: {', '.join(available_models())}"
		)

	target_path = Path(target_dir)
	target_path.mkdir(parents=True, exist_ok=True)

	filename = f"ggml-{model_name}.bin"
	destination = target_path / filename
	if destination.exists():
		logger.debug(f"Model already exists at {destination}, skipping download.")
		return destination

	if "tdrz" in model_name:
		src, pfx = _TDRZ_SRC, _TDRZ_PFX
	else:
		src, pfx = _DEFAULT_SRC, _DEFAULT_PFX

	url = f"{src}/{pfx}-{model_name}.bin"
	logger.info(f"Downloading model '{model_name}' from {url} to {destination}...")
	_download_file(url, destination)
	return destination


def _download_file(url: str, destination: Path) -> None:
	try:
		with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
			while True:
				chunk = response.read(1024 * 1024)
				if not chunk:
					break
				handle.write(chunk)
	except (HTTPError, URLError, OSError) as exc:
		raise RuntimeError(f"Failed to download model from {url}: {exc}") from exc
