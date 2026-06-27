# Proxy Pool 增强工具集

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-✓-003B57)](https://sqlite.org)

配合 [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) 使用的增强脚本集，提供 GitHub 批量代理导入、代理转发管理、自动清理等功能。

## 🧰 工具一览

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `import_github_proxies.py` | 13 个 GitHub 仓库 35 个 raw list 批量导入 | GitHub Raw URLs | SQLite |
| `proxy_manager.py` | HTTP/SOCKS5 代理转发 + 自动故障切换 | 代理池 | :8080 / :1080 |
| `auto_clean.py` | 自动清理过期/无效代理 | 规则配置 | 删除脏数据 |
| `config.py` | 采集源统一配置 | — | 源开关状态 |
| `main.py` | 进程管理器（fetcher + validator + api） | — | 多进程守护 |
| `db/` | 数据库封装（conn / Proxy / Fetcher） | — | SQLite 操作 |

## 📦 安装

```bash
git clone https://github.com/abclq/proxy-pool-tools.git
cd proxy-pool-tools
```

## 📖 详细用法

### 1. import_github_proxies.py — GitHub 批量导入

从 13 个知名 GitHub 代理仓库拉取 35 条 raw list，去重写入 SQLite。

**采集源（13 个仓库 / 35 条 raw list）：**

| 仓库 | ⭐ | 协议 | 更新频率 |
|------|:--:|------|------|
| TheSpeedX/PROXY-List | 5647 | HTTP/SOCKS4/SOCKS5 | 每日 |
| monosans/proxy-list | 1431 | HTTP/SOCKS4/SOCKS5 | 带地理位置 |
| hookzof/socks5_list | 999 | SOCKS5 | Telegram 代理 |
| roosterkid/openproxylist | 862 | HTTPS/SOCKS4/SOCKS5 | 每小时 |
| jetkai/proxy-list | 645 | HTTP/HTTPS/SOCKS4/SOCKS5 | 自动更新 |
| sunny9577/proxy-scraper | 584 | HTTP | 每 3 小时 |
| ShiftyTR/Proxy-List | 579 | HTTP/HTTPS/SOCKS4/SOCKS5 | 每小时 |
| mmpx12/proxy-list | 432 | HTTP/SOCKS4/SOCKS5 | 免费代理列表 |
| vakhov/fresh-proxy-list | 356 | HTTP/SOCKS5 | 新鲜代理 |
| ALIILAPRO/Proxy | 187 | HTTP/SOCKS4/SOCKS5 | 每小时 |
| themiralay/Proxy-List-World | 166 | HTTP | ICE 代理采集 |
| rdavydov/proxy-list | 113 | HTTP/SOCKS4/SOCKS5 | 每 30 分钟 |
| mertguvencli/http-proxy-list | — | HTTP | HTTP 代理列表 |

**使用：**

```bash
python import_github_proxies.py
```

输出示例：
```
📥 github-TheSpeedX-http ... 284 条 → 新增 47 条
📥 github-roosterkid-https ... 156 条 → 新增 23 条
...
✅ 总计新增: 523 条唯一代理
```

### 2. proxy_manager.py — 代理管理器

从代理池读取高质量代理，提供 HTTP/SOCKS5 转发，自动故障切换。

```bash
python proxy_manager.py
```

| 端口 | 协议 |
|:--:|------|
| 8080 | HTTP 代理 |
| 1080 | SOCKS5 代理 |

```bash
curl -x http://127.0.0.1:8080 https://httpbin.org/ip
curl -x socks5://127.0.0.1:1080 https://httpbin.org/ip
```

### 3. auto_clean.py — 自动清理

按规则清理过期/无效/低质代理。

```bash
python auto_clean.py
```

### 4. main.py — 进程守护

启动 fetcher + validator + api 三个子进程，异常退出自动重启，最长运行 1 小时自动回收。

```bash
python main.py
```

## 🏗 架构

```
import_github_proxies.py (13仓库 35list)
    ↓
┌─────────────────┐     ┌──────────────────────┐
│  proxy_pool DB  │────→│ proxy-pool-dashboard  │
│  (SQLite/Redis) │     │ (评分/面板/转发)       │
└────────┬────────┘     └──────────────────────┘
         │
    ┌────┴────┐
    │ auto_clean │  定期清理
    └───────────┘
```

## 📋 定时运行（Cron）

```bash
# 每小时导入
0 * * * * cd /path/to/proxy-pool-tools && python import_github_proxies.py >> /var/log/proxy.log 2>&1

# 每天凌晨清理
0 3 * * * cd /path/to/proxy-pool-tools && python auto_clean.py >> /var/log/proxy-clean.log 2>&1
```

## 🐳 Docker Compose

```bash
docker-compose up -d
```

> 完整代理池：jhao104/proxy_pool + proxy-pool-dashboard + 本工具集

## 🙏 参考

- [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) — 原版（23.4k⭐）
- [abclq/proxy-pool-dashboard](https://github.com/abclq/proxy-pool-dashboard) — 配套仪表盘
