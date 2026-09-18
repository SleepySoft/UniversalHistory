# HOW · Agent API 与 Web 前端（F10/F11）

> 实现：`universal_history/service/`（`agent_api.py` / `__main__.py` / `web/index.html`）。
> 设计动机见 `../why/04-agent-and-web.md`；本篇登记已实现的最小契约。

## 1. 服务端（service/__main__.py）

```bash
python -m universal_history.service [--host 127.0.0.1] [--port 8000] [file1.his file2.json ...]
```

- 命令行文件按扩展名分流：`.json` 走 `JsonFileAdapter`，其余走 `HisFileAdapter`，全部加载进**一个共享 Workspace**；
- REST/WebSocket 挂在 `/api/*` 与 `/ws`；`service/web/` 存在时以 StaticFiles 挂到 `/`（html=True）；
- PyInstaller 冻结运行时经 `sys._MEIPASS` 解析 web 目录（`packaging/service.spec` 已把 translations 与 web 打进 bundle）。

## 2. REST 契约（service/agent_api.py，`create_app(workspace=None)`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/schema` | LLM 友好的字段/label 约定描述 |
| GET | `/api/sources` | 已加载 source 及事件计数 |
| GET | `/api/events` | 查询；参数 `source`、`focus_label`、`time_from`、`time_to`（JDN µs）；返回 **index 形**（摘要 + 指针，见 `04-models.md` §2） |
| GET | `/api/events/{uuid}` | 单个事件全量字段 |
| GET | `/api/parse_time?text=` | 自然语言时间 → JDNTimestamp µs（复用桌面端解析器） |
| POST | `/api/events` | upsert 事件（body 为事件 JSON） |
| DELETE | `/api/events/{uuid}` | 删除事件 |
| WS | `/ws` | 广播全部 Workspace 信号（event_added/updated/removed、source_loaded/removed），供 Agent 与 Web 前端实时同步 |

- `app.state.workspace` / `app.state.hub` 暴露给测试与嵌入方；`tests/service_tests/` 用 FastAPI TestClient 覆盖。

## 3. Web 前端（service/web/index.html）

- 单文件 canvas 应用，**复刻桌面端时间轴设计**：Thread 布局、平移/缩放、悬停提示、LOD 刻度；
- 历法换算（含 BCE 天文纪年、1582 切换、闰日）由 JS 重实现，已用 Node 与 Python 端 `JDNTimestamp` 逐点对拍一致；
- 数据全部经 §2 的 REST/WS 契约，不直接读文件。

## 4. 边界

- 认证/权限、proposal/review 协同模型仍未实现（`PROJECT_STATUS.md` 未完成项）；
- Web 前端当前为只读浏览 + API 演示级写入路径，完整编辑体验仍以桌面端为准。
