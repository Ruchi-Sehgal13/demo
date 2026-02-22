"""
Vector and relational stores for verification: embeddings (Google or local), SQLite IPC→BNS mapping
(IPCBNSRelationalStore), and Chroma vector store over PDF chunks (IPCBNSVectorStore). The verifier
uses both to score claims.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from src.config import paths


def get_embeddings() -> Embeddings:
    """
    Return a LangChain Embeddings implementation: Google Generative AI if GOOGLE_API_KEY is set,
    otherwise local SentenceTransformerEmbeddings (all-MiniLM-L6-v2) so no API key is required.
    """
    if os.getenv("GOOGLE_API_KEY"):
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    return SentenceTransformerEmbeddings()


class SentenceTransformerEmbeddings(Embeddings):
    """
    Local embedding model using sentence-transformers (no API key). Implements LangChain Embeddings
    so it can be used with Chroma. Lazy-loads the model on first embed_documents or embed_query.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        """Load the SentenceTransformer model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts; returns a list of float vectors (one per text)."""
        model = self._get_model()
        return model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string; returns one float vector."""
        model = self._get_model()
        return model.encode(text, convert_to_numpy=True).tolist()


class IPCBNSRelationalStore:
    """
    Structured IPC → BNS mapping in SQLite.

    This is the authoritative layer for section mappings.
    """

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(f"sqlite:///{db_path}")
        self.meta = MetaData()
        self.mapping = Table(
            "ipcbns_mapping",
            self.meta,
            Column("ipc_section", String, primary_key=True),
            Column("bns_section", String),
            Column("notes", String),
        )
        self.meta.create_all(self.engine)

    def upsert_mapping(self, ipc: str, bns: str, notes: str = "") -> None:
        with self.engine.begin() as conn:
            conn.execute(
                self.mapping.insert()
                .values(ipc_section=ipc, bns_section=bns, notes=notes)
                .prefix_with("OR REPLACE")
            )

    def get_by_ipc(self, ipc: str) -> Optional[Dict[str, str]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.mapping).where(self.mapping.c.ipc_section == ipc)
            ).fetchone()
            if not row:
                return None
            return dict(row._mapping)

    def get_by_bns(self, bns: str) -> Optional[Dict[str, str]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.mapping).where(self.mapping.c.bns_section == bns)
            ).fetchone()
            if not row:
                return None
            return dict(row._mapping)


class IPCBNSVectorStore:
    """
    Semantic store over processed PDF chunks, backed by Chroma.
    """

    def __init__(self, persist_dir: Optional[str] = None):
        if persist_dir is None:
            persist_dir = str(Path(paths.ROOT) / "data" / "chroma_ipcbns")
        self.persist_dir = persist_dir
        self.embeddings = get_embeddings()
        self.store: Optional[Chroma] = None

    def build_from_json(self, json_path: str) -> None:
        p = Path(json_path)
        if not p.exists():
            raise FileNotFoundError(f"Chunks JSON not found at {p}")
        data = json.loads(p.read_text(encoding="utf-8"))

        # Skip empty chunks (embedding API rejects empty text)
        pairs = [(c["text"], c["metadata"]) for c in data["chunks"] if (c.get("text") or "").strip()]
        texts = [t for t, _ in pairs]
        metas = [m for _, m in pairs]

        self.store = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metas,
            persist_directory=self.persist_dir,
        )

    def load_or_build(self) -> None:
        if Path(self.persist_dir).exists():
            self.store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.persist_dir,
            )
        else:
            self.build_from_json(paths.PROCESSED_CHUNKS)

    def query(
        self, query: str, k: int = 5
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        if self.store is None:
            self.load_or_build()
        docs = self.store.similarity_search_with_score(query, k=k)
        return [(d.page_content, d.metadata, float(score)) for d, score in docs]
