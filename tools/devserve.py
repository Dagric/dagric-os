#!/usr/bin/env python3
# Local preview server for site/ ONLY. Not shipped, not deployed.
# firebase.json serves clean URLs (trailingSlash:false), so /download must
# resolve to download.html and /guide/de to guide/de/index.html; python's
# stock http.server 404s on both and every measurement would be taken against
# an unstyled error page.
import functools, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")


class H(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = super().translate_path(path)
        if os.path.isdir(p):
            if os.path.exists(os.path.join(p, "index.html")):
                return os.path.join(p, "index.html")
        if not os.path.exists(p) and not p.endswith(".html"):
            if os.path.exists(p + ".html"):
                return p + ".html"
        return p

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    os.chdir(ROOT)
    ThreadingHTTPServer(("127.0.0.1", 8412),
                        functools.partial(H, directory=ROOT)).serve_forever()
