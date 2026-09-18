# WHY 总结 —— 继承 / 优化 / 新增决策总表

> 本表是迁移决策的顶层视图。逐条出处见各分篇与 `history_legacy_spec/`。

## 一、继承旧版（行为不变，底层换代）

| 决策 | 旧版出处 | 新版实现 |
| --- | --- | --- |
| 「真实刻度 vs 历法标签」二分 | `HistoryTime.py:1-6` | `JDNTimestamp` + 实时历法属性 |
| 自然语言时间解析容错管线 | `HistoryTime.py:134-160` | `history_time_adapter.py` 原样复用 |
| 五要素 + focus_label 数据语义 | `core.py:407-418` | `Event.labels` + `focus_label` |
| .his 纯文本格式 | `example.his:21-30` | `HisFileAdapter` 读写兼容 |
| 布局稳定性：长优先、全量重排、末轨兜底 | `viewer_ex.py:344-353` | `layout.py:136-202` |
| 锚定缩放 | `viewer_ex.py:945-976` | `timeline_view.py:497-523` |
| 多 Thread 对照 + 调色板 | `viewer_utility.py:38-41` | `timeline_view.py:23-51` |
| Time 必填 + focus 校验 + Lock 保值 | `editor.py:425-510` | `ui/editor.py:381-420` |
| 刻度密度驱动换档思想 | `viewer_ex.py:632-704` | `TickStepper.LEVELS` + `_visible_ticks` |
| BCE 闰年取绝对值 | `HistoryTime.py:440-449` | `jdn_timestamp.py:227-232` |

## 二、优化旧版（有意改变，理由明确）

| 优化 | 旧版 | 新版 |
| --- | --- | --- |
| 时间模型标准化 | 自定义 TICK 零点、无 0 年、BCE 镜像 | JDN 微秒定点、天文纪年、外推格里高利 |
| 数据变更通知 | 无信号，快照不同步 | Workspace 四信号，编辑即刷新 |
| 横纵切换 | 两套绘制 + 镜像特判（且对话框崩溃不可用） | 统一逻辑坐标 + QTransform，Ctrl+T 可用 |
| 单点事件布局 | 固定轨 0 | 虚拟像素区间统一分配（§8.5） |
| 单点事件呈现 | 箭头五边形、文字无截断 | 圆角 chip + pin 线 + 省略号截断 + Tooltip（§8.6） |
| Thread 宽度 | 侧内均分不可调 | share 可调、换侧、排序（ThreadManager） |
| 缩放模型 | 48 档离散跳档 | 连续 scale ×1.2/÷1.2 |
| 重叠检测 | 只查端点落入（隐含约束） | 区间重叠闭区间判断 |
| 保存交互 | 每次 Apply 弹成功框 | 静默落盘，失败才弹框 |
| 删除确认 | 无确认直接落盘 | 确认框 |
| 编辑器缺陷修复 | focus=time 无法 Apply；回填不还原 focus；Tags 行隐藏却写空 tag | 全部修复 |
| 右键菜单精度 | 只到 Thread 级 | 精确到事件级（Edit event / Delete event） |
| 视图适配 | auto_scale 粗选档 | fit_to_sources + show_events_at_default_scale（密度感知开窗） |
| 刻度上限 | 1000 万年 | 50 亿年（Deep Time 1-2-5 循环） |

## 三、新增（旧版没有）

- 农历/干支桥接（`LunarDateBridge`）；
- Unix 时间戳互转；
- 启动自动加载示例数据；
- FilterDialog 全链路（条件 → Workspace.select → `__filter__` Thread 复用显示）；
- AddThreadDialog / BindSourceDialog（Thread 三来源：现有文件 / 新建文件 / 空 Thread）。

## 四、移除 / 废弃（旧版有，新版不做）

- Auto Detect 占位按钮、Load Depot/Load All Records、Help/About 空壳；
- .index 文件管线（断链）；Label Tag Editor 空 Tab；
- 退出确认框（回摆项，是否恢复待决策，见 [../how/98-known-issues.md](../how/98-known-issues.md)）。

## 五、旧版有而新版尚未移植（回退项，需排期）

- 主/副刻度双层体系与淡入淡出（`zoom_design.md` 核心机制）；
- 悬停十字线与持续事件「第N年/共M年」进度提示；
- 刻度像素精确吸附（`__optimise_pixel`）；
- 方向键平滑滚动（旧版本身就坏损）；
- 时间范围/缩放档位限制 API；
- 单击展开详情、密集事件聚簇（§8.6 预留增强）；
- depot 浏览器（文件重命名等）。

## 六、裁决记录（用户已明确）

1. 时间转换不做双向精确，只保留载入阶段的解析能力（§8.1）；
2. 桌面 local-first，Web 为可选只读/共享视图（§8.2）；
3. Qt6 是必然选择（§8.3）；
4. 术语统一表（Event/Index/Source/Depot/Workspace/Thread/Track/Axis，§8.4）；
5. **Track 是正式概念层级**：Thread > Track > Item，Track 行为属布局规格（[../how/07-layout.md](../how/07-layout.md) §0）；
6. **Index 是简化记录而非独立概念**：仅保留正文之外的摘要 + 指针，为减小传输尺寸而设计，由 Event 派生（[../how/04-models.md](../how/04-models.md) §2）；
7. **不沿用旧版的归属与文件管理混乱**：事件恰好归属一个 source、归属可见、写回原 source、新建默认归属当前 Thread（[../how/14-event-ownership.md](../how/14-event-ownership.md)）；
8. **以时间轴为主界面**：新建/编辑/删除从轴上下文发起，编辑器是轴的从属对话框（[../how/15-timeline-centric-editing.md](../how/15-timeline-centric-editing.md)）。
