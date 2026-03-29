from __future__ import annotations
import threading
import time
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class PowerSample:
    t: float
    power_w: float

class NVMLSampler:

    def __init__(self, enable: bool=True, sample_hz: int=20) -> None:
        self.enable = enable
        self.sample_hz = max(1, int(sample_hz))
        self._dt = 1.0 / self.sample_hz
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._samples: List[PowerSample] = []
        self._baseline_w: Optional[float] = None
        self._nvml_ok = False
        self._handle = None
        if self.enable:
            self._try_init_nvml()

    def _try_init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            _ = pynvml.nvmlDeviceGetPowerUsage(self._handle)
            self._nvml_ok = True
        except Exception:
            self._nvml_ok = False
            self._handle = None

    @property
    def nvml_available(self) -> bool:
        return self.enable and self._nvml_ok and (self._handle is not None)

    @property
    def baseline_w(self) -> Optional[float]:
        return self._baseline_w

    @property
    def samples(self) -> List[PowerSample]:
        return self._samples

    def start(self) -> None:
        if not self.nvml_available:
            return
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='NVMLSampler', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None

    def reset(self) -> None:
        self._samples = []

    def _read_power_w(self) -> float:
        import pynvml
        mw = pynvml.nvmlDeviceGetPowerUsage(self._handle)
        return float(mw) / 1000.0

    def _run(self) -> None:
        next_t = time.perf_counter()
        while not self._stop.is_set():
            now = time.perf_counter()
            if now >= next_t:
                try:
                    p = self._read_power_w()
                    self._samples.append(PowerSample(t=now, power_w=p))
                except Exception:
                    pass
                next_t = now + self._dt
            else:
                time.sleep(min(0.001, next_t - now))

    def estimate_idle_baseline(self, seconds: float=3.0) -> Optional[float]:
        if not self.nvml_available:
            self._baseline_w = None
            return None
        tmp: List[float] = []
        end = time.perf_counter() + float(seconds)
        while time.perf_counter() < end:
            try:
                tmp.append(self._read_power_w())
            except Exception:
                pass
            time.sleep(self._dt)
        if not tmp:
            self._baseline_w = None
            return None
        tmp_sorted = sorted(tmp)
        mid = len(tmp_sorted) // 2
        baseline = tmp_sorted[mid] if len(tmp_sorted) % 2 == 1 else 0.5 * (tmp_sorted[mid - 1] + tmp_sorted[mid])
        self._baseline_w = float(baseline)
        return self._baseline_w

    def energy_joules(self, t0: float, t1: float, subtract_baseline: bool=True) -> Optional[float]:
        if not self.nvml_available:
            return None
        if t1 <= t0:
            return 0.0
        samples = self._samples
        if len(samples) < 2:
            return None
        seg = [s for s in samples if t0 <= s.t <= t1]
        if len(seg) < 2:
            return None
        baseline = self._baseline_w if subtract_baseline and self._baseline_w is not None else 0.0
        e = 0.0
        for a, b in zip(seg[:-1], seg[1:]):
            pa = max(a.power_w - baseline, 0.0)
            pb = max(b.power_w - baseline, 0.0)
            dt = b.t - a.t
            e += 0.5 * (pa + pb) * dt
        return float(e)
