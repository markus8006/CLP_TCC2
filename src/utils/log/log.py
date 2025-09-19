import logging
import json
from datetime import datetime
from datetime import timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "evento": record.msg if isinstance(record.msg, str) else str(record.msg),
            "detalhes": record.args if record.args else None,
        }
        return json.dumps(log_obj)

def setup_logger():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger
