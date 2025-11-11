"""Model management utilities for downloading and caching AI models."""

import hashlib
import os
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class ModelManager:
    """Manages AI model downloading, caching, and version management."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize model manager.

        Args:
            cache_dir: Directory for model cache. Defaults to ~/.cache/screenshot_organizer/models
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".cache" / "screenshot_organizer" / "models"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ModelManager initialized with cache: {self.cache_dir}")

        # Model configurations
        self.models = {
            "phi3-vision": {
                "name": "microsoft/Phi-3-vision-128k-instruct",
                "size_gb": 8.0,
                "version": "0.1.0",
                "required": False,  # Optional (macOS only)
                "checksum": None  # Add model checksum for verification
            },
            "tesseract": {
                "name": "tesseract-ocr",
                "version": "5.x",
                "required": True,
                "system_package": True  # Installed via system package manager
            }
        }

    def check_model_availability(self, model_key: str) -> bool:
        """Check if a model is available locally.

        Args:
            model_key: Key identifying the model (e.g., 'phi3-vision').

        Returns:
            True if model is available, False otherwise.
        """
        if model_key not in self.models:
            logger.warning(f"Unknown model key: {model_key}")
            return False

        model_config = self.models[model_key]

        # System packages checked differently
        if model_config.get("system_package"):
            return self._check_system_package(model_key)

        # Check cache for downloaded models
        model_path = self.cache_dir / model_key
        available = model_path.exists() and self._verify_model(model_path, model_config)

        if available:
            logger.debug(f"Model {model_key} found in cache: {model_path}")
        else:
            logger.debug(f"Model {model_key} not found in cache")

        return available

    def _check_system_package(self, model_key: str) -> bool:
        """Check if a system package is installed.

        Args:
            model_key: Key identifying the system package.

        Returns:
            True if package is installed.
        """
        if model_key == "tesseract":
            try:
                import pytesseract
                version = pytesseract.get_tesseract_version()
                logger.debug(f"Tesseract OCR version {version} found")
                return True
            except Exception as e:
                logger.warning(f"Tesseract OCR not available: {e}")
                return False

        return False

    def _verify_model(self, model_path: Path, model_config: dict) -> bool:
        """Verify model integrity.

        Args:
            model_path: Path to model files.
            model_config: Model configuration dictionary.

        Returns:
            True if model is valid.
        """
        # Basic existence check
        if not model_path.exists():
            return False

        # Check for required files
        # This is simplified - real implementation would check specific model files
        files = list(model_path.glob("*"))
        if len(files) == 0:
            logger.warning(f"Model directory {model_path} is empty")
            return False

        # Checksum verification (if provided)
        if model_config.get("checksum"):
            # TODO: Implement checksum verification
            pass

        return True

    def download_model(self, model_key: str, force: bool = False) -> bool:
        """Download a model to the cache.

        Args:
            model_key: Key identifying the model to download.
            force: If True, re-download even if model exists.

        Returns:
            True if download successful.
        """
        if model_key not in self.models:
            logger.error(f"Unknown model key: {model_key}")
            return False

        model_config = self.models[model_key]

        # Can't download system packages
        if model_config.get("system_package"):
            logger.error(f"Cannot download system package: {model_key}")
            logger.info(f"Please install {model_config['name']} using your system package manager")
            return False

        # Check if already downloaded
        if not force and self.check_model_availability(model_key):
            logger.info(f"Model {model_key} already available")
            return True

        # Download model
        logger.info(f"Downloading model {model_key} ({model_config['size_gb']} GB)...")
        logger.warning("Model downloading not yet implemented - placeholder")

        # TODO: Implement actual model downloading
        # This would use huggingface_hub or similar to download models
        # Example:
        # from huggingface_hub import snapshot_download
        # snapshot_download(
        #     repo_id=model_config["name"],
        #     cache_dir=self.cache_dir / model_key,
        #     resume_download=True
        # )

        return False

    def get_model_info(self, model_key: str) -> Optional[dict]:
        """Get information about a model.

        Args:
            model_key: Key identifying the model.

        Returns:
            Dictionary with model information or None if not found.
        """
        if model_key not in self.models:
            return None

        model_config = self.models[model_key].copy()
        model_config["available"] = self.check_model_availability(model_key)

        if model_config["available"]:
            model_path = self.cache_dir / model_key
            if model_path.exists():
                # Get cache size
                total_size = sum(
                    f.stat().st_size
                    for f in model_path.rglob("*")
                    if f.is_file()
                )
                model_config["cached_size_mb"] = total_size / (1024 * 1024)
                model_config["cache_path"] = str(model_path)

        return model_config

    def list_models(self) -> dict:
        """List all known models and their availability.

        Returns:
            Dictionary mapping model keys to their info.
        """
        return {
            key: self.get_model_info(key)
            for key in self.models.keys()
        }

    def clear_cache(self, model_key: Optional[str] = None) -> bool:
        """Clear model cache.

        Args:
            model_key: Specific model to clear, or None to clear all.

        Returns:
            True if successful.
        """
        try:
            if model_key:
                # Clear specific model
                model_path = self.cache_dir / model_key
                if model_path.exists():
                    import shutil
                    shutil.rmtree(model_path)
                    logger.info(f"Cleared cache for model: {model_key}")
                else:
                    logger.warning(f"No cache found for model: {model_key}")
            else:
                # Clear all models
                import shutil
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("Cleared all model caches")

            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def check_requirements(self) -> dict:
        """Check if all required models are available.

        Returns:
            Dictionary with requirement check results.
        """
        results = {
            "all_required_available": True,
            "models": {}
        }

        for key, config in self.models.items():
            available = self.check_model_availability(key)
            results["models"][key] = {
                "available": available,
                "required": config.get("required", False),
                "name": config["name"]
            }

            if config.get("required") and not available:
                results["all_required_available"] = False

        return results

    def get_cache_size(self) -> float:
        """Get total size of model cache in MB.

        Returns:
            Cache size in megabytes.
        """
        if not self.cache_dir.exists():
            return 0.0

        total_size = sum(
            f.stat().st_size
            for f in self.cache_dir.rglob("*")
            if f.is_file()
        )

        return total_size / (1024 * 1024)

    def suggest_actions(self) -> list[str]:
        """Suggest actions based on model availability.

        Returns:
            List of suggested action messages.
        """
        suggestions = []
        requirements = self.check_requirements()

        if not requirements["all_required_available"]:
            for key, info in requirements["models"].items():
                if info["required"] and not info["available"]:
                    if self.models[key].get("system_package"):
                        suggestions.append(
                            f"Install {info['name']} using your system package manager"
                        )
                    else:
                        suggestions.append(
                            f"Download model: {key} ({info['name']})"
                        )

        # Check optional models
        for key, config in self.models.items():
            if not config.get("required"):
                if not self.check_model_availability(key):
                    suggestions.append(
                        f"Optional: Install {config['name']} for enhanced features"
                    )

        return suggestions
