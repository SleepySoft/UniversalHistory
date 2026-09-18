# HOW · 事件归属与文件管理（Source Ownership）

> 本篇是**新设计规范**，落实用户裁决第 3 条：「不沿用旧版缺陷——旧版对 thread 中的记录归属和文件管理很乱，通常编辑了也不知道保存到哪，这点一定要设计改进」。
> 旧版问题清单：`history_legacy_spec/how/13-stale-ui-analysis.md`、`how/11-editor.md`、`how/12-main-window.md`。

## 1. 旧版的问题（明确废弃的行为）

| 旧版行为 | 问题 |
| --- | --- |
| 编辑器可无 source 打开，Apply 时才弹「另存为」问保存到哪 | 「编辑了也不知道保存到哪」的直接来源 |
| File → Load Files 只载内存不显示 | 记录已加载但不可见，归属关系对用户是黑盒 |
| `remove_record(uuid)` 跨所有 source 按 uuid 全删 | 同名 uuid 的记录被误删；操作作用域不可预期 |
| 编辑器内嵌 depot 浏览器（HistoryRecordBrowser + Rename） | 文件管理与记录编辑混杂在一个窗口 |
| Thread 显示索引快照，与 source 的关系隐式 | 界面看不出「这条 Thread 显示的是哪个文件」 |
| `INVALID_SOURCE` 哨兵、New File 建两次记录 | 归属状态机混乱的症候 |

## 2. 设计原则

### O1. 每个事件恰好归属一个 source

`Event.source` 是必填字段；空 source 在 `Workspace.add/_add_silent` 即抛 `ValueError`（已实现，`models/event.py:133-138,270-275`）。不存在「游离事件」。

### O2. 归属永远可见

- Thread 列表（Thread Manager）每项显示绑定 source（已实现，`ui/thread_manager.py:139-155`）；
- 编辑器顶行显示当前目标文件路径（已实现，`ui/editor.py` 顶行 source 标签）；
- 任何保存动作发生前，用户能在界面上看到将写入的文件。

### O3. 编辑已有事件 = 写回它自己的 source

写回目标由**事件自身的 `source` 字段**决定，与编辑器从哪个入口打开无关（已实现：Apply → `save_file(event.source 对应路径)`；删除同理，`main_window.py:237-251`）。

### O4. 新建事件的默认归属 = 当前 Thread 的绑定 source

- Thread 已绑定 source：New event 直接进入该 source（已实现，`main_window.py:132-145`）；
- Thread 未绑定：先弹 **BindSourceDialog**（绑定现有文件 / 新建文件），再进入编辑器——**不存在「先编辑后问保存到哪」的路径**；
- AddThreadDialog 三来源（现有文件 / 新建文件 / 空 Thread）即归属的显式声明；空 Thread 是合法的「待绑定」状态，但其中的记录创建必须先完成绑定。

### O5. 操作按事件定位，不按 uuid 扫表

- uuid 全局唯一是约定，但删除/更新以事件（其 source + uuid）定位；
- 旧版「跨 source 全删同 uuid」语义废弃；当前 `Workspace.remove(uuid)` 只删第一个命中（`models/event.py:149-158`）——后续应进一步收敛为显式 source 作用域或保证 uuid 唯一性的边界测试（PROJECT_STATUS 待办 2）。

### O6. 文件管理从编辑器剥离

- 编辑器不含 depot 浏览、文件重命名（旧版 HistoryRecordBrowser 已移除）；
- 文件打开/新建集中在：File → Open File、AddThreadDialog、BindSourceDialog；
- depot 仅作为默认起始目录的兼容约定，不再是强组织结构（Workspace/Source 分层取代 depot 概念，`migration_analysis.md` §8.4）。

### O7. 保存时机与冲突（当前 + 预留）

- 当前：Apply / Delete 立即整文件覆写落盘，失败弹框；
- 预留：写回前校验文件 mtime，外部改动冲突时提示而非静默覆盖（PROJECT_STATUS 待办「保存冲突」边界）。

## 3. 当前实现对照

| 原则 | 状态 |
| --- | --- |
| O1 必填 source | ✅ 已实现 |
| O2 归属可见 | ✅ Thread Manager 与编辑器顶行 |
| O3 写回原 source | ✅ 已实现 |
| O4 默认归属 + 先绑定 | ✅ BindSourceDialog 流程 |
| O5 按事件定位 | 🔶 部分（remove 只删首个命中；uuid 唯一性测试待补） |
| O6 文件管理剥离 | ✅ 编辑器已不含文件浏览 |
| O7 冲突检测 | ⬜ 预留 |

## 4. 验收锚点

- 用户在不看代码的情况下，能回答「这条事件保存在哪个文件」——界面任何时刻可答；
- 新建事件的所有路径都有明确目标文件，无「保存时才问」分支；
- 删除/更新不波及同 uuid 的其他 source 记录。
