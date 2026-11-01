#!/usr/bin/env python3
"""Validate a Director state record, without network, UI, or filesystem mutation.

This checks declarations, not the truth of UI observations or authorization.
It is NOT a send guard, an exactly-once transport, or an evidence verifier.
Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_BYTES = 1_048_576
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
PHASES = {"draft", "ready", "sending", "sent", "running", "awaiting-user",
          "blocked", "verifying", "complete", "cancelled"}
DELIVERIES = {"not-sent", "sending", "unknown", "confirmed", "failed-no-effect"}


class ValidationError(ValueError):
    """An invalid or inconsistent record."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def obj(value: Any, fields: set[str], path: str) -> dict[str, Any]:
    require(type(value) is dict, f"{path}: expected object")
    require(set(value) == fields,
            f"{path}: wrong fields; missing={sorted(fields-set(value))}; "
            f"unknown={sorted(set(value)-fields)}")
    return value


def text(value: Any, path: str, limit: int = 4096) -> str:
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= limit,
            f"{path}: expected nonempty string of at most {limit} characters")
    return value


def ident(value: Any, path: str) -> str:
    value = text(value, path, 128)
    require(ID.fullmatch(value) is not None, f"{path}: invalid identifier")
    return value


def digest(value: Any, path: str) -> str:
    value = text(value, path, 64)
    require(HASH.fullmatch(value) is not None, f"{path}: expected lowercase SHA-256")
    return value


def timestamp(value: Any, path: str) -> datetime:
    value = text(value, path, 64)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{path}: invalid ISO timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None,
            f"{path}: timezone required")
    return parsed


def validate_state(value: Any) -> None:
    """Raise ValidationError at the first violated structural/semantic rule."""
    s = obj(value, {"schema_version", "task_id", "mode", "phase", "updated_at",
                    "target", "message", "acceptance", "blocker", "next_action"}, "state")
    require(type(s["schema_version"]) is int and s["schema_version"] == 1,
            "schema_version: only integer 1 is supported")
    ident(s["task_id"], "task_id")
    require(type(s["mode"]) is str and s["mode"] in ("execute", "resume"),
            "mode: persistent execution records are only for execute/resume")
    phase = text(s["phase"], "phase")
    require(phase in PHASES, "phase: unknown state")
    updated = timestamp(s["updated_at"], "updated_at")
    text(s["next_action"], "next_action")
    if s["blocker"] is not None:
        text(s["blocker"], "blocker")
    require(phase != "blocked" or s["blocker"] is not None,
            "blocked phase requires blocker")
    require(phase != "complete" or s["blocker"] is None,
            "complete phase must not contain an unresolved blocker")

    target = obj(s["target"], {"app", "mode", "session_anchor", "workspace"}, "target")
    for key in ("app", "mode", "session_anchor"):
        text(target[key], "target." + key)
    if target["workspace"] is not None:
        text(target["workspace"], "target.workspace")

    m = obj(s["message"], {"id", "delivery", "payload_sha256", "readback",
                           "target_anchor", "prepared_at", "send_started_at",
                           "echo", "no_effect_evidence"}, "message")
    ident(m["id"], "message.id")
    delivery = text(m["delivery"], "message.delivery")
    require(delivery in DELIVERIES, "message.delivery: unknown state")
    payload_hash = digest(m["payload_sha256"], "message.payload_sha256")
    require(text(m["target_anchor"], "message.target_anchor") == target["session_anchor"],
            "message target does not match bound session")
    prepared = timestamp(m["prepared_at"], "message.prepared_at")
    require(prepared <= updated, "prepared_at must not be after updated_at")
    if delivery == "not-sent":
        require(m["send_started_at"] is None, "not-sent must have no send_started_at")
        started = None
    else:
        started = timestamp(m["send_started_at"], "message.send_started_at")
        require(prepared <= started <= updated, "send timestamps are out of order")

    # These are declarations of a full composer observation, not proof that an
    # observation occurred. Never open evidence_ref or infer retry permission.
    if phase == "ready" or delivery != "not-sent":
        require(m["readback"] is not None,
                "ready/attempted message requires a full readback record")
    if m["readback"] is not None:
        rb = obj(m["readback"], {"payload_sha256", "target_anchor", "observed_at",
                                "evidence_ref", "complete"}, "message.readback")
        require(rb["complete"] is True, "readback.complete must be true")
        require(digest(rb["payload_sha256"], "readback.payload_sha256") == payload_hash,
                "readback.payload_sha256 mismatch")
        require(text(rb["target_anchor"], "readback.target_anchor") == target["session_anchor"],
                "readback.target_anchor mismatch")
        observed = timestamp(rb["observed_at"], "readback.observed_at")
        require(prepared <= observed <= updated,
                "readback observation must be between prepared_at and updated_at")
        require(started is None or observed <= started,
                "readback observation must not be after send_started_at")
        text(rb["evidence_ref"], "readback.evidence_ref")

    if delivery == "confirmed":
        echo = obj(m["echo"], {"message_id", "payload_sha256", "target_anchor",
                               "observed_at", "evidence_ref"}, "message.echo")
        require(ident(echo["message_id"], "echo.message_id") == m["id"],
                "echo.message_id mismatch")
        require(digest(echo["payload_sha256"], "echo.payload_sha256") == payload_hash,
                "echo.payload_sha256 mismatch")
        require(text(echo["target_anchor"], "echo.target_anchor") == target["session_anchor"],
                "echo.target_anchor mismatch")
        observed = timestamp(echo["observed_at"], "echo.observed_at")
        require(started is not None and started <= observed <= updated,
                "echo timestamp must be between send_started_at and updated_at")
        text(echo["evidence_ref"], "echo.evidence_ref")
    else:
        require(m["echo"] is None, "only confirmed delivery can contain a complete echo")

    if delivery == "failed-no-effect":
        text(m["no_effect_evidence"], "message.no_effect_evidence")
    else:
        require(m["no_effect_evidence"] is None,
                "no_effect_evidence is only for failed-no-effect")
    if delivery == "unknown":
        require(phase in {"blocked", "cancelled"},
                "unknown send cannot advance: phase must be blocked or cancelled")
    if delivery == "sending":
        require(phase in {"sending", "blocked", "cancelled"},
                "sending delivery has incompatible phase")
    if phase == "sending":
        require(delivery == "sending", "sending phase requires sending delivery")
    if phase in {"sent", "running", "awaiting-user", "verifying", "complete"}:
        require(delivery == "confirmed", f"{phase} requires confirmed delivery")
    if phase in {"draft", "ready"}:
        require(delivery in {"not-sent", "failed-no-effect"},
                "draft/ready cannot contain an unresolved or confirmed send")

    criteria = s["acceptance"]
    require(type(criteria) is list and 1 <= len(criteria) <= 100,
            "acceptance: expected 1..100 criteria")
    seen: set[str] = set()
    required_count = 0
    for i, item in enumerate(criteria):
        path = f"acceptance[{i}]"
        a = obj(item, {"id", "required", "criterion", "status", "evidence"}, path)
        key = ident(a["id"], path + ".id")
        require(key not in seen, "duplicate acceptance id")
        seen.add(key)
        require(type(a["required"]) is bool, path + ".required must be boolean")
        required_count += int(a["required"])
        text(a["criterion"], path + ".criterion")
        status = text(a["status"], path + ".status")
        require(status in {"pending", "pass", "fail", "unverifiable"},
                path + ".status is invalid")
        evidence = a["evidence"]
        require(type(evidence) is list and len(evidence) <= 100,
                path + ".evidence must be a list of at most 100 records")
        independent = False
        for j, entry in enumerate(evidence):
            ep = f"{path}.evidence[{j}]"
            e = obj(entry, {"kind", "ref", "summary"}, ep)
            kind = text(e["kind"], ep + ".kind")
            require(kind in {"claude-claim", "artifact-observation", "independent-check"},
                    ep + ".kind is invalid")
            text(e["ref"], ep + ".ref")
            text(e["summary"], ep + ".summary")
            independent |= kind == "independent-check"
        require(status != "pass" or independent,
                path + ": pass requires an independent-check evidence reference")
        if phase == "complete" and a["required"]:
            require(status == "pass", "complete requires all required criteria to pass")
    require(required_count > 0, "at least one acceptance criterion must be required")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def reject_constant(value: str) -> None:
    raise ValidationError("non-finite JSON numbers are not permitted")


def finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite JSON numbers are not permitted")
    return parsed


def read_regular_file(path: Path, limit: int = MAX_BYTES) -> bytes:
    """Read one bounded regular file; refuse symlinks, FIFOs and devices.

    O_NONBLOCK prevents an untrusted FIFO from hanging before fstat. O_NOFOLLOW
    prevents a final-component symlink race where the platform provides it.
    This does not sandbox ancestor directories or verify evidence references.
    """
    require(not path.is_symlink(), "input must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), "input must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(limit + 1)
    finally:
        os.close(descriptor)
    require(len(raw) <= limit, f"input exceeds {limit} bytes")
    return raw


def load_state(path: Path) -> Any:
    # Evidence references and log text remain opaque, untrusted strings.
    raw = read_regular_file(path)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates,
                      parse_constant=reject_constant, parse_float=finite_float)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path)
    args = parser.parse_args(argv)
    try:
        validate_state(load_state(args.state))
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        # Escaping prevents control characters in paths/JSON keys from forging
        # additional diagnostic lines. A valid log is still not authorization.
        print("INVALID: " + json.dumps(str(exc)[:2000], ensure_ascii=True), file=sys.stderr)
        print("Recovery remains unknown; invalid/missing state does not authorize a retry.",
              file=sys.stderr)
        return 1
    print("VALID: record is internally consistent; UI/evidence truth is NOT verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
