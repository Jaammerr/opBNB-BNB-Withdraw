from dataclasses import dataclass
from pydantic import BaseModel, PositiveInt, ConfigDict, Field


class BaseConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)



@dataclass
class PositiveIntRange:
    min: PositiveInt
    max: PositiveInt


@dataclass
class AttemptsAndDelaySettings:
    delay_before_start: PositiveIntRange



@dataclass
class Web3Settings:
    opbnb_rpc_url: str


@dataclass
class ApplicationSettings:
    threads: int
    rhino_api_key: str



class Config(BaseConfig):
    wallets: list[str] = Field(default_factory=list)

    application_settings: ApplicationSettings
    web3_settings: Web3Settings
    attempts_and_delay_settings: AttemptsAndDelaySettings

    module: str = ""
