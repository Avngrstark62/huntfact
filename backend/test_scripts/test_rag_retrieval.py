from logging_config import setup_logging

setup_logging()

from chroma_client import chroma_client
from config import settings
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_COLLECTION = "collection_5"
DEFAULT_MAX_CHUNKS = 5
DEFAULT_MAX_DISTANCE = 0.3


def _get_query_embedding(query: str) -> list[float]:
    client = OpenAI(api_key=settings.openai.api_key)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def _collect_similar_results(
    query_result: dict,
    max_distance: float,
    max_chunks: int,
) -> list[tuple[str, dict, float | None]]:
    documents = (query_result.get("documents") or [[]])[0]
    metadatas = (query_result.get("metadatas") or [[]])[0]
    distances = (query_result.get("distances") or [[]])[0]

    matched: list[tuple[str, dict, float | None]] = []
    for idx, doc in enumerate(documents):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        distance = distances[idx] if idx < len(distances) else None
        if distance is not None and float(distance) <= max_distance:
            matched.append((doc or "", metadata, distance))
        if len(matched) >= max_chunks:
            break

    return matched


def _print_results(
    results: list[tuple[str, dict, float | None]],
    max_distance: float,
) -> None:
    if not results:
        print(f"\nNo chunks matched distance threshold <= {max_distance:.4f}.")
        return

    print(f"\nMatched chunks: {len(results)}")
    for idx, (doc, metadata, distance) in enumerate(results, 1):

        print("\n" + "-" * 80)
        print(f"Rank: {idx}")
        print(f"Distance (cosine): {distance}")
        print(f"URL: {metadata.get('source_url') or metadata.get('url')}")
        print(f"Title: {metadata.get('source_title') or metadata.get('title')}")
        print(f"Query: {metadata.get('source_query') or metadata.get('query')}")
        print(f"Source ID: {metadata.get('source_id')}")
        print(f"Chunk: {metadata.get('chunk_index')} / {metadata.get('chunk_count')}")
        print("Chunk Text:")
        print(doc or "")


def run_interactive_rag_retrieval() -> None:
    print("Interactive RAG Retrieval")
    print("Commands:")
    print("  /dist <number>         set maximum cosine distance threshold")
    print("  /collection <name>     switch collection")
    print("  quit                   exit")

    chroma = chroma_client.connect()
    collection_name = DEFAULT_COLLECTION
    max_chunks = DEFAULT_MAX_CHUNKS
    max_distance = DEFAULT_MAX_DISTANCE

    while True:
        prompt = f"\n[{collection_name}] query> "
        query = input(prompt).strip()

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Exiting interactive retrieval.")
            break

        if query.startswith("/dist "):
            raw_distance = query.replace("/dist ", "", 1).strip()
            try:
                parsed_distance = float(raw_distance)
                if parsed_distance < 0:
                    raise ValueError("distance must be non-negative")
                max_distance = parsed_distance
                print(f"Updated maximum cosine distance to {max_distance:.4f}")
            except Exception:
                print("Invalid value for /dist. Example: /dist 0.55")
            continue

        if query.startswith("/collection "):
            next_collection = query.replace("/collection ", "", 1).strip()
            if not next_collection:
                print("Collection name cannot be empty.")
                continue
            collection_name = next_collection
            print(f"Switched collection to {collection_name}")
            continue

        try:
            collection = chroma.get_collection(name=collection_name)
            query_embedding = _get_query_embedding(query)
            query_result = collection.query(
                query_embeddings=[query_embedding],
                n_results=max_chunks,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            print(f"Retrieval failed: {str(e)}")
            continue

        similar_results = _collect_similar_results(
            query_result=query_result,
            max_distance=max_distance,
            max_chunks=max_chunks,
        )
        _print_results(similar_results, max_distance)


if __name__ == "__main__":
    run_interactive_rag_retrieval()
