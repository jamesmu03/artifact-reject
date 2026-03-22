#!/usr/bin/env python3
"""Start the artifact-reject demo on http://localhost:8000"""

import http.server
import os
import webbrowser

PORT = 8000
DEMO_DIR = os.path.join(os.path.dirname(__file__), "demo")

os.chdir(DEMO_DIR)
webbrowser.open(f"http://localhost:{PORT}/index.html")

handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(("", PORT), handler)

print(f"Serving demo at http://localhost:{PORT}/index.html")
print("Press Ctrl+C to stop.")

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
