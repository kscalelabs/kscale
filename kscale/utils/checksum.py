"""Utility functions for file checksums."""

import hashlib
from pathlib import Path
from typing import Tuple

CHUNK_SIZE = 8192


async def calculate_sha256(file_path: str | Path) -> Tuple[str, int]:
    """Calculate SHA256 checksum and size of a file.

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (checksum hex string, file size in bytes)
    """
    sha256_hash = hashlib.sha256()
    file_size = 0

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256_hash.update(chunk)
            file_size += len(chunk)

    return sha256_hash.hexdigest(), file_size


class FileChecksum:
    """Helper class for handling file checksums."""

    @staticmethod
    async def calculate(file_path: str | Path) -> Tuple[str, int]:
        """Calculate SHA256 checksum and size of a file."""
        return await calculate_sha256(file_path)

    @staticmethod
    def update_hash(hash_obj: "hashlib._Hash", chunk: bytes) -> None:
        """Update a hash object with new data."""
        hash_obj.update(chunk)
