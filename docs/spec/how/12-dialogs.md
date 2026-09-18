# HOW · 对话框（Filter / ThreadManager / AddThread / BindSource）

> 实现：`universal_history/ui/` 下 `filter_dialog.py`、`thread_manager.py`、`add_thread_dialog.py`、`bind_source_dialog.py`。

## 1. FilterDialog（Filter Events，Ctrl+L）

- 信号：`filter_applied(list[EventIndex])`；标题 "Filter Events"，500×300。
- 字段：
  - **Source**（空 = 全部）；
  - **Focus Label**：可编辑下拉，候选 `""/time/location/people/organization/event`；
  - **Include / Exclude Labels**：语法 `label: tag1, tag2; label2: tag3`（占位示例 `tags: tag5; author: Sleepy` / `tags: draft`）；**无冒号的段静默忽略**；
  - **Time From / To**：占位 `e.g. 2000` / `e.g. 2020`。
- **Apply**：时间端解析失败弹 "Parse Error" / `Cannot parse time: <输入>` 并中止；两端空 = 不限；**只填一端时另一端开放**（None 端无界，`Workspace.select` 支持 None 端；#31 已修复）；调 `workspace.select(...)`（include_all=False / exclude_any=True）→ 转 EventIndex → 发射 → accept。
- 结果去向：主窗口 `__filter__` Thread（见 [10-main-window.md](10-main-window.md) §4）。
- **预设存取（P7 已实现）**：Save Preset / Load Preset 读写 `.hisfilter` 文件（utf-8，LabelTag 格式：sources/focus_label/include_tags/exclude_tags/time_from/time_to）；无效文件弹 "Invalid filter preset file"。旧版 Generate Index、Check 按钮未移植（索引管线废弃）。

## 2. ThreadManagerDialog（Thread Manager，Ctrl+M）

- 标题 "Thread Manager"，750×500。
- **Add Thread 组**：Add Left / Add Right → AddThreadDialog → `add_thread`。
- **Axis Offset 组**：滑条 0–100，拖动即写 `coord.axis_offset` 并调公开方法 `view.relayout()` 实时生效（#30 已修复，不再调私有方法）。
- 左右两个 QListWidget：项文本 `{source 或 (custom)}\nshare={share:.0%}`，track_color 作背景；两列表选中互斥。
- 控制列：**Thread Share**（QDoubleSpinBox 0.01–0.99、步进 0.05；#30 已去掉不匹配的 " %" 后缀；仅该侧 >1 条 Thread 时可用）、**Remove**（有确认框，#28）、**Move Up / Move Down**（侧内 ±1，保持选中）、**Switch Side**（跨侧 + 归一化）、Close。

## 3. AddThreadDialog（Add Thread）

- 标题 "Add Thread"，550×180；提示 "New thread will be added on the {side} side."；只读 Source 框（占位 "No source selected"）。
- 三来源按钮：
  1. **Load existing file...** → 载入，source = `events[0].source`（空则路径），失败 "Load Failed"；
  2. **Create new source file...** → 建父目录 + 写空文件，失败 "Create Failed"；
  3. **Empty thread** → source=""、显示 "(empty thread)"。
- **构造即默认 Empty thread**（一键 Add 的取舍；测试锁定）；"Add" 为 default 按钮、初始禁用，选定来源后启用。
- `get_result()` 返回 `(source, events)`；docstring 警告勿覆写 `QDialog.result()`（exec 依赖整数返回码）。

## 4. BindSourceDialog（Bind Source to Thread）

- 标题 "Bind Source to Thread"，450×140；文案 "This thread has no source file yet. Choose one to add records."；
- 仅 Load existing file / Create new source file / Cancel（**无 Empty 选项**）；成功后直接 accept。
- 调用场景：Thread 无 source 时右键 New event 的前置步骤。

## 5. 文本约定

UI 用户可见文本以英文为源语言，全部经 `tr()` 包裹；i18n 由 `universal_history/i18n.py`（JsonTranslator）+ `translations/zh_CN.json` 提供中文翻译，语言解析顺序：显式参数 > `UH_LANGUAGE` 环境变量 > 系统 locale（#29 起接入，P11 补齐全部新文案）。
