"""Read-only local web dashboard for validation run history."""
import argparse
import html
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

def serve(db_path, host, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/': self.send_error(404); return
            try:
                with sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) as db:
                    rows = db.execute('SELECT started_at_utc, input_path, total, valid, rejected, issues FROM runs ORDER BY started_at_utc DESC LIMIT 100').fetchall()
                body = '<h1>Retail Data Quality</h1><p>Latest 100 validation runs · UTC</p><table><tr><th>Time</th><th>Input</th><th>Total</th><th>Valid</th><th>Rejected</th><th>Issue counts</th></tr>'
                for row in rows:
                    body += '<tr>' + ''.join('<td>' + html.escape(str(cell)) + '</td>' for cell in row) + '</tr>'
                body += '</table>'
            except sqlite3.Error as exc:
                body = '<h1>Dashboard unavailable</h1><p>Run a quality check first.</p><pre>' + html.escape(str(exc)) + '</pre>'
            page = ('<!doctype html><html><head><meta charset="utf-8"><title>Retail Data Quality</title><style>body{font:15px system-ui;margin:3rem;background:#f6f8fc;color:#17243b}table{border-collapse:collapse;background:white;width:100%}td,th{padding:12px;border:1px solid #ddd;text-align:left}th{background:#e8eef9}</style></head><body>' + body + '</body></html>').encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(page)
    HTTPServer((host, port), Handler).serve_forever()

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--db', default='output/quality/history.db'); p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=8080)
    a = p.parse_args(); print(f'http://{a.host}:{a.port}', flush=True); serve(a.db, a.host, a.port)
if __name__ == '__main__': main()
