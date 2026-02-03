import asyncio
import signal
import sys
import warnings

from loguru import logger
from application import ApplicationManager
from utils import setup_logs


warnings.filterwarnings("ignore")


async def main():
    app = ApplicationManager()

    try:
        await app.run()
    except asyncio.CancelledError:
        logger.info("Main task was cancelled")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    signal.signal(signal.SIGINT, lambda s, f: asyncio.get_event_loop().stop())
    signal.signal(signal.SIGTERM, lambda s, f: asyncio.get_event_loop().stop())

    try:
        setup_logs(is_main=True)
        asyncio.run(main())
    except Exception as error:
        logger.error(f"An error occurred: {error}")

    input("\nPress Enter to exit...")
