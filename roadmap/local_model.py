"""Runs the local Hugging Face model for optional roadmap tips.

torch and transformers are imported lazily so the planner and tests work
without them installed.

Device: ROADMAP_DEVICE=auto (default) uses the GPU (NVIDIA CUDA or Apple
Metal/MPS) only when it has enough free memory for the model plus working
room; otherwise the CPU. Set cpu, cuda or mps to choose. If moving the model
to the GPU fails, it stays on the CPU.
"""
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from functools import lru_cache
from typing import Callable, Optional

MODEL_ID = os.getenv("ROADMAP_MODEL_ID", "AnusmitaRC21/smolified-resume-analyzer")
TIMEOUT_S = float(os.getenv("ROADMAP_TIMEOUT_S", "120"))  # long enough to write a full set of tips
MAX_NEW_TOKENS = 400
DEVICE = os.getenv("ROADMAP_DEVICE", "auto").strip().lower()  # auto, cpu, cuda or mps
GPU_HEADROOM = 1.5  # weights plus room for activations and the attention cache
# Concurrent generations. Each one holds a CPU core busy, so raise this with the machine size.
WORKERS = max(1, int(os.getenv("ROADMAP_MODEL_WORKERS", "1")))

# (messages, max_new_tokens) -> generated text. Tests pass a fake with this shape.
TextModel = Callable[[list[dict], int], str]

_pool = ThreadPoolExecutor(max_workers=WORKERS)
_slots = threading.BoundedSemaphore(WORKERS)
_load_lock = threading.Lock()


log = logging.getLogger("roadmap")


class ModelBusy(RuntimeError):
    """Every worker is taken; the caller should show the basic roadmap now."""


def _load(model_id: str):
    with _load_lock:  # two first requests at once must not load the model twice
        return _load_once(model_id)


def _gpu_kind(torch) -> Optional[str]:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return None


def _gpu_free_bytes(torch, kind: str) -> int:
    if kind == "cuda":
        free, _total = torch.cuda.mem_get_info()
        return int(free)
    # Apple GPUs share system memory; Metal reports how much it's willing to use.
    budget = getattr(torch.mps, "recommended_max_memory", None)
    if budget is None:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") * 0.5)
    return int(budget() - torch.mps.driver_allocated_memory())


def choose_device(torch, weight_bytes: int, requested: str = DEVICE) -> tuple[str, str]:
    """(device, reason). The GPU only when it's asked for or available, and has room."""
    if requested == "cpu":
        return "cpu", "ROADMAP_DEVICE=cpu"
    available = _gpu_kind(torch)
    kind = requested if requested in ("cuda", "mps") else available
    if kind is None or kind != available:
        return "cpu", f"no usable {'GPU' if kind is None else kind.upper()} found"
    need = int(weight_bytes * GPU_HEADROOM)
    free = _gpu_free_bytes(torch, kind)
    if free < need:
        return "cpu", f"{kind} has {free / 1e9:.1f} GB free; the model needs about {need / 1e9:.1f} GB"
    return kind, f"{kind} has {free / 1e9:.1f} GB free; the model needs about {need / 1e9:.1f} GB"


@lru_cache(maxsize=1)
def _load_once(model_id: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float32)
    weight_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    device, reason = choose_device(torch, weight_bytes)
    if device != "cpu":
        try:
            # bfloat16 halves memory on NVIDIA cards that support it; Apple GPUs stay in float32,
            # because half precision can make this model's output unstable there.
            dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
            model.to(device, dtype=dtype)
        except RuntimeError as error:  # out of memory, driver problem, ...
            model.to("cpu", dtype=torch.float32)
            device, reason = "cpu", f"moving to the GPU failed ({type(error).__name__})"
    log.info("tip model on %s: %s", device, reason)
    model.eval()
    return tokenizer, model, device


def loaded_device() -> Optional[str]:
    """Where the model runs, once loaded (None before the first use)."""
    return _load_once(MODEL_ID)[2] if _load_once.cache_info().currsize else None


def hf_generate(messages: list[dict], max_new_tokens: int = MAX_NEW_TOKENS) -> str:
    import torch

    tokenizer, model, device = _load(MODEL_ID)
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if tokenizer.bos_token:
        prompt = prompt.removeprefix(tokenizer.bos_token)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=8192).to(device)
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
