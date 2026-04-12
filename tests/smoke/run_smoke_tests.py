import os
import sys

import httpx


ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8000")
SYSTEM1_URL = os.getenv("SYSTEM1_URL", "http://127.0.0.1:8001")
SYSTEM2_URL = os.getenv("SYSTEM2_URL", "http://127.0.0.1:8002")
SYSTEM3_URL = os.getenv("SYSTEM3_URL", "http://127.0.0.1:8003")


def assert_status(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label} failed: {response.status_code} {response.text}")


def main() -> int:
    with httpx.Client(timeout=30.0) as client:
        for name, base_url in {
            "system1": SYSTEM1_URL,
            "system2": SYSTEM2_URL,
            "system3": SYSTEM3_URL,
            "orchestrator": ORCHESTRATOR_URL,
        }.items():
            assert_status(client.get(f"{base_url}/health"), 200, f"{name} health")
            assert_status(client.get(f"{base_url}/ready"), 200, f"{name} ready")

        data_title = "TTY_TENTITY_Column UPDATEDDATE missing"
        infra_title = "FIN_TORDER_cluster timeout in nightly run"

        parse_data = client.post(f"{SYSTEM1_URL}/parse-and-classify", json={"raw_title": data_title})
        assert_status(parse_data, 200, "system1 data parse")
        system1_data = parse_data.json()

        parse_infra = client.post(f"{SYSTEM1_URL}/parse-and-classify", json={"raw_title": infra_title})
        assert_status(parse_infra, 200, "system1 infra parse")

        resolve = client.post(
            f"{SYSTEM2_URL}/resolve-metadata",
            json={
                "division": system1_data["division"],
                "table_name": system1_data["table_name"],
                "issue": system1_data["issue"],
                "mentioned_columns": system1_data["mentioned_columns"],
            },
        )
        assert_status(resolve, 200, "system2 resolve")
        system2_data = resolve.json()

        analyze = client.post(
            f"{SYSTEM3_URL}/analyze-incident",
            json={"system1": system1_data, "system2": system2_data},
        )
        assert_status(analyze, 200, "system3 analyze")
        system3_data = analyze.json()
        if "likely_root_cause" not in system3_data:
            raise AssertionError("system3 response missing likely_root_cause")

        chat_data = client.post(f"{ORCHESTRATOR_URL}/chat/investigate", json={"raw_title": data_title})
        assert_status(chat_data, 200, "orchestrator data flow")
        chat_payload = chat_data.json()
        if "recommended_next_step" not in chat_data.text:
            raise AssertionError("chat data response missing recommended_next_step")
        if chat_payload.get("system4") is None:
            raise AssertionError("chat data response missing system4 SQL analysis")
        if not any(step["name"] == "system4" for step in chat_payload["steps"]):
            raise AssertionError("chat data response missing system4 progress step")

        chat_infra = client.post(f"{ORCHESTRATOR_URL}/chat/investigate", json={"raw_title": infra_title})
        assert_status(chat_infra, 200, "orchestrator infra flow")
        infra_payload = chat_infra.json()
        if infra_payload["system3"] is not None:
            raise AssertionError("infra flow should short-circuit before system3")
        if infra_payload["system4"] is not None:
            raise AssertionError("infra flow should short-circuit before system4")

    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
