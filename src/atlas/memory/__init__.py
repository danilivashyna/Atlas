"""Atlas memory package - in-process and persistent memory backends."""

import os
from typing import Optional, Union

# Lazy singletons
_MEMORY_INSTANCE: Optional[Union["MappaMemory", "PersistentMemory"]] = None  # type: ignore
_MEMORY_BACKEND: Optional[str] = None


def get_memory() -> Union["MappaMemory", "PersistentMemory"]:  # type: ignore
    """
    Get memory singleton based on ATLAS_MEMORY_BACKEND env.

    Env: ATLAS_MEMORY_BACKEND = 'inproc' (default) | 'sqlite'
    """
    global _MEMORY_INSTANCE, _MEMORY_BACKEND

    backend = os.getenv("ATLAS_MEMORY_BACKEND", "inproc").lower()

    # If backend changed or not initialized, create new instance
    if _MEMORY_INSTANCE is None or _MEMORY_BACKEND != backend:
        _MEMORY_BACKEND = backend

        if backend == "sqlite":
            from atlas.memory.persistent import PersistentMemory

            _MEMORY_INSTANCE = PersistentMemory()
        else:
            # Default: inproc
            from atlas.memory.mappa import MappaMemory

            _MEMORY_INSTANCE = MappaMemory()

    return _MEMORY_INSTANCE


# For backward compatibility, provide default MEMORY (inproc)
from atlas.memory.mappa import MEMORY  # noqa: E402

__all__ = ["MappaMemory", "MEMORY", "get_memory", "PersistentMemory"]
