# HOW · HisFileAdapter（.his 读写）

> 实现：`universal_history/adapters/his_adapter.py`。格式规范：`history_legacy_spec/how/04-his-file-format.md`（**语法细节以彼为准**，本篇只登记新版的读写规则与差异）。

## 1. 解析器来源（P4 解耦后）

- `.his` 解析由 **移植版解析器包 `universal_history/parsing/`** 完成（`HistoryRecord` / `HistoryRecordLoader` / `LabelTagParser` / `history_time`），移植自旧仓库 `core.py`、`Utility/HistoryTime.py`、`Utility/to_arab.py`——**不再 sys.path 注入 sibling `History/`，无代码级依赖**。
- 写出侧用移植包的 `LabelTagParser.tags_to_text(tags, persistence=True)` 做转义/`"""` 包裹（`_label_line`，顶层 import）。
- 移植时修复了旧版解析缺陷 #1/#2/#3/#4/#5/#6/#7/#9（明细见 [98-known-issues.md](98-known-issues.md) §6 #36）；其余行为与旧版逐字一致。
- `History/depot` 仍是数据目录：`HistoryRecordLoader.get_local_depot_root()` 按路径解析 sibling 仓库的 `History/depot`（纯路径，无代码依赖）。
- `requests` 仅在 `from_web` 内惰性 import，不再是加载本地文件的硬依赖。

## 2. 读入转换

- `_RESERVED_LABELS = {"uuid", "since", "until"}`：这三个 label 升格为 Event 字段不进 `labels`；**`time` 不在保留集**——原始时间文本保留在 `labels["time"]`（写回兼容的关键）。
- `_history_record_to_event(record)`：`history_record_time_range()` 做自然语言时间 → JDNTimestamp（调用点）；其余 label 原样复制；`focus_label` 空则默认 `"event"`。
- 加载入口：`load_file(path)` / `load_source(source)`（相对路径按 depot root 解析；**Web URL 也经此通路**，承旧 loader 分流）/ `load_depot(name)` / `load_directory(dir)`。
- **错误处理（P4 已修复）**：移植版 loader 读取失败抛 `OSError`（不再静默吞错），空文件正常返回空列表，两者可区分；UI 加载入口均有弹窗反馈。
- `since:`/`until:` label：移植版补上了旧版缺失的 `decimal_year_to_tick`（旧版缺陷 #1），回读不再断链；这两个 label 仍是 reserved，升格为 Event 字段不进 `labels`，**保持「不支持在普通数据中持久化 since/until label」的现状**。

## 3. 写回规则

- `__init__(depot_root=None)`：默认取旧 loader 的 depot root（`History/depot`）；可注入。
- `save_file(path, events, force=False)`：utf-8 **整文件覆写**；自动建父目录；**事件之间写入分隔注释行 `# ----...----`**（对齐 `example.his` 手工风格；旧版不写分隔符——格式层面的优化，读取不受影响）。**冲突检测（P6）**：加载时记录文件 sha256 指纹，保存前比对，磁盘内容已变且 `force=False` 时抛 `SaveConflictError`；UI（编辑器 `_save_source`、主窗口删除路径）捕获后弹「Overwrite?」确认，确认后以 `force=True` 重试。
- `save_workspace(workspace, source, path)`：把某 source 的全部事件写到指定 path；**path 与 source 的对应关系由调用方保证**（UI 层的既定用法见 [10-main-window.md](10-main-window.md)）。
- `_event_to_his_text(event)` 序列化：
  1. focus 空默认 `"event"`；
  2. label 排序：固定优先序 `time→people→location→organization`（**按语义顺序**，旧版是字母序 location,organization,people,time——差异点）→ 其余 label 字母序（排除尾部集与 focus）→ 尾部 `title→brief→event` → **focus 永远最后**；
  3. 输出 `[START]: {focus}` + 空行 + `uuid: ...`；
  4. 逐个输出非 focus label（tags 为空跳过）；
  5. focus label 内容空/全空白 → 写 `focus: end`（与旧版兜底一致）；
  6. 结尾补换行。
- **仍未实现**：错误码（旧版 `E_*` 常量）、只读/Web source 拒绝逻辑（当前无此类 source 类型，登记为预留）。

## 4. 兼容验证（测试锁定，tests/test_his_adapter.py）

- `example.his` 加载得 6 个事件；首事件 BC3000 点事件、focus=event、title 含 "Hi-Story Example"、`since.year == -2999`（天文纪年）；第三事件 2030 AD；
- `load_depot("example")` = 1 个 source、6 事件；
- Workspace 集成：`select(include_labels={"tags": ["tag5"]})` ≥ 2；`select(focus_label="people")` == 1；
- BC/AD 边界：History 年 -1（1 BC）→ JDN 年 0；AD 1 → 年 1；
- **保存-重载往返一致性**：uuid/focus_label/time/tags/since/until 全部往返一致。
