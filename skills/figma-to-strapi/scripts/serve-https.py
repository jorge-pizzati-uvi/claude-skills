#!/usr/bin/env python3
"""Throwaway local HTTPS static server for browser-driven uploads.

The Strapi admin page cannot read local files, and its CSP blocks plain http://
origins, so the files are served over local HTTPS and fetched by the page.

Usage:
    serve-https.py --root ~/Downloads/<set>-images \
                   --cert ~/path/localhost.pem --key ~/path/localhost-key.pem \
                   [--port 8766]

Generate certs once with `mkcert localhost` if you do not have them.
Open https://localhost:<port>/ in a normal tab once so Chrome trusts the cert.
Read-only: it serves GET/HEAD and answers CORS preflight, nothing else.
"""

import argparse
import http.server
import os
import ssl
import sys


def build_handler(root: str):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=root, **kwargs)

        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET,HEAD,OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            super().end_headers()

        def do_OPTIONS(self):  # noqa: N802 - stdlib naming
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='directory to serve')
    parser.add_argument('--cert', required=True, help='TLS certificate (.pem)')
    parser.add_argument('--key', required=True, help='TLS private key (.pem)')
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()

    root = os.path.abspath(os.path.expanduser(args.root))
    cert = os.path.abspath(os.path.expanduser(args.cert))
    key = os.path.abspath(os.path.expanduser(args.key))

    for path, label in ((root, 'root'), (cert, 'cert'), (key, 'key')):
        if not os.path.exists(path):
            print(f'error: {label} not found: {path}', file=sys.stderr)
            return 1

    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', args.port), build_handler(root)
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f'serving {root} at https://localhost:{args.port}/ (ctrl-c to stop)')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
