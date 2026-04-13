# fake microservices — quick and dirty, same idea as before
import random
import time
import secrets

_event_id = 0


def _jitter():
    return (random.random() - 0.5) * 8


def _push_event(events, **kwargs):
    global _event_id
    _event_id += 1
    events.insert(0, {"id": _event_id, "ts": int(time.time() * 1000), **kwargs})
    del events[80:]


def make_initial_services():
    names = [
        "api-gateway",
        "auth-svc",
        "payments",
        "users-db",
        "orders-api",
        "inventory",
        "notifications",
        "search",
    ]
    out = []
    for i, name in enumerate(names):
        out.append(
            {
                "id": name,
                "displayName": name.replace("-", " "),
                "cpu": 15 + i * 2,
                "latencyMs": 40 + i * 5,
                "rps": 120 - i * 7,
                "errorRate": 0.1 + i * 0.02,
                "status": "ok",
                "down_until": 0,
                "latency_mult": 1.0,
                "overload_until": 0,
                "_latency_reset_at": 0,
            }
        )
    return out


TOPOLOGY = [
    {"from": "api-gateway", "to": "auth-svc"},
    {"from": "api-gateway", "to": "payments"},
    {"from": "api-gateway", "to": "orders-api"},
    {"from": "orders-api", "to": "inventory"},
    {"from": "orders-api", "to": "users-db"},
    {"from": "auth-svc", "to": "users-db"},
    {"from": "payments", "to": "users-db"},
    {"from": "search", "to": "users-db"},
    {"from": "notifications", "to": "orders-api"},
]


def _recompute_status(svc, now_ms):
    if svc["down_until"] > now_ms:
        svc["status"] = "bad"
        return
    if svc["latencyMs"] > 220 or svc["errorRate"] > 2.5 or svc["cpu"] > 88:
        svc["status"] = "warn"
        if svc["latencyMs"] > 400 or svc["errorRate"] > 6 or svc["cpu"] > 96:
            svc["status"] = "bad"
    else:
        svc["status"] = "ok"


def tick_sim(state):
    now = int(time.time() * 1000)
    events = state["recentEvents"]

    if now >= state.get("overload_clear_at", 0):
        state["globalTrafficMult"] = 1.0

    if now >= state.get("cascade_clear_at", 0):
        state["cascadeMode"] = False
        db = next((x for x in state["services"] if x["id"] == "users-db"), None)
        if db:
            db["latency_mult"] = 1.0

    for s in state["services"]:
        if now >= s.get("_latency_reset_at", 0) and s.get("_latency_reset_at", 0) > 0:
            s["latency_mult"] = 1.0
            s["_latency_reset_at"] = 0

    g_mult = state.get("globalTrafficMult") or 1.0

    for s in state["services"]:
        if s["down_until"] > now:
            s["cpu"] = 0
            s["rps"] = 0
            s["latencyMs"] = 999
            s["errorRate"] = 100
            _recompute_status(s, now)
            continue

        mult = (
            s["latency_mult"]
            * (1.6 if s["overload_until"] > now else 1.0)
            * g_mult
        )

        s["cpu"] = min(
            100,
            max(5, s["cpu"] + _jitter() + (mult - 1) * 25 + (12 if s["overload_until"] > now else 0)),
        )
        s["latencyMs"] = max(
            8,
            s["latencyMs"] + _jitter() * 3 + (mult - 1) * 40 + (30 if s["cpu"] > 75 else 0),
        )
        s["rps"] = max(0, s["rps"] + _jitter() * 4 * g_mult)
        s["errorRate"] = max(
            0, s["errorRate"] + _jitter() * 0.05 + (0.4 if s["cpu"] > 85 else 0)
        )

        db = next((x for x in state["services"] if x["id"] == "users-db"), None)
        if db and db["status"] != "ok" and s["id"] in (
            "auth-svc",
            "payments",
            "orders-api",
            "search",
        ):
            s["latencyMs"] += 25 if db["status"] == "bad" else 8
            s["errorRate"] += 0.35 if db["status"] == "bad" else 0.08

        _recompute_status(s, now)

    if state.get("cascadeMode"):
        sick = [x for x in state["services"] if x["status"] != "ok"]
        if len(sick) >= 3:
            for s in state["services"]:
                if s["status"] == "ok" and random.random() < 0.08:
                    s["cpu"] += 10
                    s["latencyMs"] += 40

    return state


def apply_command(state, msg):
    if not msg or not isinstance(msg, dict):
        return
    events = state["recentEvents"]
    now = int(time.time() * 1000)

    if msg.get("cmd") == "reset":
        state["services"] = make_initial_services()
        state["globalTrafficMult"] = 1.0
        state["cascadeMode"] = False
        state["overload_clear_at"] = 0
        state["cascade_clear_at"] = 0
        _push_event(events, level="info", text="sim reset")
        return

    if msg.get("cmd") != "fail":
        return

    kind = msg.get("kind")
    target_id = msg.get("serviceId") or "payments"

    if kind == "crash":
        svc = next((x for x in state["services"] if x["id"] == target_id), None)
        if svc:
            svc["down_until"] = now + 8000
            _push_event(events, level="error", text=f"{svc['id']} crashed (sim)")
    elif kind == "latency_spike":
        svc = next((x for x in state["services"] if x["id"] == target_id), None)
        if svc:
            svc["latency_mult"] = 3.2
            svc["_latency_reset_at"] = now + 9000
            _push_event(events, level="warn", text=f"latency spike on {svc['id']}")
    elif kind == "overload":
        state["globalTrafficMult"] = 1.85
        for s in state["services"]:
            s["overload_until"] = now + 7000
        state["overload_clear_at"] = now + 7000
        _push_event(events, level="warn", text="traffic overload everywhere")
    elif kind == "cascade":
        state["cascadeMode"] = True
        db = next((x for x in state["services"] if x["id"] == "users-db"), None)
        if db:
            db["latency_mult"] = 2.4
            db["overload_until"] = now + 12000
        state["cascade_clear_at"] = now + 12000
        _push_event(events, level="error", text="cascading failure started (db overload)")


def create_sim_state():
    return {
        "services": make_initial_services(),
        "recentEvents": [],
        "globalTrafficMult": 1.0,
        "cascadeMode": False,
        "overload_clear_at": 0,
        "cascade_clear_at": 0,
        "runId": secrets.token_hex(4),
    }


def snapshot_for_wire(state):
    now = int(time.time() * 1000)
    svcs = []
    for s in state["services"]:
        svcs.append(
            {
                "id": s["id"],
                "cpu": round(s["cpu"], 1),
                "latencyMs": round(s["latencyMs"]),
                "rps": round(s["rps"]),
                "errorRate": round(s["errorRate"], 2),
                "status": s["status"],
            }
        )
    return {
        "type": "tick",
        "topology": TOPOLOGY,
        "services": svcs,
        "events": state["recentEvents"][:25],
        "runId": state["runId"],
        "_now": now,
    }
