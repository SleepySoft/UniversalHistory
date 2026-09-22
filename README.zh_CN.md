# UniversalHistory

[English](README.md) | 中文

基于单一外推格里高利历 JDN 时间戳模型的无限历史时间与时间轴查看器的标准实现。

## 功能特性

- **统一时间模型**：微秒精度定点整数 `JDNTimestamp`，天文纪年（0 年 = 公元前 1 年）。
- **旧版 `.his` 兼容**：`HisFileAdapter` 读写 History 格式文件，把自然语言时间表达式转换为 `JDNTimestamp`。
- **时间轴渲染**：基于 PyQt6 的无限缩放/平移时间轴，单点与持续事件自动分配轨道布局；刻度轴 LOD 多层淡入淡出，含时/分/秒层级与史前（仅年份）/远古（BP 格式）显示降级。
- **多 Thread**：在轴左右两侧展示任意数量的 source；通过每个 Thread 的 **share** 按比例分配单侧空间（每侧 share 之和恒为 1）；可从已有 `.his` 文件添加 Thread、新建 source 文件，或先建空 Thread 之后再绑定 source。
- **横纵切换**：`Ctrl+T` 切换时间轴方向，Thread 保持直观的左右排布。
- **事件编辑器**：编辑时间、地点、人物、组织、标签、标题、简介和事件正文，可选择 focus label；所有操作流程都有 dirty flag 未保存提示；超出 Qt 公元 1-9999 范围的日期路由到自绘 BCE 天文纪年日期控件。
- **时间轴中心编辑**：位置感知新建（右键预填点击处轴时间）、保存后视图跳转、单击展开详情面板、非模态侧边编辑器、快速录入（标题 + 时间一步成事件）。
- **持续事件悬停进度**：Tooltip 显示光标所在「Year N of M」。
- **多国语言**：英文源文案全部经 `tr()` 包裹，JSON 翻译目录（`translations/zh_CN.json`）；`--lang` 参数或 `UH_LANGUAGE` 环境变量切换，默认跟随系统语言。
- **JSON 持久化**：`JsonFileAdapter`（schema `universal-history/v1`），`since`/`until` 直接存 JDN 微秒整数。
- **Agent API**：FastAPI REST + WebSocket 后端（`universal_history/service/`），提供 schema/sources/events 查询、自然语言时间解析、事件 upsert/删除、带冲突检测的 source 保存，以及 Workspace 信号实时广播。
- **Web 前端**：单文件 canvas 应用（`service/web/index.html`），提供菜单、富事件编辑器、Thread Manager、横纵方向切换、时间轴右键操作、快速录入和视图布局持久化；JS 历法换算与 Python 端 `JDNTimestamp` 逐点对拍一致。
- **过滤器**：按 source、focus label、包含/排除标签和时间范围查询工作区；结果复用单独的过滤 Thread。

## 安装

```bash
python -m pip install -r requirements.txt
```

或以可编辑包方式安装（Agent API / Web 前端服务端追加 `[service]`）：

```bash
python -m pip install -e .
python -m pip install -e .[service]
```

## 运行

```bash
python -m universal_history
```

安装后也可以：

```bash
universal-history
```

Agent API + Web 前端服务端：

```bash
python -m universal_history.service [--host 127.0.0.1] [--port 8000] [file1.his file2.json ...]
universal-history-server ../History/depot/example/example.his   # 安装后
```

## 打包

PyInstaller spec 位于 `packaging/`：

```bash
pyinstaller packaging/universal_history.spec --distpath dist --workpath build -y  # 桌面端
pyinstaller packaging/service.spec --distpath dist --workpath build -y            # API + Web 服务端
```

## 测试

```bash
python -m unittest discover -s tests -v
```

UI / 交互测试规范（offscreen 平台、事件注入三档、断言模式、常见坑）：见 `docs/testing.md`。

## 项目结构

```
UniversalHistory/
├── pyproject.toml
├── requirements.txt
├── README.md                 # English
├── README.zh_CN.md           # 中文（本文件）
├── packaging/                # PyInstaller spec（桌面端 + 服务端）
├── universal_history/          # 主包
│   ├── __main__.py             # python -m universal_history
│   ├── main_window.py          # PyQt6 应用入口
│   ├── models/                 # Event、EventIndex、Workspace
│   ├── chrono/                 # JDN 时间戳、桥接、刻度步进
│   ├── parsing/                # 移植版 .his 解析器（label、记录、时间文本）
│   ├── adapters/               # .his 与 .json 文件适配器
│   ├── render/                 # 时间轴 geometry/layout/painter/view
│   ├── service/                # Agent API（REST/WS）+ Web 前端
│   │   └── web/index.html      # canvas 时间轴前端
│   ├── translations/           # JSON 翻译目录（如 zh_CN.json）
│   └── ui/                     # 编辑器、侧边编辑面板、快速录入、
│                               # 天文纪年日期控件、过滤器、Thread 管理、
│                               # 添加 Thread、绑定 source 对话框
├── tests/                      # 单元测试
└── docs/                       # 设计文档
    ├── core_design.md          # 时间系统设计
    ├── zoom_design.md          # 刻度/缩放设计（多层 LOD 淡入淡出已实现）
    └── spec/                   # WHY / WHAT / HOW 结构化规格
```

`docs/spec/` 是权威行为规格：操作逻辑继承旧版 History 项目并加以针对性优化，底层（时间、数据、适配器、渲染层）遵循新设计。本文未覆盖的行为细节回退参照 `HistoryMigration/docs/history_legacy_spec/`。

`.his` 解析器已完整移植进 `universal_history/parsing/`——对同级 `History/` 仓库**没有代码依赖**。`History/depot` 目录仍是默认数据仓库（纯数据路径；可向 `HisFileAdapter` 注入其他 depot root）。
