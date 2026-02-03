import os
import yaml

from pathlib import Path
from typing import Dict, List, Generator, Union

from loguru import logger
from models import Config
from sys import exit


class ConfigurationError(Exception):
    pass


class ConfigLoader:
    REQUIRED_PARAMS = frozenset(
        {
            "attempts_and_delay_settings",
            "web3_settings",
            "application_settings",
        }
    )

    def __init__(self, base_path: Union[str, Path] = None):
        self.base_path = Path(base_path or os.getcwd())
        self.config_path = self.base_path / "config"
        self.data_path = self.config_path / "data"
        self.settings_path = self.config_path / "settings.yaml"

    @staticmethod
    def _read_file(file_path: Path, allow_empty: bool = False, is_yaml: bool = False) -> Union[List[str], Dict]:
        if not file_path.exists():
            raise ConfigurationError(f"File not found: {file_path}")

        try:
            if is_yaml:
                return yaml.safe_load(file_path.read_text(encoding='utf-8'))

            content = file_path.read_text(encoding='utf-8').strip()
            if not allow_empty and not content:
                raise ConfigurationError(f"File is empty: {file_path}")

            return [line.strip() for line in content.splitlines() if line.strip()]

        except Exception as e:
            raise ConfigurationError(f"Failed to read file {file_path}: {str(e)}")

    def _load_yaml(self) -> Dict:
        try:
            config = self._read_file(self.settings_path, is_yaml=True)
            missing_fields = self.REQUIRED_PARAMS - set(config.keys())

            if missing_fields:
                raise ConfigurationError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")

    def _parse_accounts(
            self,
            filename: str,
    ) -> Generator[str, None, None]:
        try:
            lines = self._read_file(self.data_path / filename, allow_empty=False)

            for line in lines:
                try:
                    line = line.strip()
                    if not line:
                        continue

                    yield line

                except (ValueError, IndexError) as e:
                    logger.warning(f"Invalid account format: {line} | File: {filename} | Error: {e}")
                    exit(1)

        except ConfigurationError:
            raise

        except Exception as e:
            raise ConfigurationError(f"Failed to process accounts file: {str(e)} | File: {filename}")


    def load(self) -> Config | None:
        try:
            params = self._load_yaml()
            wallets = list(self._parse_accounts("wallets.txt"))

            return Config(
                **params,
                wallets=wallets,
            )

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            exit(1)


def load_config() -> Config:
    return ConfigLoader().load()
