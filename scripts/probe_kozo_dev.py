#!/usr/bin/env python3
"""Produce a JSON end-to-end probe of a running KO-POCHI deployment.

The query is supplied explicitly on the command line.  The output contains only
values observed from live HTTP responses during this invocation.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, help="backend origin, for example http://127.0.0.1:8010")
    parser.add_argument("--gateway", required=True, help="nginx origin, for example http://127.0.0.1:8090")
    parser.add_argument("--composition", required=True, help="composition query sent to /api/search")
    parser.add_argument("--expected-user-id", required=True)
    parser.add_argument("--timeout-seconds", type=float, required=True)
    parser.add_argument("--health-timeout-seconds", type=float, required=True)
    return parser.parse_args()


def fetch_json(url: str, timeout: float, payload: Optional[dict] = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return response.status, response.headers.get("Content-Type"), json.loads(body)


def fetch_bytes(url: str, timeout: float):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def main() -> None:
    args = parse_args()
    backend = args.backend.rstrip("/")
    gateway = args.gateway.rstrip("/")
    output: dict = {
        "probe_policy": "All values in this record were observed from live HTTP responses by scripts/probe_kozo_dev.py.",
        "request": {
            "backend": backend,
            "gateway": gateway,
            "composition": args.composition,
            "expected_user_id": args.expected_user_id,
            "timeout_seconds": args.timeout_seconds,
            "health_timeout_seconds": args.health_timeout_seconds,
        },
    }

    status, content_type, backend_health = fetch_json(f"{backend}/health", args.timeout_seconds)
    gateway_status, gateway_type, gateway_health = fetch_json(f"{gateway}/health", args.timeout_seconds)
    output["health"] = {
        "backend_http_status": status,
        "backend_content_type": content_type,
        "backend_body": backend_health,
        "gateway_http_status": gateway_status,
        "gateway_content_type": gateway_type,
        "gateway_body": gateway_health,
        "bodies_equal": backend_health == gateway_health,
    }

    _, _, backend_users = fetch_json(f"{backend}/api/activity/users", args.timeout_seconds)
    _, _, gateway_users = fetch_json(f"{gateway}/api/activity/users", args.timeout_seconds)
    output["activity_users"] = {
        "backend_count": len(backend_users),
        "gateway_count": len(gateway_users),
        "responses_equal": backend_users == gateway_users,
        "expected_backend_matches": [user for user in backend_users if user.get("id") == args.expected_user_id],
        "expected_gateway_matches": [user for user in gateway_users if user.get("id") == args.expected_user_id],
    }

    registry_status, registry_type, registry = fetch_json(
        f"{gateway}/launcher/registry.json", args.timeout_seconds
    )
    output["launcher_registry"] = {
        "http_status": registry_status,
        "content_type": registry_type,
        "entry_count": len(registry),
        "health_urls": [entry.get("health") for entry in registry],
    }
    registry_health = []
    for entry in registry:
        health_path = entry.get("health")
        record = {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "health_path": health_path,
        }
        try:
            health_status, health_type, health_body = fetch_json(
                f"{gateway}{health_path}", args.health_timeout_seconds
            )
            record.update(
                {
                    "reachable": True,
                    "http_status": health_status,
                    "content_type": health_type,
                    "body": health_body,
                }
            )
            status_fields = {
                key: value for key, value in health_body.items() if "status" in key.lower()
            }
            error_fields = {
                key: value
                for key, value in health_body.items()
                if "error" in key.lower() and value not in (None, "", False, [], {})
            }
            unhealthy_status_fields = {
                key: value
                for key, value in status_fields.items()
                if str(value).lower() not in ("ok", "healthy", "ready", "running", "operational")
            }
            record.update(
                {
                    "status_fields": status_fields,
                    "error_fields": error_fields,
                    "healthy": not unhealthy_status_fields and not error_fields,
                }
            )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as error:
            record.update(
                {
                    "reachable": False,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
        registry_health.append(record)
    output["launcher_registry"]["entry_health"] = registry_health

    search_status, search_type, search = fetch_json(
        f"{gateway}/api/search",
        args.timeout_seconds,
        {"composition": args.composition},
    )
    results = search.get("results", [])
    output["database_search"] = {
        "http_status": search_status,
        "content_type": search_type,
        "reported_total_count": search.get("total_count"),
        "returned_count": len(results),
        "reported_error": search.get("error"),
    }
    if results:
        first = results[0]
        first_summary = {
            key: first.get(key)
            for key in ("formula", "energy", "nsites", "source", "original_id")
        }
        output["database_search"]["first_result"] = first_summary
        cif_url = (
            f"{gateway}/api/structure/cif/"
            f"{urllib.parse.quote(str(first['source']), safe='')}/"
            f"{urllib.parse.quote(str(first['original_id']), safe='')}"
        )
        cif_status, cif_type, cif = fetch_bytes(cif_url, args.timeout_seconds)
        output["structure_fetch"] = {
            "http_status": cif_status,
            "content_type": cif_type,
            "bytes": len(cif),
            "line_count": len(cif.splitlines()),
            "contains_data_block": b"\ndata_" in cif or cif.startswith(b"data_"),
            "contains_atom_site_fields": b"_atom_site" in cif,
        }

    core_checks = {
        "backend_healthy": backend_health.get("status") == "healthy",
        "gateway_healthy": gateway_health.get("status") == "healthy",
        "gateway_matches_backend_health": backend_health == gateway_health,
        "gateway_matches_backend_users": backend_users == gateway_users,
        "expected_user_present": bool(output["activity_users"]["expected_gateway_matches"]),
        "search_returned_results": bool(results),
        "search_reported_no_error": search.get("error") is None,
        "structure_payload_present": bool(output.get("structure_fetch", {}).get("bytes")),
        "structure_contains_atom_site_fields": bool(
            output.get("structure_fetch", {}).get("contains_atom_site_fields")
        ),
    }
    registry_checks = {
        "every_registry_health_reachable": all(item["reachable"] for item in registry_health),
        "every_registry_entry_healthy": all(item.get("healthy", False) for item in registry_health),
    }
    output["core_checks"] = core_checks
    output["registry_checks"] = registry_checks
    output["core_checks_passed"] = all(core_checks.values())
    output["all_checks_passed"] = output["core_checks_passed"] and all(registry_checks.values())
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
