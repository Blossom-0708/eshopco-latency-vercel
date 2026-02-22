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
    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_POST(self):
        # Read JSON body
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw)
            regions = payload["regions"]
            threshold_ms = float(payload["threshold_ms"])
        except Exception:
            self.send_response(400)
            self._set_cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Expected JSON body: {\"regions\": [...], \"threshold_ms\": number}"
            }).encode("utf-8"))
            return

        # Load telemetry from project root
        data_path = abspath(join(dirname(__file__), "..", "q-vercel-latency.json"))
        with open(data_path, "r", encoding="utf-8") as f:
            rows = json.load(f)

        results = []
        for region in regions:
            rrows = [r for r in rows if r.get("region") == region]
            lat = [float(r["latency_ms"]) for r in rrows]
            up = [float(r["uptime_pct"]) for r in rrows]
            breaches = sum(1 for x in lat if x > threshold_ms)

            results.append({
                "region": region,
                "avg_latency": mean(lat) if lat else None,
                "p95_latency": p95(lat),
                "avg_uptime": mean(up) if up else None,
                "breaches": breaches,
            })

        resp = {"regions": results, "threshold_ms": threshold_ms}

        self.send_response(200)
        self._set_cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode("utf-8"))
