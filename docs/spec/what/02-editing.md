# WHAT · 事件编辑

> HOW 细节：[../how/11-editor.md](../how/11-editor.md)。旧版对照：`history_legacy_spec/what/02-editing-and-data.md`。

## 打开方式

- 双击时间轴上的事件；
- Thread 右键 → New event（Thread 未绑定文件时先弹 Bind Source 对话框）；
- View → Event Editor（Ctrl+E）。

## 界面与字段

- 顶行：当前 source 路径 + Open File / New File；
- 次行：记录下拉框（按时间升序，显示 `[时间] 摘要`）+ New / Delete；
- 表单：UUID（只读）、**Time**（自然语言输入 + Calendar 按钮 + Lock）、**Location / People / Organization**（输入 + Lock）、**Focus**（单选，默认 Event）、**Tags**、Title / Brief / Event 正文；
- 底部 Apply / Cancel；快捷键 Ctrl+S = Apply。

## 行为规则

- **时间输入**：完整继承旧版容错解析——「公元前1000年」「前12世纪」「184年2月-184年8月」「至今」、中文数字、各种分隔符均可识别；输入框实时 tooltip 显示解析结果（`Parsed: ...` 或 `Cannot parse time`）；多个时间自动成为时间段。
- **必填校验**：Time 永远必填且须可解析；focus=location/people/organization 时对应字段必填；focus=event 时 Title/Brief/Event 至少一个非空。
- **Calendar**：弹日历选择器回填标准格式；限公元 1-9999 年（超出提示 Out of Range）。
- **Lock**：勾选的行在 New 下一条时保留当前值——连续录入同一地点/人物的系列事件。
- **Apply**：写回该事件所属 .his 文件（静默落盘，失败弹框）；时间轴**即时刷新**。
- **Delete**：弹确认框后删除并落盘。
- **回填**：编辑旧记录时还原 focus 选择（旧版不还原的缺陷已修复）。

## 相对旧版的改进

- 编辑后时间轴即时刷新（旧版从不刷新）；
- 删除有确认（旧版无确认直接落盘）；
- focus=time 可正常保存（旧版 bug）；
- Tags 字段正式暴露（旧版隐藏但仍产生数据副作用）；
- 保存不再弹「Save successful」模态框（旧版每次都弹）。

## 已知沿用缺陷

- 切换记录 / New / Cancel 不提示未保存修改（继承旧版）；
- Apply 后 UI 未暴露的 label（author、自定义标签）丢失（继承旧版缺陷，待修复决策见 [../how/98-known-issues.md](../how/98-known-issues.md)）。
