from datetime import datetime, UTC
import re
from typing import Any
from uuid import uuid4

from chroma_client import chroma_client
from config import settings
from logging_config import get_logger
from openai import OpenAI

logger = get_logger("services.rag_storage.rag_storage")

DEFAULT_TOKEN_LIMIT = 200
DEFAULT_OVERLAP_TOKENS = 80
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_BATCH_SIZE = 100


def _sanitize_collection_name(collection_name: str | None) -> str:
    if not collection_name:
        return "rag"

    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", collection_name.strip())
    normalized = normalized.strip("_")
    if not normalized:
        return "rag"

    normalized = normalized[:63]
    if len(normalized) < 3:
        normalized = f"rag_{normalized}"
    if not normalized[0].isalnum():
        normalized = f"r{normalized}"
    if not normalized[-1].isalnum():
        normalized = f"{normalized}0"

    return normalized[:63]


def _build_unique_collection_name(collection_name: str | None) -> str:
    prefix = _sanitize_collection_name(collection_name)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    candidate = f"{prefix}_{timestamp}_{suffix}"
    return candidate[:63]


def _estimate_tokens(text: str) -> int:
    # Approximate token count without adding a tokenizer dependency.
    return len(re.findall(r"\w+|[^\w\s]", text))


def _clean_markdown_content(content: str) -> str:
    """
    Remove noisy markdown media/link patterns before chunking:
    - Images: ![alt](image_url) -> removed
    - Links: [text](url) -> text
    """
    if not content:
        return ""

    cleaned = content
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _split_into_sentences(text: str) -> list[str]:
    if not text.strip():
        return []

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    sentences: list[str] = []

    for paragraph in paragraphs:
        if paragraph.startswith("#") or paragraph.startswith("- ") or paragraph.startswith("* "):
            sentences.append(paragraph)
            continue

        parts = re.split(r"(?<=[.!?])\s+", paragraph)
        for part in parts:
            value = part.strip()
            if value:
                sentences.append(value)

    return sentences


def _split_long_sentence(sentence: str, token_limit: int) -> list[str]:
    words = sentence.split()
    if not words:
        return []

    pieces: list[str] = []
    current_words: list[str] = []
    current_tokens = 0

    for word in words:
        word_tokens = _estimate_tokens(word)
        if current_words and current_tokens + word_tokens > token_limit:
            pieces.append(" ".join(current_words))
            current_words = [word]
            current_tokens = word_tokens
        else:
            current_words.append(word)
            current_tokens += word_tokens

    if current_words:
        pieces.append(" ".join(current_words))

    return pieces


def _build_overlap_tail(
    chunk_sentences: list[str],
    chunk_tokens: list[int],
    overlap_tokens: int,
) -> tuple[list[str], int]:
    if overlap_tokens <= 0 or not chunk_sentences:
        return [], 0

    tail_sentences: list[str] = []
    tail_tokens = 0
    for sentence, token_count in zip(reversed(chunk_sentences), reversed(chunk_tokens)):
        if tail_sentences and tail_tokens + token_count > overlap_tokens:
            break
        tail_sentences.insert(0, sentence)
        tail_tokens += token_count

    return tail_sentences, tail_tokens


def _chunk_text(
    text: str,
    token_limit: int = DEFAULT_TOKEN_LIMIT,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[str]:
    cleaned_text = text.strip()
    if not cleaned_text:
        return []
    if token_limit <= 0:
        raise ValueError("token_limit must be greater than zero")
    if overlap_tokens < 0:
        raise ValueError("overlap_tokens must be zero or greater")
    if overlap_tokens >= token_limit:
        raise ValueError("overlap_tokens must be smaller than token_limit")

    sentences = _split_into_sentences(cleaned_text)
    if not sentences:
        return []

    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens_per_sentence: list[int] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)

        if sentence_tokens > token_limit:
            for part in _split_long_sentence(sentence, token_limit):
                part_tokens = _estimate_tokens(part)
                if current_sentences:
                    chunks.append(" ".join(current_sentences))
                    current_sentences = []
                    current_tokens_per_sentence = []
                    current_tokens = 0
                chunks.append(part)
                current_sentences = [part]
                current_tokens_per_sentence = [part_tokens]
                current_tokens = part_tokens
            continue

        if current_sentences and current_tokens + sentence_tokens > token_limit:
            chunks.append(" ".join(current_sentences))
            overlap_tail, overlap_token_count = _build_overlap_tail(
                current_sentences,
                current_tokens_per_sentence,
                overlap_tokens,
            )
            current_sentences = overlap_tail.copy()
            current_tokens_per_sentence = [_estimate_tokens(item) for item in overlap_tail]
            current_tokens = overlap_token_count

        current_sentences.append(sentence)
        current_tokens_per_sentence.append(sentence_tokens)
        current_tokens += sentence_tokens

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return [chunk for chunk in chunks if chunk.strip()]


def _normalize_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_sources: list[dict[str, Any]] = []
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            continue

        url = str(source.get("url", "")).strip()
        raw_content = str(source.get("content", "")).strip()
        content = _clean_markdown_content(raw_content)
        if not url or not content:
            continue

        source_id_value = source.get("source_id")
        try:
            source_id = int(source_id_value) if source_id_value is not None else index
        except (TypeError, ValueError):
            source_id = index

        normalized_sources.append(
            {
                "source_id": source_id,
                "url": url,
                "title": str(source.get("title", "")).strip(),
                "query": str(source.get("query", "")).strip(),
                "content": content,
            }
        )

    return normalized_sources


def _get_embeddings(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []

    for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        embeddings.extend(item.embedding for item in response.data)

    logger.info("Generated embeddings for %s chunks", len(embeddings))
    return embeddings


async def store_sources_in_rag(
    sources: list[dict[str, Any]],
    collection_name: str | None = None,
) -> dict[str, Any]:
    normalized_sources = _normalize_sources(sources)
    if not normalized_sources:
        logger.warning("No valid sources provided for RAG storage")
        return {"collection_name": None, "source_count": 0, "chunk_count": 0}

    target_collection_name = _build_unique_collection_name(collection_name)
    logger.info(
        "Storing %s sources to RAG collection: %s",
        len(normalized_sources),
        target_collection_name,
    )

    chroma = chroma_client.connect()
    collection = chroma.get_or_create_collection(
        name=target_collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    documents: list[str] = []
    ids: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for source_index, source in enumerate(normalized_sources):
        chunks = _chunk_text(source["content"])
        if not chunks:
            continue

        total_chunks = len(chunks)
        for chunk_index, chunk in enumerate(chunks):
            chunk_id = f"{target_collection_name}_{source_index}_{chunk_index}"
            documents.append(chunk)
            ids.append(chunk_id)
            metadatas.append(
                {
                    "collection_name": target_collection_name,
                    "source_id": source["source_id"],
                    "url": source["url"],
                    "title": source["title"],
                    "query": source["query"],
                    "source_url": source["url"],
                    "source_title": source["title"],
                    "source_query": source["query"],
                    "source_index": source_index,
                    "chunk_index": chunk_index,
                    "chunk_count": total_chunks,
                }
            )

    if not documents:
        logger.warning("No chunks generated from valid sources for RAG storage")
        return {
            "collection_name": target_collection_name,
            "source_count": len(normalized_sources),
            "chunk_count": 0,
        }

    embeddings = _get_embeddings(documents)
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info(
        "Stored %s chunks from %s sources in collection: %s",
        len(documents),
        len(normalized_sources),
        target_collection_name,
    )
    return {
        "collection_name": target_collection_name,
        "source_count": len(normalized_sources),
        "chunk_count": len(documents),
    }
