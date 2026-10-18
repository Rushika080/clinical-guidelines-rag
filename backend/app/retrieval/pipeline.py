"""
Full retrieval pipeline.
embed → vector search → parent expansion → rerank
"""

import logging
from typing import Optional

from langchain.schema import Document
from langsmith import traceable

from app.config import get_settings
from app.retrieval.vectorstore import get_vectorstore, get_chroma_client
from app.retrieval.parent_retriever import expand_to_parents
from app.retrieval.hybrid import build_pinecone_filter
from app.reranking.cohere_reranker import rerank_documents

logger = logging.getLogger(__name__)


@traceable(name="retrieve-evidence", tags=["retrieval", "clinical-rag"])
def retrieve_evidence(
    query: str,
    specialty: Optional[str] = None,
    organization: Optional[str] = None,
    year: Optional[int] = None,
    guideline_id: Optional[str] = None,
    vector_top_k: Optional[int] = None,
    rerank_top_n: Optional[int] = None,
) -> dict:
    settings = get_settings()
    vector_top_k = vector_top_k or settings.vector_top_k
    rerank_top_n = rerank_top_n or settings.rerank_top_n

    logger.info(
        f"Retrieving evidence | query='{query[:80]}' "
        f"specialty={specialty} org={organization} year={year}"
    )

    # Build metadata filter (ChromaDB flat syntax)
    pinecone_filter = build_pinecone_filter(
        query=query,
        specialty=specialty,
        organization=organization,
        year=year,
        guideline_id=guideline_id,
    )
    logger.info(f"Filter: {pinecone_filter}")

    # Discover all guideline collections dynamically
    if guideline_id:
        collections_to_search = [guideline_id]
    else:
        client = get_chroma_client()
        all_collections = [c.name for c in client.list_collections()]
        collections_to_search = [
            c for c in all_collections
            if c != "clinical_guidelines"
        ] or ["ada-standards-2024"]

    logger.info(f"Searching collections: {collections_to_search}")

    # Search each collection and merge
    all_child_docs = []
    search_errors = []
    for coll_name in collections_to_search:
        
        try:
            vs = get_vectorstore(collection_name=coll_name)

            search_kwargs = {"k": vector_top_k}
            if pinecone_filter:
                search_kwargs["filter"] = pinecone_filter
            docs = vs.similarity_search(query=query, **search_kwargs)
            logger.info(f"Collection '{coll_name}': {len(docs)} results")
            all_child_docs.extend(docs)
        except Exception as e:
            logger.warning(f"Search failed for '{coll_name}': {e}")
            search_errors.append(f"{coll_name}: {str(e)}")

    child_docs = all_child_docs
    logger.info("Vector search returned %s child chunks total", len(child_docs))
    if not child_docs:
        return {
            "documents": [],
            "query": query,
            "vector_top_k": vector_top_k,
            "rerank_top_n": rerank_top_n,
            "filter_applied": pinecone_filter,
            "retrieval_count": 0,
            "reranked_count": 0,
        }
        if search_errors:
            result["error"] = "; ".join(search_errors)
        return result
    
    # Expand to parent sections
    parent_docs = expand_to_parents(child_docs)
    logger.info(f"Expanded to {len(parent_docs)} parent sections")

    # Rerank
    reranked_docs = rerank_documents(
        query=query,
        documents=parent_docs,
        top_n=rerank_top_n,
    )

    return {
        "documents":       reranked_docs,
        "query":           query,
        "vector_top_k":    vector_top_k,
        "rerank_top_n":    rerank_top_n,
        "filter_applied":  pinecone_filter,
        "retrieval_count": len(child_docs),
        "reranked_count":  len(reranked_docs),
    }