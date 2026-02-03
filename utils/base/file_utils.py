import asyncio
import aiofiles

from pathlib import Path
from loguru import logger



class FileOperations:
    def __init__(self, base_path: str = "./results"):
        self.base_path = Path(base_path)
        self.lock = asyncio.Lock()
        self.module_paths: dict[str, dict[str, Path]] = {
            "rhino_bridge": {
                "success": self.base_path / "login" / "rhino_bridge_success.txt",
                "failed": self.base_path / "login" / "rhino_bridge_failed.txt",
            },
        }

    async def setup_files(self):
        self.base_path.mkdir(exist_ok=True)
        for module_name, module_paths in self.module_paths.items():
            for path_key, path in module_paths.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                if module_name == "stats":
                    continue
                else:
                    path.touch(exist_ok=True)

    async def export_result(self, result: str, status: bool, module: str):
        if module not in self.module_paths:
            raise ValueError(f"Unknown module: {module}")

        file_path = self.module_paths[module]["success" if status else "failed"]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, "a") as file:
                    await file.write(f"{result}\n")
            except IOError as e:
                logger.error(f"Error writing to file (IOError): {e}")
            except Exception as e:
                logger.error(f"Error writing to file: {e}")

