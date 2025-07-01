import abc
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

class AbstractLLMCache(abc.ABC):
    @abc.abstractmethod
    async def aget_value(self, key: str) -> Optional[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def aset_value(self, key: str, value: Dict[str, Any], expiry_seconds: int) -> None:
        pass

    @abc.abstractmethod
    async def adelete_value(self, key: str) -> None:
        pass

    @abc.abstractmethod
    async def is_expired(self, key: str, expiry_seconds: int) -> bool:
        pass