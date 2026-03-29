from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from greenslo.orchestrator.green_slo_contract import GreenSLO
from greenslo.orchestrator.scheduler import PriorityBatchScheduler

@dataclass
class RouteDecision:
    scheduler: PriorityBatchScheduler
    max_new_tokens: int
    reason: str

class GreenRouter:

    def __init__(self, small_sched: PriorityBatchScheduler, large_sched: PriorityBatchScheduler) -> None:
        self.small = small_sched
        self.large = large_sched

    def choose_for_writer(self, prompt: str, contract: GreenSLO, remaining_energy_j: Optional[float]) -> RouteDecision:
        max_new = int(contract.max_new_tokens)
        if contract.tier.lower() == 'eco':
            sched = self.small
            reason = 'eco_tier_small_default'
        else:
            sched = self.large
            reason = 'default_large'
        pred = sched.predict_energy_j(prompt, max_new)
        if remaining_energy_j is not None and pred is not None and (pred > remaining_energy_j):
            if pred > 0:
                scale = max(0.2, float(remaining_energy_j) / float(pred))
                max_new = max(32, int(max_new * scale))
                reason = f'cap_tokens_energy_budget(scale={scale:.2f})'
        pred2 = sched.predict_energy_j(prompt, max_new)
        if remaining_energy_j is not None and pred2 is not None and (pred2 > remaining_energy_j):
            sched = self.small
            reason = 'route_to_small_energy_budget'
        return RouteDecision(scheduler=sched, max_new_tokens=max_new, reason=reason)
