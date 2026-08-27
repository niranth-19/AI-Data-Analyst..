import json
from datetime import datetime
from typing import Any

import numpy as np


def to_serializable(value: Any) -> Any:
    """Convert numpy/pandas/datetime values to JSON-serializable Python types."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (np.datetime64,)):
        return str(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_serializable(v) for v in value]
    return str(value)


def dumps_json(data: Any) -> str:
    return json.dumps(to_serializable(data))
