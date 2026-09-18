# WHAT · 过滤与数据兼容

> HOW 细节：[../how/05-his-adapter.md](../how/05-his-adapter.md)、[../how/12-dialogs.md](../how/12-dialogs.md)。

## 过滤（Filter Events，Ctrl+L）

条件（全部可选，为空即不限）：

- **Source**：限定数据来源文件；
- **Focus Label**：`time/location/people/organization/event` 任选（可编辑下拉）；
- **Include / Exclude Labels**：`label: tag1, tag2; label2: tag3` 语法（如 `tags: tag5; author: Sleepy`）——命中任意一条 include 即入选，命中任意一条 exclude 即排除（沿用旧版 `include_all=False, exclude_any=True` 语义）；
- **Time From / To**：时间范围（自然语言可解析）；只填一端时按该时间点过滤。

结果去向：匹配事件显示在专用的 **`__filter__` Thread**（左侧、淡蓝配色）；再次过滤**复用**同一 Thread 更新内容。`__filter__` 是内存结果，不对应可写文件。

相对旧版：旧版过滤器只能编辑/存盘/生成断链的 index 文件，无法应用到时间轴；新版实现了全链路（条件 → 筛选 → 上轴显示）。

## 数据兼容（.his 读写）

- **读**：加载旧版 History 的全部 .his 数据——自然语言时间、focus 结构（`[START]: event` … `event: end`）、`"""` 多行文本、注释、中文文件名均兼容；`depot/example/example.his` 6 条记录、`China_CN/`、`World_CN/` 真实数据有测试锁定。
- **写**：编辑/删除的结果写回原 source 文件；写回保持格式兼容（label 排序、focus 压轴、空 focus 补 `end`、多行文本 `"""` 包裹），事件间加分隔注释对齐手工风格；保存-重载往返一致性有回归测试。
- **路径**：depot 根仍为同级 `History/depot/`（兼容旧数据布局）；打开文件对话框从 depot 根开始。
- **农历/干支**：桥接层支持公历↔农历互转（干支年、生肖、中文月日）；当前未在 UI 暴露，供刻度/提示/Agent 等后续功能使用。

## 兼容红线

- 修改解析或写出逻辑时，先用 `History/depot/example/example.his` 验证向后兼容（AGENTS.md 约定）；
- 不静默改写用户数据；
- 自然语言解析行为逐字继承旧版——容错度只能增不能减。
