# HOW · HisFileAdapter（.his 读写）

> 实现：`universal_history/adapters/his_adapter.py`。格式规范：`history_legacy_spec/how/04-his-file-format.md`（**语法细节以彼为准**，本篇只登记新版的读写规则与差异）。

## 1. 对旧解析器的依赖

- `_HISTORY_ROOT = Path(__file__).resolve().parents[3] / "History"`——假定 `History/` 与 `UniversalHistory/` 同级；`sys.path.insert` 后 `from core import HistoryRecord, HistoryRecordLoader`。
- 写出侧复用 `LabelTagParser.tags_to_text(tags, persistence=True)` 做转义/`"""` 包裹（`_label_line`）。
- **不在 UniversalHistory 重写 .his 解析**——格式是自研的，旧解析器已能处理（模块 docstring）。
- 间接依赖 `requests`（旧 core.py 的 import）。脱离 sibling 仓库是已知待办（`PROJECT_STATUS.md` 下一步 1）。

## 2. 读入转换

- `_RESERVED_LABELS = {"uuid", "since", "until"}`：这三个 label 升格为 Event 字段不进 `labels`；**`time` 不在保留集**——原始时间文本保留在 `labels["time"]`（写回兼容的关键）。
- `_history_record_to_event(record)`：`history_record_time_range()` 做自然语言时间 → JDNTimestamp（调用点）；其余 label 原样复制；`focus_label` 空则默认 `"event"`。
- 加载入口：`load_file(path)` / `load_source(source)`（相对路径按 depot root 解析；**Web URL 也经此通路**，承旧 loader 分流）/ `load_depot(name)` / `load_directory(dir)`。
- **错误处理继承旧版**：加载异常被吞，失败与空文件不可区分（旧版缺陷 #7 未修复）。
- 旧版 `since:`/`until:` label 回读断链（`decimal_year_to_tick` 不存在）——新版把它们列为 reserved 直接丢弃，**继承「不支持持久化 since/until label」的现状**。

## 3. 写回规则

- `__init__(depot_root=None)`：默认取旧 loader 的 depot root（`History/depot`）；可注入。
- `save_file(path, events)`：utf-8 **整文件覆写**；自动建父目录；**事件之间写入分隔注释行 `# ----...----`**（对齐 `example.his` 手工风格；旧版不写分隔符——格式层面的优化，读取不受影响）。
- `save_workspace(workspace, source, path)`：把某 source 的全部事件写到指定 path；**path 与 source 的对应关系由调用方保证**（UI 层的既定用法见 [10-main-window.md](10-main-window.md)）。
- `_event_to_his_text(event)` 序列化：
  1. focus 空默认 `"event"`；
  2. label 排序：固定优先序 `time→people→location→organization`（**按语义顺序**，旧版是字母序 location,organization,people,time——差异点）→ 其余 label 字母序（排除尾部集与 focus）→ 尾部 `title→brief→event` → **focus 永远最后**；
  3. 输出 `[START]: {focus}` + 空行 + `uuid: ...`；
  4. 逐个输出非 focus label（tags 为空跳过）；
  5. focus label 内容空/全空白 → 写 `focus: end`（与旧版兜底一致）；
  6. 结尾补换行。
- **未实现**：错误码（旧版 `E_*` 常量）、冲突检测、只读/Web source 拒绝逻辑；保存冲突边界测试待补。

## 4. 兼容验证（测试锁定，tests/test_his_adapter.py）

- `example.his` 加载得 6 个事件；首事件 BC3000 点事件、focus=event、title 含 "Hi-Story Example"、`since.year == -2999`（天文纪年）；第三事件 2030 AD；
- `load_depot("example")` = 1 个 source、6 事件；
- Workspace 集成：`select(include_labels={"tags": ["tag5"]})` ≥ 2；`select(focus_label="people")` == 1；
- BC/AD 边界：History 年 -1（1 BC）→ JDN 年 0；AD 1 → 年 1；
- **保存-重载往返一致性**：uuid/focus_label/time/tags/since/until 全部往返一致。
