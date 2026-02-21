"""
Singleton store manager for all database operations.

Provides thread-safe, lazily-initialized singleton access to the
relational (SQLite) and vector (Chroma) stores used by the verification
pipeline.

Usage:
    from src.rag.store_manager import StoreManager

    stores = StoreManager()       # always returns the same instance
    result = stores.relational.get_by_ipc("302")
    hits   = stores.vector.query("murder", k=3)
"""

import logging
import threading

from src.config import paths
from src.rag.vectorstore import IPCBNSRelationalStore, IPCBNSVectorStore

logger = logging.getLogger(__name__)


class StoreManager:
    """
    Singleton that owns the relational and vector store instances.

    * Thread-safe: uses a lock around first-time initialization.
    * Lazy: stores are created only on first access.
    * Eager vector build: ``load_or_build()`` is called immediately to
      avoid ChromaDB tenant-connection errors under concurrency.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Relational store (SQLite)
            self._relational = IPCBNSRelationalStore(paths.SQLITE_DB)
            logger.info("StoreManager: relational store ready (%s)", paths.SQLITE_DB)

            # Vector store (Chroma) – eagerly build/load index
            self._vector = IPCBNSVectorStore()
            self._vector.load_or_build()
            logger.info("StoreManager: vector store ready")

            self._initialized = True

    # ── Public accessors ─────────────────────────────────────────────────

    @property
    def relational(self) -> IPCBNSRelationalStore:
        """Return the singleton relational (SQLite) store."""
        return self._relational

    @property
    def vector(self) -> IPCBNSVectorStore:
        """Return the singleton vector (Chroma) store."""
        return self._vector
