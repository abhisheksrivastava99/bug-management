import os
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(SHARED_SRC))

from bug_management_shared.observability_fixture_builder import (  # noqa: E402
    SAMPLE_KQL_QUERIES,
    build_observability_fixture_bundle,
    write_observability_fixture_bundle,
)


def main() -> None:
    seed = int(os.getenv("BM_FIXTURE_SEED", os.getenv("BM_OBSERVABILITY_SEED", "29")))
    now_utc = _parse_optional_datetime(os.getenv("BM_OBSERVABILITY_NOW"))
    bundle = build_observability_fixture_bundle(seed=seed, now_utc=now_utc)
    paths = write_observability_fixture_bundle(bundle)
    print(
        f"Wrote {len(bundle['pipeline_metadata'])} pipeline metadata rows, "
        f"{len(bundle['ADFTriggerRun'])} trigger rows, "
        f"{len(bundle['ADFPipelineRun'])} pipeline rows, and "
        f"{len(bundle['ADFActivityRun'])} activity rows to {paths['manifest']} using seed={seed}."
    )
    print("\nSample KQL queries:")
    for index, query in enumerate(SAMPLE_KQL_QUERIES, start=1):
        print(f"\n[{index}]\n{query}")


def _parse_optional_datetime(raw_value):
    if not raw_value:
        return None
    normalized = raw_value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


if __name__ == "__main__":
    main()
