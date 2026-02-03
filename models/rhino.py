from dataclasses import dataclass
from typing import Optional, Any, Dict


@dataclass
class RhinoQuoteResult:
    quote_id: str
    pay_amount: Optional[str] = None
    receive_amount: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
