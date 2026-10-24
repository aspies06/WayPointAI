"""Runs the local Hugging Face model for optional roadmap tips.

torch and transformers are imported lazily so the planner and tests work
without them installed.
"""
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from functools import lru_cache
from typing import Callable

MODEL_ID = os.getenv("ROADMAP_MODEL_ID", "AnusmitaRC21/smolified-resume-analyzer")
TIMEOUT_S = float(os.getenv("ROADMAP_TIMEOUT_S", "45"))
MAX_NEW_TOKENS = 400
# Concurrent generations. Each one holds a CPU core busy, so raise this with the machine size.
WORKERS = max(1, int(os.getenv("ROADMAP_MODEL_WORKERS", "1")))

# (messages, max_new_tokens) -> generated text. Tests pass a fake with this shape.
TextModel = Callable[[list[dict], int], str]

_pool = ThreadPoolExecutor(max_workers=WORKERS)
_slots = threading.BoundedSemaphore(WORKERS)
_load_lock = threading.Lock()


class ModelBusy(RuntimeError):
    """Every worker is taken; the caller should show the basic roadmap now."""


def _load(model_id: str):
    with _load_lock:  # two first requests at once must not load the model twice
        return _load_once(model_id)


@lru_cache(maxsize=1)
def _load_once(model_id: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float32)
    model.to("cpu")
    model.eval()
    return tokenizer, model


def hf_generate(messages: list[dict], max_new_tokens: int = MAX_NEW_TOKENS) -> str:
    import torch

    tokenizer, model = _load(MODEL_ID)
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if tokenizer.bos_token:
        prompt = prompt.removeprefix(tokenizer.bos_token)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=8192)
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def generate_with_timeout(model: TextModel, messages: list[dict],
                          max_new_tokens: int = MAX_NEW_TOKENS, timeout_s: float = TIMEOUT_S) -> str:
    """Raises ModelBusy at once if every worker is taken, so requests never queue
    behind each other, and TimeoutError if the model is too slow. The worker thread
    can't be killed, so a slow call finishes in the background (still holding its
    slot) and its result is dropped."""
    if not _slots.acquire(blocking=False):
        raise ModelBusy(f"all {WORKERS} local model worker(s) are busy")
    try:
        future = _pool.submit(model, messages, max_new_tokens)
    except BaseException:
        _slots.release()
        raise
    future.add_done_callback(lambda _: _slots.release())
    try:
        return future.result(timeout=timeout_s)
    except FutureTimeout:
        raise TimeoutError(f"local model took longer than {timeout_s}s")


def warm_up() -> None:
    """Download and load the model ahead of time (e.g. at app start)."""
    _load(MODEL_ID)
