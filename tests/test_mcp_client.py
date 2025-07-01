from kebogyro.mcp_adapter.client import BBServerMCPClient
from kebogyro.cache import AbstractLLMCache

class DummyCache(AbstractLLMCache):
    async def aget_value(self, key): return None
    async def aset_value(self, key, value, expiry_seconds): pass
    async def adelete_value(self, key): pass
    async def is_expired(self, key, expiry_seconds): return False

def test_mcp_client_instantiation():
    client = BBServerMCPClient(
        connections={
            "bridge": {
                "url": "http://localhost:8000/bridge/user/test/sse",
                "transport": "sse"
            }
        },
        cache_adapter=DummyCache()
    )
    assert "bridge" in client.connections
