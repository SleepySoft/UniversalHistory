# HOW · 数据模型（Event / EventIndex / Workspace）

> 实现：`universal_history/models/event.py`。旧版对照：`history_legacy_spec/how/03-data-model.md`、`how/05-loading-and-storage.md`。

## 1. Event（dataclass）

| 字段 | 类型 | 语义 |
| --- | --- | --- |
| `uuid` | str | 唯一 ID |
| `source` | str | 来源（文件路径/URL），Workspace 按它分组 |
| `since` / `until` | Optional[JDNTimestamp] | 起止时间；None 表示无时间 |
| `focus_label` | str | 聚焦标签（五要素之一） |
| `labels` | Dict[str, List[str]] | 任意 label → tags；规范五要素为 time/location/people/organization/event |

方法与行为：

- `is_point_event()` / `is_period_event()` / `has_time()`：since、until 均非 None 且相等 / 不等 / 均非 None。
- `title()` / `brief()` / `event_text()`：对应 label 首 tag，空则 `""`。
- `time_text()`：`time` label 全部 tag `", "` 拼接（**展示用原文**——写回兼容的关键）。
- `abstract(max_length=50)`：取 title→brief→event 首个非空；strip、换行折叠为空格；超长截断为 `max_length-1` 字符 + `…`（旧版是硬切 `[:50]`）。
- `first_tag(label)` / `all_tags(label)`。
- `to_index()` → EventIndex（abstract 现场计算）。

与旧版差异：Event 是扁平 dataclass；`uuid/since/until` 升格为字段（旧版是拦截式 label）；labels 列表**保序不去重**（旧版 `add_tags` 用 set 去重会打乱顺序——旧版缺陷 #6 修复）。

## 2. EventIndex（dataclass）

- 字段：`uuid`、`source`、`since`、`until`、`abstract: str`。
- 用途：只需摘要的场景——网络传输、大列表、时间轴渲染。**内存投影，无持久化**（旧版 .index 文件管线不迁移）。
- 仅有 `is_point_event()`（缺 `is_period_event`/`has_time`，已知瑕疵）。

## 3. Workspace（QObject，内存唯一数据源）

### 信号

| 信号 | 参数 | 触发时机 |
| --- | --- | --- |
| `event_added` | Event | `add()` 追加后；`upsert()` 未发现同 uuid 时 |
| `event_updated` | Event | `upsert()` 替换已有同 uuid 时 |
| `event_removed` | str(uuid) | `remove()` 命中时；`remove_source()` 逐事件；**`upsert()` 替换时也会先发此信号**（内部调 remove） |
| `source_loaded` | str(source) | `load()` 每个 source 合并完成后 |

批量加载**不逐条发 event_added**（走 `_add_silent`）——UI 应监听 `source_loaded` 整体刷新。

### CRUD 语义

- `sources()` / `events(source=None)`（None 摊平全部）/ `indexes(source=None)`（现场 to_index）。
- `add(event)`：**空 source 抛 ValueError**；**不检查重复 uuid**（已知边界，测试待补）。
- `upsert(event)`：有同 uuid 则替换（跨 source 找第一个删除后追加到 `event.source` 末尾），否则追加；按是否存在旧值发 `event_updated` 或 `event_added`。
- `remove(uuid)`：跨所有 source 找**第一个**同 uuid 弹出（旧版删所有——差异点）；source 空则删键；发 `event_removed`；返回被删事件或 None。
- `remove_source(source)`：整组删除，逐事件发信号；不存在则静默。
- `clear()`：清空后对每个旧 source 发 `source_loaded`——**信号名与语义不符（疑似 bug）**，无 `source_removed` 信号。
- `get_by_uuid(uuid)`：首个匹配或 None。

### select 筛选（镜像旧版 `History.select_records` 语义）

参数全部 keyword-only：`sources`、`focus_label`、`include_labels`+`include_all=True`、`exclude_labels`+`exclude_any=True`、`time_range=(lo, hi)`。

逻辑顺序：source 集合 → focus_label 相等 → include 匹配 → exclude 排除 → 时间区间重叠。

- **时间过滤**：`time_range` 给定时，since/until 任一为 None 的事件直接跳过；否则闭区间重叠 `since <= hi and until >= lo`（与旧版 `period_adapt` 一致）。
- **标签匹配** `_match_labels`：空 dict → True；`match_all=True` 要求每个 key 的 wanted 非空且全部命中（wanted 空列表返回 False——与旧版边界一致）；`match_all=False` 任一命中即 True。
- **应用层固定用法**：UI 过滤走 `include_all=False, exclude_any=True`（旧版同款）。

### load

- `load(adapter_result)`：每个 source 先 `remove_source`（**整体替换语义**，同旧版 `dict.update`）再静默追加，最后发一次 `source_loaded`。
- `load_events(events)`：按 `event.source` 分组后走 `load`。

### 测试锁定（tests/test_workspace_signals.py）

- upsert 新 uuid → 仅 added；已有 uuid → updated；
- remove 发 `event_removed(uuid)`；
- load 同 source 整体替换。
