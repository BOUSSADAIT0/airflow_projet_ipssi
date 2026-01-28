import json
import pandas as pd
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DATA_PATH = "/opt/airflow/data/orders.csv"  # inside containers
PORT = 8099

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._send(200, {"status": "ok"})
        if parsed.path == "/orders":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", ["10"])[0])
            df = pd.read_csv(DATA_PATH)
            rows = df.head(limit).to_dict(orient="records")
            return self._send(200, {"count": len(rows), "rows": rows})
        return self._send(404, {"error": "not found"})

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mock API listening on :{PORT}")
    server.serve_forever()
