# HOW 总览 —— 分层架构与数据流

> 本文件是 how/ 的「总」入口。层规则以根仓库 `AGENTS.md`「项目分层」为准；各层细节见分篇。

## 分层架构

```
universal_history/
├── chrono/    时间底座：JDNTimestamp、TickStepper、datetime/农历/旧 TICK 桥接
├── models/    数据：Event、EventIndex、Workspace（QObject + 信号）
├── parsing/   格式解析：.his 解析器移植版（token_parser / label_tag /
│              history_record / history_time / cn_num / text_utils）
├── adapters/  格式：HisFileAdapter（外部格式唯一入口；基于 parsing 包）
├── render/    渲染：geometry（逻辑坐标）、layout（轨道布局）、painter（绘制）、
│              timeline_view（TimelineView 控件，组装三者 + 交互）
├── ui/        对话框：editor、filter_dialog、thread_manager、add_thread_dialog、
│              bind_source_dialog、quick_entry、astro_date_picker、editor_dock
├── service/   Agent API + Web 前端：agent_api（REST/WS）、__main__（uvicorn 入口）、
│              web/（canvas 单文件前端）——详见 how/16-agent-api.md
├── main_window.py  组装：Workspace + Adapter + TimelineView + 菜单/右键
└── __main__.py     入口：python -m universal_history
```

## 层间依赖规则

- chrono 不依赖任何上层（仅 `time_utils.py` 例外地依赖 PyQt6 供 UI 使用）；
- models 依赖 chrono；QObject 仅用于信号，不依赖 QWidget；
- parsing 只依赖标准库（`requests` 仅在 from_web 惰性 import），不依赖 chrono/models；
- adapters 依赖 models、chrono 与 parsing 包；
- render 依赖 chrono、models；**不读写业务数据**（事件以 EventIndex 快照进入）；
- service 依赖 models、adapters 与 parsing 包（时间解析）；**不依赖 PyQt6**，可独立部署；
- ui/main_window 组装各层，连接信号。

## 全局数据流

```
.his 文件 ──HisFileAdapter──▶ Event（自然语言时间经 parsing 包 → JDNTimestamp）
                                   │
                              Workspace（内存唯一数据源）
                                   │  pyqtSignal：event_added / event_updated /
                                   │              event_removed / source_loaded
                                   ▼
                     TimelineView.refresh_source → EventIndex 快照
                                   │
                     geometry（时间↔逻辑 X）→ layout（Track 分配）→ painter（绘制）
```

写回路径：编辑器/删除操作 → `workspace.upsert/remove` → 信号刷新 UI；同时 `HisFileAdapter.save_file(source 对应路径, workspace.events(source))` 整文件覆写落盘。

## 外部依赖

- PyQt6（>=6.0,<7.0；实测 6.11 在某些 Windows 环境 Qt6Core.dll 加载失败，6.8.1 可用）；
- `lunar_python`（农历桥接）；
- `fastapi` + `uvicorn`（可选，`pip install -e .[service]`；Agent API 服务端，`service/` 层）；
- `requests`（可选，仅 `parsing` 包加载 Web source 时惰性 import）；
- ~~同级 `History/` 仓库代码~~：P4 起解析器已移植进 `universal_history/parsing/`，无代码级依赖；`History/depot` 仍按路径作为默认数据目录（可注入其他 depot root）。

## 运行与测试

```bash
python -m universal_history                       # 启动（自动加载 History/depot/example/example.his）
python -m universal_history.service example.his   # Agent API + Web 前端（默认 127.0.0.1:8000）
python -m unittest discover -s tests -v           # 全部测试
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v   # 无显示环境
```

打包（PyInstaller，规格见 `packaging/`）：

```bash
pyinstaller packaging/universal_history.spec --distpath dist --workpath build -y  # 桌面端
pyinstaller packaging/service.spec --distpath dist --workpath build -y            # Agent API 服务端
```
