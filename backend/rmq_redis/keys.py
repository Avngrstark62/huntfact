def job_prefix(job_id: str) -> str:
    return f"job:{job_id}"


def job_meta_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:meta"


def job_steps_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:steps"


def job_keys_registry_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:keys"


def job_utterances_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:utterances"


def job_utterances_en_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:utterances_en"


def job_items_index_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:items:index"


def job_item_base_key(job_id: str, item_id: str) -> str:
    return f"{job_prefix(job_id)}:items:base:{item_id}"


def job_item_urls_key(job_id: str, item_id: str) -> str:
    return f"{job_prefix(job_id)}:items:urls:{item_id}"


def job_item_selected_key(job_id: str, item_id: str) -> str:
    return f"{job_prefix(job_id)}:items:selected:{item_id}"


def job_item_answer_key(job_id: str, item_id: str) -> str:
    return f"{job_prefix(job_id)}:items:answer:{item_id}"


def job_audio_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:artifact:audio"


def job_audio_meta_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:artifact:audio_meta"


def job_pages_index_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:artifact:pages:index"


def job_page_key(job_id: str, page_id: str) -> str:
    return f"{job_prefix(job_id)}:artifact:pages:{page_id}"


def job_result_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}:result"
