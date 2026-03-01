import json
import os
import threading
import time


class ApiRecorder:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def record(self, method, params, response):
        payload = {
            "ts": time.time(),
            "method": method,
            "params": params,
            "response": response,
        }
        line = json.dumps(payload, ensure_ascii=True)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")


class ApiReplay:
    def __init__(self, path):
        self.path = path
        self._records = {}
        self._cursor = {}
        self._load()

    def _make_key(self, method, params):
        return method + ":" + json.dumps(params, sort_keys=True, ensure_ascii=True)

    def _load(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Replay data not found: {self.path}")
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                key = self._make_key(item["method"], item.get("params", {}))
                self._records.setdefault(key, []).append(item.get("response"))

    def get_next(self, method, params):
        key = self._make_key(method, params)
        if key not in self._records:
            raise KeyError(f"No recorded response for {method} {params}")
        idx = self._cursor.get(key, 0)
        responses = self._records[key]
        if idx >= len(responses):
            raise IndexError(f"No more recorded responses for {method} {params}")
        self._cursor[key] = idx + 1
        return responses[idx]
