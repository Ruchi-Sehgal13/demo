"""
Vector store for verification: embeddings (Google or local) and Chroma vector store over PDF chunks
(IPCBNSVectorStore). The verifier uses the vector store to score claims by semantic similarity.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
