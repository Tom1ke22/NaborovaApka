import json
import logging
import sys


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(env: str) -> None:
    if env != "production":
        # Lokálne: čitateľný plain text
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="%(levelname)-8s  %(name)s  %(message)s",
            force=True,
        )
        return

    # Produkcia (Cloud Run): každý riadok = JSON objekt
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Uvicorn logery presmerujeme do nášho handlera
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        lgr = logging.getLogger(name)
        lgr.handlers.clear()
        lgr.propagate = True
