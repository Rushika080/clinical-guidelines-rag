import logging
from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import chromadb

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    settings = get_settings()
    logger.info(f"Loading embedding model: {settings.embedding_model}")
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache
def get_chroma_client():
    """
    Return a persistent ChromaDB client.
    Using lru_cache ensures the same client instance is reused —
    this is critical for persistence to work correctly on Windows.
    """
    settings = get_settings()
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"ChromaDB persist dir: {persist_dir.resolve()}")
    return chromadb.PersistentClient(path=str(persist_dir.resolve()))


def get_vectorstore(collection_name: str = "clinical_guidelines") -> Chroma:
    """
    Return a Chroma vectorstore backed by a persistent client.
    Passing the client explicitly ensures data is written to disk.
    """
    client = get_chroma_client()
    embeddings = get_embeddings()

    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def ensure_index_exists() -> None:
    logger.info("ChromaDB: using persistent client, collection auto-created.")