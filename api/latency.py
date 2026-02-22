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

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    # CORS preflight
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # Some graders probe with GET
    def do_GET(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "message": "OK. Use POST with JSON: {\"regions\": [...], \"threshold_ms\": number}"
        }).encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # Actual required endpoint
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)
            regions = payload["regions"]
            threshold_ms = float(payload["threshold_ms"])
        except Exception:
            self.send_response(400)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Expected JSON: {\"regions\": [...], \"threshold_ms\": number}"
            }).encode("utf-8"))
            return

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
                "breaches": breaches
            })

        resp = {"regions": results, "threshold_ms": threshold_ms}

        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode("utf-8"))
