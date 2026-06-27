#!/usr/bin/env python3
"""
代理管理器 - Clash Verge 风格
API: 0.0.0.0:5001 | SOCKS5: 0.0.0.0:1080 | HTTP: 0.0.0.0:8888
"""

import sqlite3, socket, threading, select, struct, json, time, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

DB_PATH = "/home/wang/proxy-pool/data.db"
current_proxy = {}

def get_proxies(protocol=None, source=None, limit=200, latency_filter="all"):
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    q = "SELECT * FROM proxies WHERE validated=1"
    params = []
    if protocol and protocol != "all":
        q += " AND protocol=?"; params.append(protocol)
    if source and source != "all":
        q += " AND fetcher_name=?"; params.append(source)
    if latency_filter == "fast":
        q += " AND latency > 0 AND latency < 3000"
    elif latency_filter == "normal":
        q += " AND latency > 0 AND latency BETWEEN 3000 AND 8000"
    elif latency_filter == "slow":
        q += " AND latency > 8000"
    q += " ORDER BY latency ASC LIMIT ?"; params.append(limit)
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    db.close()
    return rows

def get_fast_proxies(protocol=None, limit=50):
    """返回最快的已验证代理（延迟<3s）"""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    q = "SELECT * FROM proxies WHERE validated=1 AND latency > 0 AND latency < 3000"
    params = []
    if protocol and protocol != "all":
        q += " AND protocol=?"; params.append(protocol)
    q += " ORDER BY latency ASC LIMIT ?"; params.append(limit)
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    db.close()
    return rows

def get_stats():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM proxies"); total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validated=1"); avail = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validated=0 AND validate_failed_cnt=0"); pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validate_failed_cnt>=3"); dead = cur.fetchone()[0]
    cur.execute("SELECT fetcher_name, COUNT(*) FROM proxies GROUP BY fetcher_name ORDER BY COUNT(*) DESC")
    sources = [{"name": r[0], "count": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT protocol FROM proxies")
    protocols = [r[0] for r in cur.fetchall()]
    db.close()
    return {"total": total, "available": avail, "pending": pending, "dead": dead,
            "sources": sources, "protocols": protocols}

def get_sources():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    cur.execute("SELECT DISTINCT fetcher_name FROM proxies ORDER BY fetcher_name")
    sources = [r[0] for r in cur.fetchall()]
    db.close()
    return sources

def test_latency(protocol, ip, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        start = time.time()
        s.connect((ip, int(port)))
        lat = int((time.time() - start) * 1000)
        s.close()
        return lat
    except:
        return -1

def relay(c1, c2):
    try:
        socks = [c1, c2]
        while True:
            r, _, _ = select.select(socks, [], [], 30)
            if not r: break
            for s in r:
                data = s.recv(8192)
                if not data: return
                if s is c1: c2.sendall(data)
                else: c1.sendall(data)
    except: pass
    finally:
        try: c1.close()
        except: pass
        try: c2.close()
        except: pass

# --- SOCKS5 ---
class SOCKS5Server:
    def __init__(self, host="0.0.0.0", port=1080):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind((host, port))
        self.srv.listen(128)
        self.running = True

    def close(self):
        self.running = False
        try: self.srv.close()
        except: pass

    def run(self):
        while self.running:
            try:
                c, _ = self.srv.accept()
                t = threading.Thread(target=self.handle, args=(c,), daemon=True)
                t.start()
            except: break

    def handle(self, client):
        try:
            client.recv(262); client.send(b"\x05\x00")
            data = client.recv(4)
            if len(data) < 4: return
            cmd, atyp = data[1], data[3]
            if atyp == 1:
                host = socket.inet_ntoa(client.recv(4))
            elif atyp == 3:
                host = client.recv(ord(client.recv(1))).decode()
            else: return
            port = struct.unpack(">H", client.recv(2))[0]
            if cmd == 1:
                self.do_connect(client, host, port)
        except: pass
        finally:
            try: client.close()
            except: pass

    def do_connect(self, client, host, port):
        proxy = current_proxy
        if not proxy.get("ip"):
            try:
                r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                r.settimeout(15); r.connect((host, port))
                client.send(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                relay(client, r)
            except:
                client.send(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            return

        try:
            r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            r.settimeout(15); r.connect((proxy["ip"], proxy["port"]))
            if proxy["protocol"] == "socks5":
                r.send(b"\x05\x01\x00"); r.recv(2)
                r.send(b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + struct.pack(">H", port))
                r.recv(10)
            else:
                req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
                r.send(req.encode()); resp = r.recv(4096)
                if b"200" not in resp:
                    client.send(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00"); return
            client.send(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            relay(client, r)
        except:
            client.send(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")

# --- HTTP Proxy ---
class HTTPHandler(BaseHTTPRequestHandler):
    def do_CONNECT(self):
        host, port = self.path.split(":"); port = int(port)
        proxy = current_proxy
        if not proxy.get("ip"):
            try:
                r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                r.settimeout(15); r.connect((host, port))
                self.send_response(200, "Connection Established"); self.end_headers()
                relay(self.connection, r)
            except: self.send_error(502)
            return
        try:
            r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            r.settimeout(15); r.connect((proxy["ip"], proxy["port"]))
            if proxy["protocol"] in ("socks5", "socks4"):
                r.send(b"\x05\x01\x00"); r.recv(2)
                r.send(b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + struct.pack(">H", port))
                r.recv(10)
            else:
                req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
                r.send(req.encode())
                if b"200" not in r.recv(4096): self.send_error(502); return
            self.send_response(200, "Connection Established"); self.end_headers()
            relay(self.connection, r)
        except: self.send_error(502)

    def log_message(self, *a): pass

# --- Management API ---
class APIHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path
        q = parse_qs(p.query)
        try:
            if path in ("/", "/index.html"):
                fp = "/home/wang/proxy-pool/dashboard.html"
                if os.path.exists(fp):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with open(fp, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            if path == "/api/proxies":
                latency_filter = q.get("latency", ["all"])[0]
                proxies = get_proxies(
                    q.get("protocol", ["all"])[0],
                    q.get("source", ["all"])[0],
                    int(q.get("limit", ["200"])[0]),
                    latency_filter)
                self.wfile.write(json.dumps({"success": True, "proxies": proxies}).encode())

            elif path == "/api/fast":
                # 快速代理：延迟<3s 且已验证
                proxies = get_fast_proxies(
                    q.get("protocol", ["all"])[0],
                    int(q.get("limit", ["50"])[0]))
                self.wfile.write(json.dumps({"success": True, "proxies": proxies}).encode())

            elif path == "/api/stats":
                s = get_stats(); s["current"] = current_proxy
                self.wfile.write(json.dumps({"success": True, **s}).encode())

            elif path == "/api/sources":
                self.wfile.write(json.dumps({"success": True, "sources": get_sources()}).encode())

            elif path == "/api/current":
                self.wfile.write(json.dumps({"success": True, "current": current_proxy}).encode())

            elif path == "/api/switch":
                current_proxy.update({
                    "protocol": q.get("protocol", [""])[0],
                    "ip": q.get("ip", [""])[0],
                    "port": int(q.get("port", [0])[0]),
                    "fetcher": q.get("fetcher", [""])[0],
                    "switched_at": datetime.now().strftime("%H:%M:%S")})
                self.wfile.write(json.dumps({"success": True, "current": current_proxy}).encode())

            elif path == "/api/disconnect":
                current_proxy.clear()
                self.wfile.write(json.dumps({"success": True, "current": {}}).encode())

            elif path == "/api/test_latency":
                lat = test_latency(
                    q.get("protocol", [""])[0],
                    q.get("ip", [""])[0],
                    int(q.get("port", [0])[0]))
                self.wfile.write(json.dumps({"success": True, "latency": lat}).encode())

            else:
                self.wfile.write(json.dumps({"success": False, "error": "Not found"}).encode())

        except Exception as e:
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

    def log_message(self, *a): pass

if __name__ == "__main__":
    threading.Thread(target=lambda: SOCKS5Server().run(), daemon=True).start()
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", 8888), HTTPHandler).serve_forever(), daemon=True).start()
    print(f"📊 http://0.0.0.0:5001 | 🔒 SOCKS5:1080 | 🌐 HTTP:8888 | 📦 {get_stats()['total']} 条")
    HTTPServer(("0.0.0.0", 5001), APIHandler).serve_forever()
