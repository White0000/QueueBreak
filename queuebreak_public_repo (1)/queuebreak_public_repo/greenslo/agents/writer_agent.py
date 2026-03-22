from __future__ import annotations
import json
from typing import Any, Dict, Optional
from greenslo.agents.types import WriterResult
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.router import GreenRouter
from greenslo.utils.json import try_parse_json

class WriterAgent:

    def __init__(self, router: GreenRouter) -> None:
        self.router = router

    def _fallback(self, tool_results: Dict[str, Any]) -> Dict[str, Any]:
        score = None
        try:
            score = float(tool_results.get('anomaly_score', {}).get('score', 0.0))
        except Exception:
            score = 0.0
        action = 'ALERT' if score and score > 0.5 else 'OK'
        return {'action': action, 'summary': 'Fallback response (LLM output was not valid JSON).', 'confidence': 0.5, 'anomaly_score': score}

    async def write(self, workflow_id: str, user_request: str, tool_results: Dict[str, Any], contract: GreenSLO, remaining_energy_j: Optional[float]) -> WriterResult:
        prompt = f'You are an assistant for an IoT operations workflow.\nGiven the user request and tool results, produce a SHORT JSON response.\nReturn ONLY valid JSON with keys: action, summary, confidence.\nAllowed action: OK, ALERT, THROTTLE, REBOOT.\n\nUser request:\n{user_request}\n\nTool results (JSON):\n{json.dumps(tool_results, ensure_ascii=False)}\n'
        decision = self.router.choose_for_writer(prompt, contract=contract, remaining_energy_j=remaining_energy_j)
        res = await decision.scheduler.submit(prompt, max_new_tokens=decision.max_new_tokens, contract=contract, meta={'workflow_id': workflow_id, 'step': 'writer', 'route_reason': decision.reason})
        obj = try_parse_json(res.text)
        if isinstance(obj, dict) and 'action' in obj and ('summary' in obj):
            if 'confidence' not in obj:
                obj['confidence'] = 0.7
            return WriterResult(obj=obj, raw=res.text, ok=True, llm_tokens_in=res.tokens_in, llm_tokens_out=res.tokens_out, llm_start_t=res.start_t, llm_end_t=res.end_t, llm_energy_j=res.energy_j, route_reason=decision.reason)
        fb = self._fallback(tool_results)
        return WriterResult(obj=fb, raw=res.text, ok=False, llm_tokens_in=res.tokens_in, llm_tokens_out=res.tokens_out, llm_start_t=res.start_t, llm_end_t=res.end_t, llm_energy_j=res.energy_j, route_reason=decision.reason)
