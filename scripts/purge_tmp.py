from pathlib import Path
import time

from app.config import settings


def purge():
    now = time.time()
    age_sec = settings.purge_age_hours * 3600
    for d in [settings.tmp_dir, settings.upload_dir]:
        for p in Path(d).glob("*"):
            try:
                if p.is_file() and now - p.stat().st_mtime > age_sec:
                    p.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    purge()
    print("purged")
