from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from greenslo.measurement.nvml_sampler import NVMLSampler
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.llm_service import LLMService

@dataclass
class LLMCallResult:
    text: str
    tokens_in: int
    tokens_out: int
    start_t: float
    end_t: float
    energy_j: Optional[float]

@dataclass
class _QueuedCall:
    prompt: str
    max_new_tokens: int
    contract: GreenSLO
    meta: Dict[str, Any]
    created_t: float
    fut: asyncio.Future

class PriorityBatchScheduler:

    def __init__(self, llm: LLMService, sampler: NVMLSampler, gpu_lock: asyncio.Lock, name: str) -> None:
        self.llm = llm
        self.sampler = sampler
        self.gpu_lock = gpu_lock
        self.name = name
        self._q: 'asyncio.Queue[_QueuedCall]' = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._closed = False
        self._avg_j_per_token: Optional[float] = None

    @property
    def avg_j_per_token(self) -> Optional[float]:
        return self._avg_j_per_token

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._worker_loop(), name=f'Scheduler[{self.name}]')

    async def close(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
        self._task = None

    async def submit(self, prompt: str, max_new_tokens: int, contract: GreenSLO, meta: Optional[Dict[str, Any]]=None) -> LLMCallResult:
        if self._closed:
            raise RuntimeError('scheduler_closed')
        if self._task is None:
            self.start()
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        item = _QueuedCall(prompt=prompt, max_new_tokens=int(max_new_tokens), contract=contract, meta=dict(meta or {}), created_t=time.perf_counter(), fut=fut)
        await self._q.put(item)
        return await fut

    def _estimate_input_tokens(self, prompt: str) -> int:
        return max(1, len(prompt) // 4)

    def predict_energy_j(self, prompt: str, max_new_tokens: int) -> Optional[float]:
        if self._avg_j_per_token is None:
            return None
        tokens = self._estimate_input_tokens(prompt) + int(max_new_tokens)
        return float(self._avg_j_per_token) * float(tokens)

    async def _worker_loop(self) -> None:
        while True:
            first = await self._q.get()
            batch: List[_QueuedCall] = [first]
            min_window_ms = min((x.contract.waiting_window_ms for x in batch))
            t_deadline = time.perf_counter() + min_window_ms / 1000.0

            def workflow_deadline(x: _QueuedCall) -> float:
                return x.created_t + x.contract.p99_ms / 1000.0
            t_earliest = min((workflow_deadline(x) for x in batch))
            if time.perf_counter() + min_window_ms / 1000.0 > t_earliest:
                t_deadline = time.perf_counter()
            approx_tokens = sum((self._estimate_input_tokens(x.prompt) for x in batch))
            max_batch_size = min((x.contract.max_batch_size for x in batch))
            max_batch_tokens = min((x.contract.max_batch_tokens for x in batch))
            while time.perf_counter() < t_deadline:
                if len(batch) >= max_batch_size:
                    break
                if approx_tokens >= max_batch_tokens:
                    break
                try:
                    item = self._q.get_nowait()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.001)
                    continue
                batch.append(item)
                approx_tokens += self._estimate_input_tokens(item.prompt)
                min_window_ms = min(min_window_ms, item.contract.waiting_window_ms)
                max_batch_size = min(max_batch_size, item.contract.max_batch_size)
                max_batch_tokens = min(max_batch_tokens, item.contract.max_batch_tokens)
                t_deadline = min(t_deadline, time.perf_counter() + min_window_ms / 1000.0)
            prompts = [x.prompt for x in batch]
            max_new_tokens = min((x.max_new_tokens for x in batch))
            async with self.gpu_lock:
                t0 = time.perf_counter()
                outs = await asyncio.to_thread(self.llm.generate_batch, prompts, max_new_tokens=max_new_tokens, temperature=0.0, do_sample=False)
                t1 = time.perf_counter()
            e_batch = self.sampler.energy_joules(t0, t1, subtract_baseline=True)
            total_tokens = sum((max(1, o.tokens_in + o.tokens_out) for o in outs))
            per_token = float(e_batch) / float(total_tokens) if e_batch is not None and total_tokens > 0 else None
            if per_token is not None:
                if self._avg_j_per_token is None:
                    self._avg_j_per_token = per_token
                else:
                    self._avg_j_per_token = 0.9 * self._avg_j_per_token + 0.1 * per_token
            for item, o in zip(batch, outs):
                e_call = None
                if per_token is not None:
                    e_call = per_token * float(max(1, o.tokens_in + o.tokens_out))
                res = LLMCallResult(text=o.text, tokens_in=o.tokens_in, tokens_out=o.tokens_out, start_t=t0, end_t=t1, energy_j=e_call)
                if not item.fut.cancelled():
                    item.fut.set_result(res)
