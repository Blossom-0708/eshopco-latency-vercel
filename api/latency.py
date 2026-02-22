import json
import os
from statistics import mean

def _p95(values):
    if not values:
        return None
    xs = sorted(values)
    # nearest-rank style index
    k = int(0.95 * (len(xs) - 1))
    return xs[k]

def _cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

def handler(request):
    # CORS preflight
    if request.method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors(), "body": ""}

    if request.method != "POST":
        return {
            "statusCode": 405,
            "headers": {**_cors(), "Content-Type": "application/json"},
            "body": json.dumps({"error": "Use POST"}),
        }

    try:
        payload = request.json
        regions = payload["regions"]
        threshold_ms = float(payload["threshold_ms"])
    except Exception:
        return {
            "statusCode": 400,
            "headers": {**_cors(), "Content-Type": "application/json"},
            "body": json.dumps({"error": "Expected JSON body: {\"regions\": [...], \"threshold_ms\": number}"}),
        }

    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json"))
    with open(data_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    out = []
    for region in regions:
        rrows = [r for r in rows if r.get("region") == region]
        lat = [float(r["latency_ms"]) for r in rrows]
        up = [float(r["uptime_pct"]) for r in rrows]

        breaches = sum(1 for x in lat if x > threshold_ms)

        out.append({
            "region": region,
            "avg_latency": mean(lat) if lat else None,
            "p95_latency": _p95(lat),
            "avg_uptime": mean(up) if up else None,
            "breaches": breaches
        })

    return {
        "statusCode": 200,
        "headers": {**_cors(), "Content-Type": "application/json"},
        "body": json.dumps({"regions": out, "threshold_ms": threshold_ms}),
    }
