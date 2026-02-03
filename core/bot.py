import asyncio
import random

from typing import Optional
from loguru import logger

from core.swap_module import RhinoSwapModule
from loader import config, semaphore, file_operations


class Bot:
    @staticmethod
    async def safe_swap(
        delay: int,
        private_key: str,
        rpc_url: str,
        amount: Optional[float] = None,
    ):
        async with semaphore:
            module = RhinoSwapModule(
                api_key=config.application_settings.rhino_api_key,
                private_key=private_key,
                rpc_url=rpc_url,
            )

            try:
                if delay > 0:
                    logger.info(f"Wallet: {module.depositor_address} | Waiting for {delay} seconds before starting..")
                    await asyncio.sleep(delay)

                logger.info(f"Wallet: {module.depositor_address} | Bridge all BNB (opBNB -> BSC)..")
                status, result = await module.process_swap(amount)

                if status:
                    tx_hash = result if result.startswith("0x") else f"0x{result}"
                    tx = f"https://opbnbscan.com/tx/{tx_hash}"
                    logger.success(f"Wallet: {module.depositor_address} | BNB bridged | TX: {tx}")
                else:
                    logger.error(f"Wallet: {module.depositor_address} | Failed to bridge BNB | Error: {result}")

                await file_operations.export_result(module.depositor_address, status, "rhino_bridge")

            finally:
                if module:
                    await module.cleanup()

    async def process_swaps(self):
        tasks = []

        logger.info(f"Preparing bridge tasks for {len(config.wallets)} wallets..")
        for wallet in config.wallets:
            delay = (
                random.randint(
                    config.attempts_and_delay_settings.delay_before_start.min,
                    config.attempts_and_delay_settings.delay_before_start.max,
                )
                if config.attempts_and_delay_settings.delay_before_start.max > 0
                else 0
            )

            tasks.append(
                asyncio.create_task(
                    self.safe_swap(
                        delay=delay,
                        private_key=wallet,
                        rpc_url=config.web3_settings.opbnb_rpc_url,
                    )
                )
            )

        logger.success(f"Prepared {len(tasks)} swap tasks. Starting execution..")
        await asyncio.gather(*tasks)
