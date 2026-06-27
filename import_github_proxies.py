#!/usr/bin/env python3
"""批量从 GitHub raw proxy lists 导入代理到 ProxyPoolWithUI 数据库"""

import sqlite3
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

DB_PATH = "/home/wang/proxy-pool/data.db"

# 源 URL -> 协议类型 (从 URL 路径推断)
SOURCES = {
    # TheSpeedX - 5647⭐ 每日更新
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt": "http",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt": "socks5",
    # jetkai/proxy-list
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt": "http",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt": "http",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt": "https",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks4.txt": "socks4",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt": "socks5",
    # ShiftyTR/Proxy-List - 579⭐ 每小时更新
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt": "http",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt": "https",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt": "socks5",
    # sunny9577/proxy-scraper - 584⭐ 每3小时更新
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt": "http",
    # hookzof/socks5_list - 999⭐ Telegram代理
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt": "socks5",
    # roosterkid/openproxylist - 862⭐ 每小时更新
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt": "https",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4.txt": "socks4",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5.txt": "socks5",
    # mertguvencli/http-proxy-list
    "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt": "http",
    # themiralay/Proxy-List-World
    "https://raw.githubusercontent.com/themiralay/Proxy-List-World/master/data.txt": "http",
    # ALIILAPRO/Proxy
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt": "http",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/socks5.txt": "socks5",
    # mmpx12/proxy-list
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt": "http",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt": "socks5",
    # rdavydov/proxy-list
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt": "http",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt": "socks5",
    # vakhov/fresh-proxy-list
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt": "http",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt": "socks5",
    # monosans/proxy-list
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt": "http",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt": "socks4",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt": "socks5",
}


def parse_proxy(line: str, protocol: str, fetcher_name: str):
    """从一行文本解析 IP:PORT"""
    line = line.strip()
    if not line or line.startswith('#') or line.startswith('//'):
        return None

    # 已有 protocol:// 前缀
    if '://' in line:
        try:
            parsed = urlparse(line)
            ip = parsed.hostname
            port = parsed.port
            prot = parsed.scheme
            if ip and port:
                return (prot, ip, port)
        except:
            pass

    # IP:PORT 格式
    m = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})$', line)
    if m:
        return (protocol, m.group(1), int(m.group(2)))

    # host:port 格式 (域名)
    m = re.match(r'^([\w.-]+):(\d{1,5})$', line)
    if m:
        return (protocol, m.group(1), int(m.group(2)))

    return None


def import_proxies():
    import subprocess

    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()

    total_added = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for url, default_protocol in SOURCES.items():
        fetcher_name = urlparse(url).netloc.replace("raw.githubusercontent.com", 
                          url.split("/")[4])  # 取 GitHub 用户名

        # 从 URL 提取 fetcher 名
        parts = url.split("/")
        if "raw.githubusercontent.com" in url:
            fetcher_name = f"github-{parts[3]}-{parts[4]}"
        else:
            fetcher_name = urlparse(url).netloc

        print(f"📥 {fetcher_name} ...", end=" ", flush=True)

        try:
            result = subprocess.run(
                ["curl", "-sL", "--max-time", "15", url],
                capture_output=True, text=True, timeout=20
            )
            lines = result.stdout.split("\n")
            parsed = []
            for line in lines:
                p = parse_proxy(line, default_protocol, fetcher_name)
                if p:
                    parsed.append(p)

            added = 0
            for protocol, ip, port in parsed:
                if port < 1 or port > 65535:
                    continue
                try:
                    cur.execute(
                        """INSERT OR IGNORE INTO proxies 
                        (fetcher_name, protocol, ip, port, validated, to_validate_date, validate_failed_cnt)
                        VALUES (?, ?, ?, ?, 0, ?, 0)""",
                        (fetcher_name, protocol, str(ip), port, now)
                    )
                    if cur.rowcount > 0:
                        added += 1
                except Exception:
                    continue

            db.commit()

            # 更新 fetchers 表
            cur.execute(
                """INSERT OR REPLACE INTO fetchers 
                (name, enable, sum_proxies_cnt, last_proxies_cnt, last_fetch_date)
                VALUES (?, 1, ?, ?, ?)""",
                (fetcher_name, len(parsed), len(parsed), now)
            )
            db.commit()

            print(f"{len(parsed)} 条 → 新增 {added} 条")
            total_added += added

        except Exception as e:
            print(f"❌ {e}")

    db.close()
    print(f"\n✅ 总计新增: {total_added} 条唯一代理")


if __name__ == "__main__":
    import_proxies()
