# HOW · 主窗口

> 实现：`universal_history/main_window.py`、`universal_history/__main__.py`。旧版对照：`history_legacy_spec/how/12-main-window.md`、`how/10-interactions.md`。

## 1. 启动

- `python -m universal_history` → `main_window.main()`；QApplication 只传 `sys.argv[0]`（注释：防 PyCharm 调试参数被 Qt 误解析）。
- 标题 "UniversalHistory"，窗口 1400×900（旧版是屏幕 80% 居中——差异）。
- **启动自动加载** `parents[2]/History/depot/example/example.his`（存在则加载为右侧 Thread 并 `show_events_at_default_scale`；不存在静默跳过）——因此应在完整工作区（History/ 与 UniversalHistory/ 同级）运行。
- 无状态栏；**Help 菜单已实现（P7）**：Help Contents / About UniversalHistory（QMessageBox，i18n 文案，内容含导航、事件操作、时间自然语言说明）；**退出确认已恢复**（2026-09-18 决策，closeEvent 确认框，i18n 文案）。

## 2. 菜单与快捷键

| 菜单 | 文本 | 快捷键 | 行为 |
| --- | --- | --- | --- |
| File | Open File... | Ctrl+O | 文件对话框（depot 根，`*.his`）→ adapter 载入 → workspace 合并 → 右侧新 Thread → 密度感知开窗；失败弹 "Load Failed" |
| File | Exit | Ctrl+Q | 直接 close |
| View | Event Editor | Ctrl+E | 用 `workspace.sources()[0]`（空则 `""`）开编辑器 |
| View | Filter... | Ctrl+L | FilterDialog；`filter_applied` 接过滤去向（见 §4） |
| View | Fit to View | Ctrl+0 | `fit_to_sources()` |
| View | Toggle Orientation | Ctrl+T | 横/纵切换 |
| View | Thread Manager... | Ctrl+M | ThreadManagerDialog |
| Help | Help Contents | — | 使用说明（QMessageBox，P7 新增） |
| Help | About UniversalHistory | — | 关于对话框（P7 新增） |

旧版修复/变化：Toggle Orientation 真正可用（旧版对话框构造即崩溃）；修复旧版 Ctrl+R 双绑冲突；Help/About 由空壳转为真正实现（P7）；移除 Load Depot/Load All Records；双击编辑器与主界面联动刷新（旧版零联动）。

## 3. 右键菜单

命中判定：先 `thread_at_screen`，否则 `side_at_screen` 定左右侧。条目：

1. **Add thread**（总有）→ 光标侧弹 AddThreadDialog；
2. **Load file**（总有）→ Thread 上 = 载入该 Thread；空白 = 等同 Add thread；
3. **New event**（仅 Thread）→ 有 source 直接开编辑器；无 source 先弹 BindSourceDialog 绑定再开；**点击处的轴时间预填进 Time 字段**（T5-1，`format_jdn(time_at_screen(pos))`，预填内容计为未保存修改）；
4. **Set thread share...** → 输入 0.01–0.99（"Share of this side (0.0 ~ 1.0):"）；
5. **Switch side** / **Remove this thread**（移除有确认框，#28）；
6. **Fit to view** / **Toggle orientation**；
7. 命中事件时追加 **Edit event** / **Delete event**（Record 级右键——旧版没有）。

**Delete event**：确认框 "Confirm Delete" / `Delete '{abstract[:40]}'?`；Yes 后 `workspace.remove` + `adapter.save_file(...)` **立即落盘**，失败弹 "Save Failed"；磁盘冲突（`SaveConflictError`）弹「Save Conflict / Overwrite?」确认后强制重试（P6）。

**Add Thread 接受后**：合并事件、`add_thread`；**空 source 新建后立即开编辑器**（注释：无缝录入第一条）。

## 4. 过滤去向

`filter_applied` 到来时：已有 `source=="__filter__"` 的 Thread 则**复用**（`set_thread_events` 更新内容），否则新建**左侧** Thread，固定淡蓝配色（track `(220,230,240)` / item `(200,210,240)`）。`__filter__` 是内存结果，不对应可写文件。测试锁定。
