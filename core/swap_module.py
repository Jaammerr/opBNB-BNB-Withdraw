import asyncio
import httpx

from decimal import Decimal
from typing import Optional, Tuple, Dict, Any

from loguru import logger
from web3 import Web3

from models import RhinoQuoteResult

API_BASE = "https://api.rhino.fi"
BRIDGE_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "commitmentId", "type": "uint256"}],
        "name": "depositNativeWithId",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
]


class RhinoSwapModule:
    CHAIN_IN = "OPBNB"
    CHAIN_OUT = "BINANCE"
    TOKEN_IN = "BNB"
    TOKEN_OUT = "BNB"

    def __init__(
        self,
        *,
        api_key: str,
        private_key: str,
        rpc_url: str,
    ):
        self.api_key = api_key
        self.private_key = private_key
        self.rpc_url = rpc_url

        self._client: Optional[httpx.AsyncClient] = None
        self._jwt: Optional[str] = None
        self._configs: Optional[Dict[str, Any]] = None

        self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self._account = self._w3.eth.account.from_key(self.private_key)
        self.depositor_address = Web3.to_checksum_address(self._account.address)
        self.recipient_address = Web3.to_checksum_address(self._account.address)

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _http(self, method: str, path: str, *, json_body: Optional[dict] = None, jwt: Optional[str] = None) -> dict:
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=API_BASE,
                timeout=30,
                headers={"content-type": "application/json"},
            )

        headers = {}
        if jwt:
            headers["authorization"] = jwt

        r = await self._client.request(method, path, json=json_body, headers=headers)
        try:
            data = r.json()
        except Exception:
            raise RuntimeError(f"Non-JSON response ({r.status_code}): {r.text[:300]}")

        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} {path}: {str(data)[:800]}")

        return data

    async def _get_jwt(self) -> str:
        if self._jwt:
            return self._jwt

        data = await self._http("POST", "/authentication/auth/apiKey", json_body={"apiKey": self.api_key})
        jwt = data.get("token") or data.get("jwt") or data.get("accessToken") or data.get("authorization")
        if not jwt:
            raise RuntimeError(f"Can't find JWT in response: {data}")

        self._jwt = jwt
        return jwt

    async def _get_configs(self) -> Dict[str, Any]:
        if self._configs:
            return self._configs

        self._configs = await self._http("GET", "/bridge/configs")
        return self._configs

    @staticmethod
    def _quote_id_to_commitment_int(quote_id: str) -> int:
        q = quote_id.strip().lower()
        if q.startswith("0x"):
            q = q[2:]
        return int(q, 16)

    async def _get_native_balance_wei(self) -> int:
        return await asyncio.to_thread(lambda: self._w3.eth.get_balance(self._account.address))

    async def _calc_max_send_wei(self, *, safety_mul: Decimal = Decimal("1.25")) -> int:
        balance = await self._get_native_balance_wei()
        gas_price = await asyncio.to_thread(lambda: self._w3.eth.gas_price)

        conservative_gas = 300_000
        fee_buffer = int(Decimal(gas_price * conservative_gas) * safety_mul)

        max_send = balance - fee_buffer
        return max_send if max_send > 0 else 0

    async def _estimate_gas_native_deposit(self, bridge_contract, commitment_id_int: int, value_wei: int) -> int:
        def _estimate() -> int:
            tx = bridge_contract.functions.depositNativeWithId(commitment_id_int).build_transaction(
                {"from": self._account.address, "value": value_wei}
            )
            return self._w3.eth.estimate_gas(tx)

        return int(await asyncio.to_thread(_estimate))

    async def _send_native_deposit(
        self,
        *,
        bridge_address: str,
        chain_id: int,
        commitment_id_int: int,
        value_wei: int,
    ) -> str:
        bridge = self._w3.eth.contract(
            address=Web3.to_checksum_address(bridge_address),
            abi=BRIDGE_ABI,
        )

        gas_price = await asyncio.to_thread(lambda: self._w3.eth.gas_price)

        try:
            gas_est = await self._estimate_gas_native_deposit(bridge, commitment_id_int, value_wei)
            gas_limit = int(gas_est * 1.20)
        except Exception as e:
            gas_limit = 300_000

        nonce = await asyncio.to_thread(lambda: self._w3.eth.get_transaction_count(self._account.address))

        def _build_sign_send() -> str:
            tx = bridge.functions.depositNativeWithId(commitment_id_int).build_transaction(
                {
                    "from": self._account.address,
                    "value": value_wei,
                    "nonce": nonce,
                    "chainId": int(chain_id),
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                }
            )
            signed = self._account.sign_transaction(tx)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            return tx_hash.hex()

        return await asyncio.to_thread(_build_sign_send)

    async def process_swap(self, amount: Optional[float]) -> Tuple[bool, str]:
        try:
            jwt = await self._get_jwt()
            configs = await self._get_configs()

            if self.CHAIN_IN not in configs:
                available = ", ".join(sorted(configs.keys()))
                raise RuntimeError(f"chainIn '{self.CHAIN_IN}' not found in configs. Available: {available}")

            chain_cfg = configs[self.CHAIN_IN]

            chain_id = chain_cfg.get("chainId") or self._w3.eth.chain_id
            bridge_address = chain_cfg.get("contractAddress")
            native_token_name = chain_cfg.get("nativeTokenName")

            if not bridge_address:
                raise RuntimeError(f"Missing contractAddress for chain '{self.CHAIN_IN}' in rhino configs")

            if native_token_name and self.TOKEN_IN != native_token_name:
                raise RuntimeError(
                    f"tokenIn '{self.TOKEN_IN}' != nativeTokenName '{native_token_name}' for chain '{self.CHAIN_IN}'. "
                    f"This module expects native deposit."
                )

            if amount is None:
                max_send_wei = await self._calc_max_send_wei()
                if max_send_wei <= 0:
                    raise RuntimeError("Not enough balance to pay gas + amount (amount=None).")

                amount_dec = Decimal(self._w3.from_wei(max_send_wei, "ether"))
                amount_str = format(amount_dec, "f")
                logger.info(f"Wallet: {self.depositor_address} | Using MAX available: {amount_str} {self.TOKEN_IN}")
            else:
                if amount <= 0:
                    raise RuntimeError("Amount must be > 0 (or None for max balance).")
                amount_str = f"{amount:.18f}".rstrip("0").rstrip(".")

            quote_payload = {
                "chainIn": self.CHAIN_IN,
                "chainOut": self.CHAIN_OUT,
                "amount": amount_str,
                "mode": "pay",
                "tokenIn": self.TOKEN_IN,
                "tokenOut": self.TOKEN_OUT,
                "depositor": self.depositor_address,
                "recipient": self.recipient_address,
                "amountNative": "0",
                "isSda": "false",
            }

            quote = await self._http("POST", "/bridge/quote/bridge-swap/user", jwt=jwt, json_body=quote_payload)
            quote_id = quote.get("quoteId")
            if not quote_id:
                raise RuntimeError(f"Quote has no quoteId: {quote}")

            q = RhinoQuoteResult(
                quote_id=quote_id,
                pay_amount=quote.get("payAmount"),
                receive_amount=quote.get("receiveAmount"),
                raw=quote,
            )

            logger.info(
                f"Wallet: {self.depositor_address} | Rhino quote: pay={q.pay_amount} {self.TOKEN_IN} -> receive={q.receive_amount} {self.TOKEN_OUT} | quoteId={q.quote_id}"
            )

            commit = await self._http("POST", f"/bridge/quote/commit/{q.quote_id}", jwt=jwt)
            committed_id = commit.get("quoteId")
            if not committed_id:
                raise RuntimeError(f"Commit failed: {commit}")

            commitment_int = self._quote_id_to_commitment_int(committed_id)

            value_wei = self._w3.to_wei(Decimal(amount_str), "ether")
            tx_hash = await self._send_native_deposit(
                bridge_address=bridge_address,
                chain_id=int(chain_id),
                commitment_id_int=commitment_int,
                value_wei=int(value_wei),
            )

            return True, tx_hash

        except Exception as e:
            return False, str(e)
