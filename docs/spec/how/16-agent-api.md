# HOW · Agent API 与 Web 前端（F10/F11）

> 实现：`universal_history/service/`（`agent_api.py` / `__main__.py` / `web/index.html`）。
> 设计动机见 `../why/04-agent-and-web.md`；本篇登记已实现的最小契约。

## 1. 服务端（service/__main__.py）

```bash
python -m universal_history.service [--host 127.0.0.1] [--port 8000]
                                   [--allow-root PATH] [file1.his file2.json ...]
```

- 命令行文件按扩展名分流：`.json` 走 `JsonFileAdapter`，其余走 `HisFileAdapter`，全部加载进**一个共享 Workspace**；
- REST/WebSocket 挂在 `/api/*` 与 `/ws`；`service/web/` 存在时以 StaticFiles 挂到 `/`（html=True）；
- PyInstaller 冻结运行时经 `sys._MEIPASS` 解析 web 目录（`packaging/service.spec` 已把 translations 与 web 打进 bundle）。

## 2. REST 契约（service/agent_api.py，`create_app(workspace=None)`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/schema` | LLM 友好的字段/label 约定描述 |
| GET | `/api/sources` | 已加载 source 及事件计数 |
| GET | `/api/events` | 查询；参数 `source`、`focus_label`、`include_labels`、`exclude_labels`、`time_from`、`time_to`（JDN µs）；返回 **index 形**（摘要 + 指针，见 `04-models.md` §2） |
| GET | `/api/events/{uuid}` | 单个事件全量字段 |
| GET | `/api/parse_time?text=` | 自然语言时间 → JDNTimestamp µs（复用桌面端解析器） |
| GET | `/api/files` | 列出 `--allow-root` 暴露的 `.his` / `.json` 文件（返回 opaque file id） |
| POST | `/api/files/load` | 按 opaque file id 加载允许文件；不接受客户端路径 |
| POST | `/api/events` | upsert 事件（body 为事件 JSON） |
| DELETE | `/api/events/{uuid}` | 删除事件 |
| POST | `/api/sources/{source:path}/save` | 将 source 写回其加载时的服务端允许文件；`{"force": true}` 可在 409 冲突后覆盖 |
| WS | `/ws` | 广播全部 Workspace 信号（event_added/updated/removed、source_loaded/removed），供 Agent 与 Web 前端实时同步 |

- `app.state.workspace`、`app.state.hub`、`app.state.source_paths` 与 `app.state.file_fingerprints` 暴露给测试与嵌入方；`tests/test_agent_api.py` 和 `tests/test_service_files.py` 用 FastAPI TestClient 覆盖。

## 3. Web 前端（service/web/index.html）

- 单文件 canvas 应用，**对齐桌面端工作台**：菜单栏、Thread 布局、Thread Manager（侧别/share/order/axis offset）、平移/缩放、悬停提示、LOD 刻度、横纵切换；
- 历法换算（含 BCE 天文纪年、1582 切换、闰日）由 JS 重实现，已用 Node 与 Python 端 `JDNTimestamp` 逐点对拍一致；
- 数据全部经 §2 的 REST/WS 契约，不直接读文件；
- `Files…` 面板可浏览/加载服务端允许文件；
- 右键时间轴可新建/编辑/删除事件、快速录入、切换侧别、移除视图 Thread；筛选结果复用 `__filter__` Thread；
- 富事件编辑器包含 Form / Label Tags、focus 校验、dirty 确认和 Ctrl+S；编辑结果先更新 Workspace，再写回 source 对应的服务端允许文件；
- Thread side/share/order/axis offset/orientation/筛选条件保存在浏览器 `localStorage`。

## 4. 边界

- 认证/权限、proposal/review 协同模型仍未实现（`PROJECT_STATUS.md` 未完成项）；
- Web 前端只暴露服务端 `--allow-root` 文件；不接受客户端提供的任意路径。保存冲突需用户确认后以 `force=true` 覆盖。
