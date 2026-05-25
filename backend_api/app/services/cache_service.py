import json
import redis
import logging
import numpy as np
from typing import Optional, Dict

logger = logging.getLogger(__name__)

ROLLING_WINDOW = 10  

class RedisCacheService:

    def __init__(self, host="localhost", port=6379, db=0):
        try:
            self.client = redis.Redis(
                host=host, port=port, db=db,
                decode_responses=True
            )
            self.client.ping()
            logger.info(f"Redis connected: {host}:{port} db={db}")
        except redis.ConnectionError:
            logger.error(
                "CRITICAL: Could not connect to Redis. "
                "Ensure the server is running. "
                "Falling back to population baseline only."
            )
            self.client = None

    def _generate_key(self, case_no: str, biomarker_code: str) -> str:
        biomarker_code = str(biomarker_code).strip().upper()
        return f"patient_baseline:{case_no}:{biomarker_code}"

    def get_patient_history(
        self,
        case_no: str,
        biomarker_code: str,
    ) -> Optional[Dict]:

        if not self.client or not case_no:
            return None

        key  = self._generate_key(case_no, biomarker_code)
        data = self.client.get(key)

        return json.loads(data) if data else None

    def update_patient_history(
        self,
        case_no        : str,
        biomarker_code : str,
        new_value      : float,
        timestamp      : str = None,
    ) -> None:

        if not self.client or not case_no:
            return

        key          = self._generate_key(case_no, biomarker_code)
        current_data = self.get_patient_history(case_no, biomarker_code)

        if current_data:
            values     = current_data.get("values", [])
            timestamps = current_data.get("timestamps", [])
        else:
            values     = []
            timestamps = []
        values.append(round(float(new_value), 4))
        if timestamp:
            timestamps.append(str(timestamp))
        values     = values[-ROLLING_WINDOW:]
        timestamps = timestamps[-ROLLING_WINDOW:]

        n    = len(values)
        mean = round(float(np.mean(values)), 4)

        # std requires n >= 2
        # return None (not 0.0) when std can't be computed
        # so stat_engine falls through to population baseline
        if n >= 2:
            std = float(np.std(values, ddof=1))
            std = round(std, 4) if std > 0 else None
        else:
            std = None

        # trend requires n >= 3
        trend = None
        if n >= 3:
            x     = np.arange(n, dtype=float)
            trend = round(float(np.polyfit(x, values, 1)[0]), 4)
            # positive = rising, negative = falling

        updated = {
            "values"    : values,
            "timestamps": timestamps,
            "mean"      : mean,
            "std"       : std,       # None if n < 2 or no variance
            "trend"     : trend,     # None if n < 3
            "n"         : n,
            "status"    : "active" if n >= 2 else "insufficient_history",
        }

        try:
            self.client.set(key, json.dumps(updated))
        except redis.RedisError as e:
            logger.error(f"Redis write failed for {key}: {e}")