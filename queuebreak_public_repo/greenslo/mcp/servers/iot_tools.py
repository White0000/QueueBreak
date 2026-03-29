from __future__ import annotations
import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List
from greenslo.mcp.protocol import MCPServerBase, ToolSpec

def _schema(properties: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}

@dataclass
class ToolServerConfig:
    base_latency_ms: int = 60
    jitter_ms: int = 50
    failure_prob: float = 0.15

class IoTToolServer(MCPServerBase):

    def __init__(self, cfg: ToolServerConfig, seed: int=42) -> None:
        self.cfg = cfg
        self._rng = random.Random(seed)
        self._tools = [ToolSpec(name='sensor_read', description='Read a sensor by id and return recent measurements.', input_schema=_schema({'sensor_id': {'type': 'string'}, 'n': {'type': 'integer', 'minimum': 1, 'maximum': 32}}, ['sensor_id']), output_schema=_schema({'sensor_id': {'type': 'string'}, 'values': {'type': 'array', 'items': {'type': 'number'}}, 'ts': {'type': 'number'}}, ['sensor_id', 'values', 'ts'])), ToolSpec(name='anomaly_score', description='Compute a simple anomaly score from numeric measurements.', input_schema=_schema({'values': {'type': 'array', 'items': {'type': 'number'}}}, ['values']), output_schema=_schema({'score': {'type': 'number'}}, ['score'])), ToolSpec(name='device_status', description='Return current device status (online/offline, battery, temperature).', input_schema=_schema({'device_id': {'type': 'string'}}, ['device_id']), output_schema=_schema({'device_id': {'type': 'string'}, 'online': {'type': 'boolean'}, 'battery': {'type': 'number'}, 'temp_c': {'type': 'number'}}, ['device_id', 'online', 'battery', 'temp_c'])), ToolSpec(name='actuate', description='Send an actuation command to a device (e.g., reboot, throttle, alert).', input_schema=_schema({'device_id': {'type': 'string'}, 'action': {'type': 'string'}}, ['device_id', 'action']), output_schema=_schema({'ok': {'type': 'boolean'}, 'echo': {'type': 'object'}}, ['ok', 'echo']))]

    def list_tools(self) -> List[ToolSpec]:
        return list(self._tools)

    async def _sleep_latency(self) -> None:
        ms = self.cfg.base_latency_ms + self._rng.randint(0, max(0, self.cfg.jitter_ms))
        await asyncio.sleep(ms / 1000.0)

    def _maybe_fail(self) -> None:
        if self._rng.random() < float(self.cfg.failure_prob):
            raise RuntimeError('tool_error: simulated failure')

    async def call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        await self._sleep_latency()
        self._maybe_fail()
        if name == 'sensor_read':
            sensor_id = str(args.get('sensor_id', 'S1'))
            n = int(args.get('n', 8))
            n = max(1, min(n, 32))
            base = 50.0 + 10.0 * self._rng.random()
            values = [base + self._rng.gauss(0, 2.0) for _ in range(n)]
            if self._rng.random() < 0.2:
                values[self._rng.randint(0, n - 1)] += 15.0 + 10.0 * self._rng.random()
            return {'sensor_id': sensor_id, 'values': values, 'ts': time.time()}
        if name == 'anomaly_score':
            values = args.get('values', [])
            if not values:
                return {'score': 0.0}
            mean = sum((float(v) for v in values)) / len(values)
            score = max(0.0, max((abs(float(v) - mean) for v in values)) - 3.0) / 10.0
            return {'score': float(score)}
        if name == 'device_status':
            device_id = str(args.get('device_id', 'D1'))
            online = self._rng.random() > 0.05
            battery = 0.2 + 0.8 * self._rng.random()
            temp_c = 30.0 + 20.0 * self._rng.random()
            return {'device_id': device_id, 'online': bool(online), 'battery': float(battery), 'temp_c': float(temp_c)}
        if name == 'actuate':
            device_id = str(args.get('device_id', 'D1'))
            action = str(args.get('action', 'alert'))
            return {'ok': True, 'echo': {'device_id': device_id, 'action': action}}
        raise KeyError(f'unknown_tool: {name}')
