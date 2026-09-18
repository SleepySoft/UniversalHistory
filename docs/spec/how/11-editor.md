# HOW · EventEditor

> 实现：`universal_history/ui/editor.py`（`EventEditor` + `EventEditorDialog` 壳 + `DateTimePickerDialog`）。docstring 自述：「新模型 + PyQt6 全新实现，有意比旧版简单但保留核心工作流」。旧版对照：`history_legacy_spec/how/11-editor.md`。

## 1. 结构

- 信号：`event_saved(Event)` / `event_deleted(uuid)`。
- 顶行：source 标签（默认 "No source"）+ Open File / New File；
- 次行：记录下拉框 + New / Delete；
- 表单移入 QTabWidget（P7）：「Form」tab 为原表单——UUID（只读）；Time 行（radio + 输入 + Calendar + Lock）；Location / People / Organization 行（radio + 输入 + Lock）；Focus 行（radio "Event" 默认勾选 + 静态文本）；**Tags 行（输入 + Lock）**——旧版此行被注释隐藏却仍产生数据副作用，新版正式暴露；Title / Brief / Event；「Label Tags」tab（P7 新增）为两列 QTableWidget 直接编辑全部 labels（含 author 等 UI 未暴露字段），Apply 时表格为权威并与表单字段双向同步；
- 底部 Apply / Cancel；Ctrl+S = Apply（修饰键须精确 Control）。
- **编辑器自建独立 HisFileAdapter**（与主窗口非同一实例，已知瑕疵）。

## 2. 校验（_ui_to_event）

- **Time 必填且可解析**：否则 "Input Check" / "Time field is required and must be parseable."；
- focus=location/people/organization → 对应字段非空（各一条专属提示）；
- focus=event → title/brief/event 至少一个非空；
- **focus=time 无额外校验**——旧版「选 Time 永远无法 Apply」的 bug 已修复；
- 无 source 时 Apply 弹 "Source Required" / "Please select or create a file first."（旧版是保存时才弹另存对话框；新版改为先选文件再 Apply）。

## 3. 字段映射

- 五要素 + tags 按英文逗号 split 并 strip；**time 原文存入 `labels["time"]`**（写回兼容关键）；uuid 沿用当前记录。
- **labels 合并（已修复）**：`_ui_to_event` 合并而非重建 labels——UI 未暴露的 label（author、自定义标签）Apply 后保留（回归测试 `test_apply_preserves_unexposed_labels`）；「Label Tags」tab 提供全量直接编辑。

## 4. 行为

- **Apply**：upsert → 立即整文件落盘（失败 "Save Failed"；磁盘冲突抛 `SaveConflictError` → 弹「Save Conflict / Overwrite?」确认后 `force=True` 重试，P6）→ 发信号（主窗口联动刷新）→ 刷新下拉框并选中。**不再弹成功框**（旧版每次弹）。
- **Delete**：确认框 `Delete event '{abstract(40)}'?`（**新增**，旧版无确认）→ remove → 落盘（同样有冲突确认）→ 新建空白记录。
- **New**：新 uuid、focus=event；**Lock 勾选行的当前值复制进新记录**（继承旧版保值设计）。
- **dirty flag（已修复 #28）**：编辑器跟踪编辑变动；切换记录 / New / Cancel / 关闭时如有未保存修改，提示 保存 / 放弃 / 取消。
- **回填还原 focus radio**（旧版不还原——修复）。
- **下拉框**：按 since 升序；文本 `[format_jdn] abstract(30)`（旧版显示 uuid）；无时间显示 "?" 排最前。
- **Open File / New File**：depot 根对话框；New File 写空文件。
- **Calendar**：需先有可解析时间（否则 "No Time"）；限公元 1-9999 年（否则 "Out of Range"）；DateTimePickerDialog 格式 `yyyy-MM-dd HH:mm:ss`、calendarPopup；initial=None 时为 Qt 默认值（旧版默认当前系统时间——差异）。
- **时间输入反馈**：输入框 tooltip 实时显示 `Parsed: ...` / `Cannot parse time`（旧版是悬浮 QToolTip 弹窗跟随——降级为 tooltip 属性）。

## 5. EventEditorDialog

壳对话框：标题 "Event Editor"，900×700，暴露 `.editor` 属性。旧版的 depot/文件浏览器（HistoryRecordBrowser）与 Rename 功能**未移植**；旧版 "Save and New" 按钮、Auto Detect 占位按钮均已移除；旧版 Label Tag Editor 空 Tab 已由 P7 的「Label Tags」tab 真正实现。
