from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, TypeAdapter

from result_schema import FactCheckRow
from rmq.constants import (
    CLAIM_VERIFIER,
    EXTRACT_AUDIO,
    EXTRACT_CLAIM_CLUSTERS,
    NOTIFY,
    RAG_STORAGE,
    SAVE_RESULT_TO_DB,
    TRANSCRIBE,
    TRANSLATE,
    URL_FETCHER,
    WEB_SCRAPER,
)

TRANSCRIPTION_CORRECT = "TRANSCRIPTION_CORRECT"


class WorkflowMessage(BaseModel):
    workflow_id: str = Field(..., description="Unique workflow run id")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Workflow payload data")


class TaskMessage(BaseModel):
    step: str = Field(..., description="Step name or type")
    payload: Dict[str, Any] = Field(..., description="Task payload data")
    priority: int = Field(default=5, description="Message priority")
    retry_count: int = Field(default=0, description="Retry count")


class ExtractAudioResult(BaseModel):
    audio_bytes_b64: str = Field(..., min_length=1)
    audio_format: str = Field(..., min_length=1)


class TranscribeResult(BaseModel):
    transcript_text: str = Field(..., min_length=1)


class TranscriptionCorrectResult(BaseModel):
    corrected_transcript: str = Field(..., min_length=1)


class TranslateResult(BaseModel):
    translated_text: str = Field(..., min_length=1)


class ExtractClaimClustersResult(BaseModel):
    clusters: list[list[str]]


class UrlEntry(BaseModel):
    title: str
    url: str


class UrlFetcherQueryResult(BaseModel):
    query: str
    urls: list[UrlEntry]


class UrlFetcherResult(BaseModel):
    results: list[UrlFetcherQueryResult]


class WebContextSource(BaseModel):
    source_id: int
    url: str
    title: str
    query: str
    content: str


class WebVerificationContext(BaseModel):
    sources: list[WebContextSource]


class WebScraperResult(BaseModel):
    context: WebVerificationContext


class RagReference(BaseModel):
    collection_name: str | None = None
    source_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)


class RagStorageResult(BaseModel):
    rag_reference: RagReference


class ClaimVerifierRow(BaseModel):
    claim: str
    verdict: str
    confidence: int = Field(ge=0, le=100)
    sources: list[str]
    explanation: str


class ClaimVerifierTable(BaseModel):
    rows: list[ClaimVerifierRow]


class ClaimVerifierResult(BaseModel):
    table: ClaimVerifierTable


class SavedHuntResult(BaseModel):
    hunt_id: int
    result: list[FactCheckRow]
    title: str
    summary: str
    trust_score: int = Field(ge=0, le=100)


class SaveResultToDbResult(BaseModel):
    saved: SavedHuntResult


class NotifyResult(BaseModel):
    sent: bool


STEP_RESULT_MODELS: dict[str, type[BaseModel]] = {
    EXTRACT_AUDIO: ExtractAudioResult,
    TRANSCRIBE: TranscribeResult,
    TRANSCRIPTION_CORRECT: TranscriptionCorrectResult,
    TRANSLATE: TranslateResult,
    EXTRACT_CLAIM_CLUSTERS: ExtractClaimClustersResult,
    URL_FETCHER: UrlFetcherResult,
    WEB_SCRAPER: WebScraperResult,
    RAG_STORAGE: RagStorageResult,
    CLAIM_VERIFIER: ClaimVerifierResult,
    SAVE_RESULT_TO_DB: SaveResultToDbResult,
    NOTIFY: NotifyResult,
}


def validate_task_step_result(step: str, result: dict[str, Any]) -> dict[str, Any]:
    model = STEP_RESULT_MODELS.get(step)
    if model is None:
        raise ValueError(f"No step result schema registered for step: {step}")
    return model.model_validate(result).model_dump()


class TaskRpcSuccessResponse(BaseModel):
    status: Literal["success"]
    step: str
    result: dict[str, Any]


class TaskRpcErrorResponse(BaseModel):
    status: Literal["error"]
    step: str
    error: str


TaskRpcResponse = TaskRpcSuccessResponse | TaskRpcErrorResponse
_TASK_RPC_RESPONSE_ADAPTER = TypeAdapter(TaskRpcResponse)


def parse_task_rpc_response(payload: dict[str, Any]) -> TaskRpcResponse:
    return _TASK_RPC_RESPONSE_ADAPTER.validate_python(payload)
