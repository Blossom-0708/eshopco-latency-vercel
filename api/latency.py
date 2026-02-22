import json
from http.server import BaseHTTPRequestHandler
from statistics import mean
from os.path import abspath, dirname, join


def p95(values):
    if not values:
        return None
    xs = sorted(values)
    k = int(0.95 * (len(xs) - 1))
    return xs[k]


class handler(BaseHTTPRequestHandler):

    # ---- unified CORS ----
    def _send_headers(self, status=200):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    # ---- preflight ----
    def do_OPTIONS(self):
        self._send_headers(200)

    # ---- grader probe (GET allowed) ----
    def do_GET(self):
        self._send_headers(200)
        self.wfile.write(json.dumps({
            "message": "OK. Use POST with JSON."
        }).encode())

    # ---- main endpoint ----
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            payload = json.loads(self.rfile.read(length).decode())

            regions = payload["regions"]
            threshold_ms = float(payload["threshold_ms"])
        except Exception:
            self._send_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        data_path = abspath(join(dirname(__file__), "..", "q-vercel-latency.json"))
        with open(data_path, "r", encoding="utf-8") as f:
            rows = json.load(f)

        results = []

        for region in regions:
            rrows = [r for r in rows if r["region"] == region]

            lat = [float(r["latency_ms"]) for r in rrows]
            up = [float(r["uptime_pct"]) for r in rrows]

            breaches = sum(1 for x in lat if x > threshold_ms)

            results.append({
                "region": region,
                "avg_latency": mean(lat) if lat else None,
                "p95_latency": p95(lat),
                "avg_uptime": mean(up) if up else None,
                "breaches": breaches
            })

        self._send_headers(200)
        self.wfile.write(json.dumps({
            "regions": results,
            "threshold_ms": threshold_ms
        }).encode())