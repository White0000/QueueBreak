from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from rich.console import Console
console = Console()

@dataclass
class LLMOutput:
    text: str
    tokens_in: int
    tokens_out: int

class LLMService:

    def __init__(self, model_id: str, device: str='auto', dtype: str='auto') -> None:
        self.model_id = model_id
        self.device_pref = device
        self.dtype_pref = dtype
        self._mock = False
        self._torch = None
        self._model = None
        self._tokenizer = None
        self._device = 'cpu'
        self._dtype = None
        self._init()

    @property
    def is_mock(self) -> bool:
        return self._mock

    @property
    def device(self) -> str:
        return self._device

    def _init(self) -> None:
        try:
            import torch
            self._torch = torch
        except Exception:
            self._mock = True
            console.print(f'[yellow]torch is not available; using MockLLM for {self.model_id}[/yellow]')
            return
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception:
            self._mock = True
            console.print(f'[yellow]transformers is not available; using MockLLM for {self.model_id}[/yellow]')
            return
        if self.device_pref == 'auto':
            if hasattr(self._torch, 'cuda') and self._torch.cuda.is_available():
                self._device = 'cuda'
            else:
                self._device = 'cpu'
        else:
            self._device = self.device_pref
        if self.dtype_pref == 'auto':
            if self._device == 'cuda':
                self._dtype = getattr(self._torch, 'float16')
            else:
                self._dtype = getattr(self._torch, 'float32')
        else:
            self._dtype = getattr(self._torch, self.dtype_pref)
        try:
            console.print(f'[cyan]Loading model:[/cyan] {self.model_id} on {self._device} ({self._dtype})')
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, use_fast=True)
            if getattr(self._tokenizer, 'pad_token', None) is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            if self._device == 'cuda':
                self._model = AutoModelForCausalLM.from_pretrained(self.model_id, torch_dtype=self._dtype, low_cpu_mem_usage=True).to(self._device)
            else:
                self._model = AutoModelForCausalLM.from_pretrained(self.model_id, torch_dtype=self._dtype, low_cpu_mem_usage=True)
            self._model.eval()
            _ = self.generate_batch(['Hello'], max_new_tokens=8, temperature=0.0, do_sample=False)
        except Exception as e:
            self._mock = True
            console.print(f'[yellow]Failed to load {self.model_id}. Using MockLLM. Error: {e}[/yellow]')
            self._model = None
            self._tokenizer = None

    def generate_batch(self, prompts: List[str], max_new_tokens: int, temperature: float=0.0, do_sample: bool=False) -> List[LLMOutput]:
        if self._mock or self._model is None or self._tokenizer is None or (self._torch is None):
            outs: List[LLMOutput] = []
            for p in prompts:
                text = '{"ok": true, "note": "mock", "len": %d}' % len(p)
                outs.append(LLMOutput(text=text, tokens_in=max(1, len(p) // 4), tokens_out=max(1, len(text) // 4)))
            return outs
        tok = self._tokenizer
        torch = self._torch
        enc = tok(prompts, return_tensors='pt', padding=True, truncation=True)
        input_ids = enc['input_ids']
        attention_mask = enc['attention_mask']
        if self._device == 'cuda':
            input_ids = input_ids.to(self._device)
            attention_mask = attention_mask.to(self._device)
        lengths_in = attention_mask.sum(dim=1).tolist()
        gen_kwargs: Dict[str, Any] = dict(max_new_tokens=int(max_new_tokens), do_sample=bool(do_sample), temperature=float(temperature), pad_token_id=tok.eos_token_id)
        with torch.inference_mode():
            outputs = self._model.generate(input_ids=input_ids, attention_mask=attention_mask, **gen_kwargs)
        results: List[LLMOutput] = []
        for i in range(len(prompts)):
            in_len = int(lengths_in[i])
            out_ids = outputs[i][in_len:]
            text = tok.decode(out_ids, skip_special_tokens=True)
            tokens_out = int(out_ids.numel())
            results.append(LLMOutput(text=text, tokens_in=in_len, tokens_out=tokens_out))
        return results
