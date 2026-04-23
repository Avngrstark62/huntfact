from typing import Optional
from logging_config import get_logger
from config import settings
from llm import llm
from chroma_client import chroma_client
from services.save_data_to_rag.save_data_to_rag import _get_embeddings

logger = get_logger("services.answer_questions.answer_questions")


async def answer_question(job_id: str, question: str, query: str) -> Optional[str]:
    """
    Answer a single question using chunks retrieved from RAG.
    """
    logger.info(f"Answering one question using RAG for job_id: {job_id}")

    collection_name = f"job_{job_id}"
    chroma = chroma_client.connect()

    try:
        collection = chroma.get_collection(name=collection_name)
    except Exception as e:
        logger.error(f"Failed to get collection {collection_name}: {str(e)}", exc_info=True)
        raise

    logger.info(f"Answering question: {question}")

    query_embedding = _get_embeddings([query])[0]

    query_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    chunks = []
    if query_result and query_result.get("documents"):
        chunks = query_result["documents"][0]

    logger.info(f"Retrieved {len(chunks)} chunks for query: {query}")

    chunks_text = "\n\n".join(chunks)

    prompt = f"""Based on the following chunks of information, answer the question:

QUESTION: {question}

CHUNKS:
{chunks_text}

Provide a clear and concise answer based only on the information provided in the chunks. If the chunks don't contain relevant information to answer the question, state that."""

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that answers questions based on provided context chunks."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    answer = await llm.call(
        model=settings.cheap_model,
        messages=messages,
    )
    logger.info(f"Answer generated for question: {question}")
    return answer
