from __future__ import annotations
import math
import random
from typing import List

def generate_arrival_times(n: int, rate_rps: float, burstiness: float, seed: int) -> List[float]:
    rng = random.Random(seed)
    n = int(n)
    rate = float(rate_rps)
    if n <= 0:
        return []
    if rate <= 0:
        return [0.0 for _ in range(n)]
    mean_dt = 1.0 / rate
    cv = max(0.05, float(burstiness))
    dts: List[float] = []
    if abs(cv - 1.0) < 1e-06:
        for _ in range(n):
            u = max(1e-12, rng.random())
            dts.append(-math.log(u) * mean_dt)
    elif cv > 1.0:
        sigma2 = math.log(cv * cv + 1.0)
        sigma = math.sqrt(sigma2)
        mu = math.log(mean_dt) - 0.5 * sigma2
        for _ in range(n):
            z = rng.gauss(0.0, 1.0)
            dts.append(math.exp(mu + sigma * z))
    else:
        k = max(1, int(round(1.0 / (cv * cv))))
        for _ in range(n):
            s = 0.0
            for _j in range(k):
                u = max(1e-12, rng.random())
                s += -math.log(u) * (mean_dt / k)
            dts.append(s)
    t = 0.0
    arr: List[float] = []
    for dt in dts:
        t += float(dt)
        arr.append(t)
    t0 = arr[0]
    return [max(0.0, x - t0) for x in arr]
