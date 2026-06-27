#!/usr/bin/env python3
"""
代理池自动清理脚本 - cron 定期执行
建议：每30分钟执行一次
"""
import sqlite3, os, sys
from datetime import datetime, timedelta

DB_PATH = "/home/wang/proxy-pool/data.db"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def clean():
    db = sqlite3.connect(DB_PATH)
    cur = db.cursor()
    
    stats_before = {}
    cur.execute("SELECT COUNT(*) FROM proxies"); stats_before['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validated=1"); stats_before['valid'] = cur.fetchone()[0]
    
    deleted = 0
    
    # 1. 删除5+次失败
    cur.execute("DELETE FROM proxies WHERE validate_failed_cnt >= 5")
    d1 = cur.rowcount
    deleted += d1
    if d1: log(f"删除5+失败: {d1}")
    
    # 2. 删除死HTTPS (validated=0)
    cur.execute("DELETE FROM proxies WHERE protocol='https' AND validated=0")
    d2 = cur.rowcount
    deleted += d2
    if d2: log(f"删除死HTTPS: {d2}")
    
    # 3. 删除慢速验证通过的代理 (>10s) - 降权到观察
    cur.execute("UPDATE proxies SET validated=0, validate_failed_cnt=validate_failed_cnt+1 WHERE validated=1 AND latency > 10000")
    d3 = cur.rowcount
    if d3: log(f"降权慢速代理(>10s): {d3}")
    
    # 4. proxyscrape.com 同IP端口限制
    cur.execute("""
    SELECT ip, COUNT(*) as cnt FROM proxies 
    WHERE fetcher_name='proxyscrape.com'
    GROUP BY ip HAVING cnt > 5 ORDER BY cnt DESC
    """)
    noisy = cur.fetchall()
    for ip_row in noisy:
        ip = ip_row[0]
        cur.execute("""
        SELECT rowid FROM proxies WHERE fetcher_name='proxyscrape.com' AND ip=?
        ORDER BY validated DESC, CASE WHEN latency>0 THEN latency ELSE 99999 END ASC
        LIMIT -1 OFFSET 5
        """, (ip,))
        to_del = [r[0] for r in cur.fetchall()]
        if to_del:
            cur.execute(f"DELETE FROM proxies WHERE rowid IN ({','.join('?'*len(to_del))})", to_del)
            deleted += len(to_del)
    if noisy: log(f"proxyscrape端口去重: {sum(r[1]-5 for r in noisy)} IPs")
    
    db.commit()
    
    # 5. VACUUM
    if deleted > 100:
        cur.execute("VACUUM")
        log("VACUUM done")
    
    stats_after = {}
    cur.execute("SELECT COUNT(*) FROM proxies"); stats_after['total'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validated=1"); stats_after['valid'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM proxies WHERE validated=1 AND latency>0 AND latency<3000")
    stats_after['fast'] = cur.fetchone()[0]
    
    db.close()
    
    log(f"清理完成: 删除{deleted}条")
    log(f"总量: {stats_before['total']}→{stats_after['total']} | "
        f"可用: {stats_before['valid']}→{stats_after['valid']} "
        f"({stats_after['valid']/max(stats_after['total'],1)*100:.1f}%) | "
        f"快速: {stats_after['fast']}")
    
    return deleted

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    clean()
