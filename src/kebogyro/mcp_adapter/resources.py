import base64
from typing import Any
from dataclasses import dataclass

from mcp import ClientSession
from mcp.types import BlobResourceContents, ResourceContents, TextResourceContents


@dataclass
class Blob:
    data: Any
    mime_type: str
    metadata: dict[str, Any]

    @classmethod
    def from_data(cls, data: Any, mime_type: str, metadata: dict[str, Any]):
        return cls(data=data, mime_type=mime_type, metadata=metadata)


def convert_mcp_resource_to_blob(
    resource_uri: str,
    contents: ResourceContents,
) -> Blob:
    if isinstance(contents, TextResourceContents):
        data = contents.text.encode("utf-8")
    elif isinstance(contents, BlobResourceContents):
        data = base64.b64decode(contents.blob)
    else:
        raise ValueError(f"Unsupported content type for URI {resource_uri}")

    return Blob.from_data(
        data=data,
        mime_type=contents.mimeType,
        metadata={"uri": resource_uri},
    )


async def get_mcp_resource(session: ClientSession, uri: str) -> list[Blob]:
    contents_result = await session.read_resource(uri)
    if not contents_result.contents or len(contents_result.contents) == 0:
        return []

    return [
        convert_mcp_resource_to_blob(uri, content) for content in contents_result.contents
    ]


async def load_mcp_resources(
    session: ClientSession,
    *,
    uris: str | list[str] | None = None,
) -> list[Blob]:
    blobs = []

    if uris is None:
        resources_list = await session.list_resources()
        uri_list = [r.uri for r in resources_list.resources]
    elif isinstance(uris, str):
        uri_list = [uris]
    else:
        uri_list = uris

    for uri in uri_list:
        try:
            resource_blobs = await get_mcp_resource(session, uri)
            blobs.extend(resource_blobs)
        except Exception as e:
            raise RuntimeError(f"Error fetching resource {uri}") from e

    return blobs
