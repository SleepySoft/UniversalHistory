# HOW 总结二 · 验收清单

> 与 `history_legacy_spec/how/99-migration-checklist.md` 配套使用：彼清单核对「旧版行为是否忠实迁移」，本清单核对「新版自身规格是否满足」。
> 运行基准：`QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v`（61 测试全过，2026-09-18）。

## 1. 时间层

- [ ] `to_gregorian` 往返误差 0 微秒（月末、午夜、闰日、远古）；
- [ ] 天文纪年连续：Year 0 = 1 BC，跨公元无跳变；
- [ ] 旧年份迁移走 `history_year_to_jdn_year()`（-1 → 0）；
- [ ] 自然语言解析行为与旧版逐字一致（容错规则以 legacy `how/02` 为准）；
- [ ] BCE 月日允许与旧镜像规则有细微差异（不作为不符项）；
- [ ] 用户可见时间格式统一带 BC/AD 后缀。

## 2. 刻度与缩放

- [ ] 刻度吸附标准日历单位；推进走日历运算（2 月比 1 月窄）；
- [ ] 密度驱动选层（目标间距 120px）；
- [ ] Ctrl+滚轮锚定缩放：鼠标指向的时间点不动；
- [ ] Deep Time 覆盖到 50 亿年；
- [ ] （排期后）主/副刻度双层 + 淡入淡出（zoom_design.md）。

## 3. 布局与绘制

- [ ] 同一事件滚动中永远在同一列（布局稳定）；
- [ ] 单点事件 120px 卡片参与统一轨道分配，不固定轨 0；
- [ ] 重叠事件分轨、不重叠复用轨、末轨兜底；
- [ ] 文字省略号截断；悬停 Tooltip；远端 chip 退化为 marker（>2 年跨度）；
- [ ] 横/纵切换（Ctrl+T）下「右侧 Thread 视觉仍在右」；
- [ ] 相邻 Thread 调色板异色。

## 4. 数据与兼容（红线）

- [ ] `History/depot/example/example.his` 6 条事件解析一致（时间/标签/source/focus）；
- [ ] `China_CN/`、`World_CN/` 真实数据可加载；
- [ ] 保存-重载往返一致（uuid/focus/time/tags/since/until）；
- [ ] 写回不静默改写用户数据；事件间分隔注释、`focus: end` 兜底、`"""` 包裹规则保持；
- [ ] 过滤语义对齐 legacy `core.py:test_history_filter` 基准（include OR / exclude ANY）。

## 5. 交互与编辑

- [ ] 编辑/删除后时间轴即时刷新（Workspace 信号）；
- [ ] 删除事件有确认框；
- [ ] Time 必填；focus 校验（event 时三字段至少其一）；
- [ ] Lock 字段在 New 时保值；回填还原 focus radio；
- [ ] 右键菜单条目与位置感知（含事件级 Edit/Delete）；
- [ ] 过滤结果显示在 `__filter__` Thread 且复用更新；
- [ ] 启动自动加载示例数据；
- [ ] UI 文本全英文。

## 6. 修复后需回归的旧版缺陷

编辑后刷新、focus=time 无法 Apply、回填 focus、删除确认、保存弹框、横纵切换可用——以上均有新实现；修复「Apply 丢失未暴露字段」后需补回归测试（见 [98-known-issues.md](98-known-issues.md) #26）。
