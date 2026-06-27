# Proxy Pool 增强工具集

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-✓-003B57)](https://sqlite.org)

配合 [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) 使用的增强脚本集，提供额外的代理采集、管理、清理功能。

## 🧰 工具一览

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `import_github_proxies.py` | 35 个 GitHub raw lists 批量导入 | GitHub Raw URLs | SQLite |
| `proxy_manager.py` | HTTP/SOCKS5 代理转发 + 自动切换 | 代理池 | :8080 / :1080 |
| `auto_clean.py` | 自动清理过期/无效代理 | 规则配置 | 删除脏数据 |
| `config.py` | 采集源统一配置 | — | 源开关状态 |

## 📦 安装

```bash
git clone https://github.com/abclq/proxy-pool-tools.git
cd proxy-pool-tools
```

## 📖 详细用法

### 1. import_github_proxies.py — GitHub 批量导入

从 35 个知名 GitHub 代理仓库拉取免费代理列表，去重写入 SQLite。

**采集源（35 个 GitHub 仓库）：**

| 仓库 | 协议 | 说明 |
|------|:--:|------|
| TheSpeedX/PROXY-List | HTTP/SOCKS4/SOCKS5 | 5647⭐ 每日更新 |
| jetkai/proxy-list | HTTP/HTTPS/SOCKS4/SOCKS5 | 多协议在线代理 |
| ShiftyTR/Proxy-List | HTTP/HTTPS/SOCKS4/SOCKS5 | 579⭐ 每小时更新 |
| sunny9577/proxy-scraper | HTTP | 584⭐ 每3小时更新 |
| hookzof/socks5_list | SOCKS5 | 999⭐ |
| roosterkid/openproxylist | HTTPS/SOCKS4/SOCKS5 | 862⭐ 每小时更新 |
| mertguvencli/http-proxy-list | HTTP | — |
| themiralay/Proxy-List-World | HTTP | — |
| ALIILAPRO/Proxy | HTTP/SOCKS4/SOCKS5 | — |
| mmpx12/proxy-list | HTTP/SOCKS4/SOCKS5 | — |
| rdavydov/proxy-list | HTTP/SOCKS4/SOCKS5 | — |
| vakhov/fresh-proxy-list | HTTP/SOCKS5 | — |
| monosans/proxy-list | HTTP/SOCKS4/SOCKS5 | — |

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

**配置项：**

修改脚本开头的 `SOURCES` 字典可增减采集源：

```python
SOURCES = {
    "https://raw.githubusercontent.com/xxx/xxx/main/http.txt": "http",
    # 新增源...
}
```

### 2. proxy_manager.py — 代理管理器

从代理池数据库读取高质量代理，提供 HTTP/SOCKS5 转发服务，支持自动故障切换。

**启动：**

```bash
python proxy_manager.py
```

**端口：**

| 端口 | 协议 | 用途 |
|:--:|------|------|
| 8080 | HTTP | HTTP 代理转发 |
| 1080 | SOCKS5 | SOCKS5 代理转发 |

**使用示例：**

```bash
# 通过代理访问
curl -x http://127.0.0.1:8080 https://httpbin.org/ip

# SOCKS5 代理
curl -x socks5://127.0.0.1:1080 https://httpbin.org/ip
```

### 3. auto_clean.py — 自动清理

按规则清理数据库中过期/无效/低质代理，保持代理池健康。

**使用：**

```bash
python auto_clean.py
```

**可选参数：**

可在脚本内调整清理阈值（超时天数、失败次数等）。

## 🏗 与 proxy-pool-dashboard 配合

```
import_github_proxies.py (35源)
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

> 完整代理池系统：**jhao104/proxy_pool**（采集+基础校验）+ **proxy-pool-dashboard**（评分+面板）+ **本工具集**（额外采集+管理）

## 📋 定时运行（Cron）

```bash
# 每小时导入 GitHub 代理
0 * * * * cd /path/to/proxy-pool-tools && python import_github_proxies.py >> /var/log/proxy-import.log 2>&1

# 每天凌晨清理
0 3 * * * cd /path/to/proxy-pool-tools && python auto_clean.py >> /var/log/proxy-clean.log 2>&1
```

## 🙏 参考

- [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) — 原版代理池（23.4k⭐）
- [abclq/proxy-pool-dashboard](https://github.com/abclq/proxy-pool-dashboard) — 配套仪表盘
