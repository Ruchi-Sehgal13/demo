"""
Build the Chroma vector store from the processed PDF chunks.
Run once (requires GOOGLE_API_KEY in .env): python -m scripts.build_vector_store
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import paths
from src.rag.vectorstore import IPCBNSVectorStore


def main():
    persist_dir = str(Path(paths.ROOT) / "data" / "chroma_ipcbns")
    chunks_path = Path(paths.PROCESSED_CHUNKS)
    data = json.loads(chunks_path.read_text(encoding="utf-8"))
    num_chunks = data.get("num_chunks") or len(data.get("chunks", []))

    store = IPCBNSVectorStore(persist_dir=persist_dir)
    store.build_from_json(paths.PROCESSED_CHUNKS)
    print(f"[build_vector_store] Indexed {num_chunks} chunks into {persist_dir}")


if __name__ == "__main__":
    main()
