# Testing Guide · PyQt 界面自动化测试规范

> 本文件是 UniversalHistory 的 UI 测试方法论与模板。写新的 UI 功能测试时先读这里，照抄对应档位的模板。

## 1. 核心原则：把逻辑从 Qt 里剥出来

最好的 UI 测试是**不用测 UI**。项目分层（chrono / models / adapters 不依赖 QWidget）让绝大部分行为可以用纯 Python 单测覆盖——快、稳定、可在任何环境跑。UI 测试只负责「组装和交互」这层皮。

## 2. 无头运行

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v   # Linux/macOS
set QT_QPA_PLATFORM=offscreen && python -m unittest discover -s tests -v   # Windows cmd
$env:QT_QPA_PLATFORM="offscreen"; python -m unittest discover -s tests -v  # PowerShell
```

offscreen 平台让 QWidget 在无显示器/CI 环境里也能创建、布局、渲染。`tests/ui_tests/` 与 `tests/render_tests/` 全部以此运行。

每个测试类只需要一个共享的 `QApplication`：

```python
class TestSomething(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
```

## 3. 事件注入三档（按真实性递增，按稳定性递减）

```python
from PyQt6.QtCore import QPointF, QPoint, QEvent, Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication

# 档1：直接调 handler —— 最快，测逻辑分支
view._update_hover(QPointF(x, y))

# 档2：QApplication.sendEvent —— 走完整事件分发（event() → handler），首选
move = QMouseEvent(QEvent.Type.MouseMove, pos, QPointF(view.mapToGlobal(pos.toPoint())),
                   Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
                   Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(view, move)

# 档3：QTest.mouseMove —— 经 OS 光标注入，最接近真人，只做端到端抽查
from PyQt6.QtTest import QTest
QTest.mouseMove(view, QPoint(x, y))
```

**已踩的坑（#39 排查实录）**：档 3 依赖真实 OS 光标注入，在某些远程/无头会话里会静默失效——事件根本没送达，但测试不报错。若断言依赖先行的直接调用，会误判「链路正常」。**关键路径断言一律用档 2**；档 3 只作补充抽查。

滚轮事件模板（注意 `QApplication.keyboardModifiers()` 是全局状态，测 Ctrl+缩放用修饰键注入或用 `QTest.keyPress` 配合）：

```python
wheel = QWheelEvent(pos, QPointF(view.mapToGlobal(pos.toPoint())),
                    QPoint(0, 0), QPoint(0, 120),   # pixelDelta, angleDelta
                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                    Qt.ScrollPhase.NoScrollPhase, False)
QApplication.sendEvent(view, wheel)
```

键盘事件模板：

```python
from PyQt6.QtGui import QKeyEvent
key = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
QApplication.sendEvent(view, key)
```

## 4. 断言状态，不断言像素

像素断言太脆（字体、DPI、抗锯齿都会变）。断言**可观察状态**：

```python
# 几何：平移后事件条屏幕位置精确偏移
self.assertAlmostEqual(after.left() - before.left(), delta_px, delta=1.0)
# 信号：用列表收集发射
fired = []
view.itemClicked.connect(fired.append)
# 属性/模型：tooltip 文本、center_time、scale、dock 的 isHidden()
```

Qt 静态/全局方法用 mock 截获：

```python
with patch("universal_history.render.timeline_view.QToolTip") as tip:
    view._update_hover(pos)
    tip.showText.assert_called_once()
```

## 5. 视觉验证：截图人工确认（一次性手段，不进 CI）

行为对 ≠ 看起来对。关键视觉改动用 `grab()` 出帧亲眼确认（offscreen 也能渲染）：

```python
view.resize(900, 500); view.show()
app.processEvents()
view.grab().save("frame.png")
```

#38 平移 bug 的最终确认就是平移前后两张截图逐帧对比。截图是**验证手段**，不是回归断言。

## 6. 真实平台冒烟（收尾必做）

offscreen 证明不了真实窗口行为——#39 就是 offscreen 全对、真实平台才暴露的问题。收尾时跑一次真实平台冒烟：

```python
w = MainWindow(); w.show()
QTest.qWaitForWindowExposed(w, 3000)
# ... sendEvent 交互 ...
w.deleteLater()   # 不要 w.close()：退出确认框是模态的，会挂起测试
```

## 7. 常见坑清单（本项目实测）

| 坑 | 对策 |
| --- | --- |
| 模态对话框（退出确认、保存确认）挂起测试 | `deleteLater()` 代替 `close()`；或 mock `QMessageBox.exec`/`question` |
| 窗口未 show 时 `isVisible()` 恒 False | 断言改用 `not isHidden()` |
| QTest 光标注入静默失效 | 关键断言用 `sendEvent`，QTest 只做抽查 |
| `QToolTip.isVisible()` / 弹窗状态异步 | `QTest.qWait(300)` + `app.processEvents()` 后再断言 |
| offscreen 下中文字体渲染为豆腐块 | 截图验证只看几何布局，不看文字 |
| 定时器驱动交互（方向键平滑滚动） | 直接调 `_on_scroll_timer()` 测效果，keyPress/keyRelease 只测按键状态登记 |
| 多参数信号接 `list.append` 只收到第一个参数 | PyQt 会按槽签名截断参数；收集全部参数用 `signal.connect(lambda *a: fired.append(a))` |
| 测试间 QApplication 状态泄漏 | `setUpClass` 共享 instance；每个测试结束 `widget.deleteLater()` |

## 8. 现有测试索引

| 目录 | 覆盖 |
| --- | --- |
| `tests/` 根 | chrono / models / adapters / parsing / service 纯逻辑 |
| `tests/render_tests/` | 几何、布局、刻度 LOD、平移锚点、悬停、交互注入（`test_interactions.py`） |
| `tests/ui_tests/` | 主窗口、编辑器、对话框、i18n、详情面板 |
