import hashlib
from typing import AsyncIterator, Optional


Stream = AsyncIterator[bytes]


class MemoryStorage:
    def __init__(self):
        self._files: dict[str, bytes] = {}
    async def find(self, key: str) -> Optional[Stream]:
        """
        Async context manager that provides an async iterator of `bytes` chunks
        and closes all opened resources when the `async with` block ends.
        """
        content = self._files.get(key)
        if content is None:
            return None
        content_ = content  # microsoft/pyright/issues/599

        async def _find() -> AsyncIterator[bytes]:
            yield content_
        return _find()

    async def upload(self, stream: Stream) -> tuple[bool, str]:
        """
        :return: (file already exists, hash digest)
        """
        h = hashlib.sha512()

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            h.update(chunk)

        file_hash = h.hexdigest()
        if file_hash in self._files:
            return True, file_hash

        self._files[file_hash] = b"".join(chunks)
        return False, file_hash

    async def delete(self, key: str) -> None:
        """
        :raises: KeyError
        """
        self._files.pop(key)
