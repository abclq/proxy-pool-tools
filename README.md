# Proxy Pool 增强工具集

配合 [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) 使用的增强脚本。

## 工具

| 文件 | 功能 | 来源数 |
|------|------|:--:|
| `import_github_proxies.py` | 从 35 个 GitHub raw lists 批量导入代理 | 35 |
| `proxy_manager.py` | 代理管理器（HTTP/SOCKS5 转发、自动切换） | — |
| `auto_clean.py` | 自动清理过期/无效代理 | — |
| `config.py` | 采集源配置 | — |

## 架构

```
import_github_proxies.py (35源)
    ↓ SQLite
proxy_pool 数据库
    ↑          ↑
proxy_manager.py   auto_clean.py
(转发/切换)        (清理)
```

## 使用

```bash
# GitHub 代理导入
python import_github_proxies.py

# 代理管理器（HTTP:8080 SOCKS5:1080）
python proxy_manager.py

# 自动清理
python auto_clean.py
```

## 参考

- [jhao104/proxy_pool](https://github.com/jhao104/proxy_pool) — 原版代理池
- [abclq/proxy-pool-dashboard](https://github.com/abclq/proxy-pool-dashboard) — 配套 Dashboard
