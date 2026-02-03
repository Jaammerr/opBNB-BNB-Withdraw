from loader import config
from console import Console
from core.bot import Bot
from loader import file_operations


class ApplicationManager:

    @staticmethod
    async def run() -> None:
        await file_operations.setup_files()

        while True:
            await Console().build()

            if config.module == "swap_bnb_via_rhino":
                await Bot().process_swaps()

            input("\nPress Enter to continue...")
