import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QTransform, QFontMetrics


class UniversalTimeAxis(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- 核心状态 ---
        self.is_vertical = False  # 是否竖直绘制
        self.center_time = 0.0  # 屏幕中心对应的时间点 (可以是 JDN，这里用 float 模拟)
        self.px_per_unit = 100.0  # 缩放比例：每单位时间占多少像素

        # --- 交互状态 ---
        self._last_mouse_pos = None  # 拖动用的上一次鼠标位置
        self._mouse_press_time = 0.0  # 鼠标按下时的中心时间

        # --- 样式配置 ---
        self.bg_color = QColor(30, 30, 30)
        self.axis_color = QColor(200, 200, 200)
        self.tick_color = QColor(150, 150, 150)
        self.text_color = QColor(220, 220, 220)
        self.font_ticks = QFont("Arial", 9)

        # 开启鼠标追踪，保证体验流畅
        self.setMouseTracking(True)

    # =========================================================================
    # 1. 统一坐标系核心 (The Unified Coordinate System Method)
    # =========================================================================

    def get_coordinate_transform(self) -> QTransform:
        """
        获取 '逻辑坐标系' 到 '屏幕坐标系' 的变换矩阵。

        逻辑坐标系定义：
          - 原点 (0, 0) 永远对应 Widget 的几何中心。
          - X 轴正方向 永远是时间增加的方向。
          - Y 轴 永远是垂直于时间轴的方向。
        """
        w, h = self.width(), self.height()
        transform = QTransform()

        # 1. 将原点平移到窗口中心
        transform.translate(w / 2, h / 2)

        # 2. 如果是竖直模式，旋转 90 度
        if self.is_vertical:
            transform.rotate(90)

        return transform

    def map_to_logical(self, screen_pos: QPointF) -> QPointF:
        """将屏幕像素点映射回逻辑坐标 (TimeAxis_X, Perpendicular_Y)"""
        transform = self.get_coordinate_transform()
        inverted_transform, _ = transform.inverted()
        return inverted_transform.map(screen_pos)

    def get_logical_viewport(self):
        """获取逻辑视口的宽高 (length=时间轴长度, breadth=非时间轴宽度)"""
        if self.is_vertical:
            return self.height(), self.width()
        else:
            return self.width(), self.height()

    # =========================================================================
    # 2. 绘图逻辑 (Rendering)
    # =========================================================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)

        # 获取变换矩阵
        transform = self.get_coordinate_transform()

        # --- 第一层绘制：几何图形 (线、刻度) ---
        # 应用变换，此时 Painter 认为自己在水平画图，且原点在中心
        painter.setTransform(transform)
        self.draw_geometry(painter)

        # --- 第二层绘制：文字 (Text) ---
        # 既然文字不能歪，我们需要重置变换，直接画在屏幕坐标上
        painter.resetTransform()
        self.draw_labels(painter, transform)

    def draw_geometry(self, painter: QPainter):
        """
        绘制轴线和刻度线。
        注意：此处代码完全不知道 '竖直' 这回事，只当做在 X 轴上画图。
        """
        logical_len, _ = self.get_logical_viewport()
        half_len = logical_len / 2

        # 1. 绘制主轴线 (从左尽头到右尽头)
        pen = QPen(self.axis_color, 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(-half_len, 0), QPointF(half_len, 0))

        # 2. 绘制中心红线指示器
        painter.setPen(QPen(QColor(255, 50, 50), 2))
        painter.drawLine(QPointF(0, -15), QPointF(0, 15))

        # 3. 绘制刻度
        # 计算逻辑视口内的时间范围
        # logical_x = (time - center_time) * px_per_unit
        # 所以 time = logical_x / px_per_unit + center_time

        start_logical_x = -half_len
        end_logical_x = half_len

        start_time = start_logical_x / self.px_per_unit + self.center_time
        end_time = end_logical_x / self.px_per_unit + self.center_time

        # 获取要绘制的刻度列表 (简单算法，实际项目可用之前的 TickStepper)
        ticks = self.calculate_ticks(start_time, end_time)

        painter.setPen(QPen(self.tick_color, 1))
        for time_val, label_str in ticks:
            # 将时间转换为逻辑 X 坐标
            logical_x = (time_val - self.center_time) * self.px_per_unit

            # 绘制刻度线 (向上 5px，向下 5px)
            # 这里的 (logical_x, -5) 会被 Transform 自动处理成水平或竖直
            painter.drawLine(QPointF(logical_x, -5), QPointF(logical_x, 5))

    def draw_labels(self, painter: QPainter, transform: QTransform):
        """
        绘制刻度文字。
        策略：计算逻辑位置 -> Map 到屏幕位置 -> 绘制文字 (保持正向)
        """
        logical_len, _ = self.get_logical_viewport()
        half_len = logical_len / 2

        start_time = (-half_len) / self.px_per_unit + self.center_time
        end_time = (half_len) / self.px_per_unit + self.center_time

        ticks = self.calculate_ticks(start_time, end_time)

        painter.setFont(self.font_ticks)
        painter.setPen(self.text_color)
        fm = QFontMetrics(self.font_ticks)

        for time_val, label_str in ticks:
            logical_x = (time_val - self.center_time) * self.px_per_unit

            # 关键：将逻辑上的刻度点 (logical_x, 10) 映射到屏幕像素坐标
            # Y=10 表示在轴线"下方" 10像素的位置
            screen_pos = transform.map(QPointF(logical_x, 10))

            # 测量文字宽高，为了居中
            text_w = fm.width(label_str)
            text_h = fm.height()

            # 根据方向微调文字位置，使其美观
            draw_x = screen_pos.x()
            draw_y = screen_pos.y()

            if self.is_vertical:
                # 竖直模式：文字在刻度右侧垂直居中
                draw_x += 5
                draw_y += text_h / 4
            else:
                # 水平模式：文字在刻度下方水平居中
                draw_x -= text_w / 2
                draw_y += text_h

            painter.drawText(QPointF(draw_x, draw_y), label_str)

    def calculate_ticks(self, start_t, end_t):
        """简易的刻度生成算法 (1-2-5 步进)"""
        span = end_t - start_t
        if span <= 0: return []

        # 目标：大约每 100 像素一个刻度
        target_step_time = 100.0 / self.px_per_unit

        # 找最近的 1, 2, 5 步长
        magnitude = 10 ** math.floor(math.log10(target_step_time))
        base = target_step_time / magnitude

        if base < 1.5:
            step = 1 * magnitude
        elif base < 3.5:
            step = 2 * magnitude
        else:
            step = 5 * magnitude

        # 对齐起始点
        first_tick = math.ceil(start_t / step) * step

        res = []
        curr = first_tick
        while curr <= end_t:
            res.append((curr, f"{curr:.1f}"))
            curr += step
        return res

    # =========================================================================
    # 3. 交互逻辑 (Interaction)
    # =========================================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_pos = event.pos()
            self._mouse_press_time = self.center_time
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos:
            # 1. 获取当前和上一次的屏幕坐标
            current_pos = event.pos()
            last_pos = self._last_mouse_pos

            # 2. 将屏幕移动向量转换为逻辑移动向量
            # 我们不需要手动判断 x 还是 y，map_to_logical 会帮我们做
            logical_curr = self.map_to_logical(QPointF(current_pos))
            logical_last = self.map_to_logical(QPointF(last_pos))

            # 逻辑坐标系的 X 轴增量 = 屏幕上的有效拖动量
            delta_logical_x = logical_curr.x() - logical_last.x()

            # 3. 将像素增量转换为时间增量
            # 拖动方向与时间轴相反（像抓着纸拖动），所以是减
            time_delta = delta_logical_x / self.px_per_unit
            self.center_time -= time_delta

            self._last_mouse_pos = current_pos
            self.update()

    def mouseReleaseEvent(self, event):
        self._last_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event):
        # 获取滚轮 delta (通常 120 或 -120)
        angle_delta = event.angleDelta().y()

        # --- 情况 A: Ctrl + 滚轮 = 缩放 (Zoom) ---
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            zoom_factor = 1.1
            if angle_delta > 0:
                self.px_per_unit *= zoom_factor
            else:
                self.px_per_unit /= zoom_factor

            # 限制最小最大缩放防止崩溃
            self.px_per_unit = max(0.001, min(self.px_per_unit, 10000.0))

        # --- 情况 B: 普通滚轮 = 滚动 (Pan) ---
        else:
            # 滚动距离：屏幕像素
            scroll_px = angle_delta / 2.0

            # 如果是竖直模式，可能需要反向习惯，或者直接映射
            # 这里逻辑是：向上滚(正) -> 时间向后(未来) -> center_time 增加
            # 这取决于具体的 UX 习惯，这里简单映射
            time_delta = scroll_px / self.px_per_unit
            self.center_time -= time_delta  # 减号意味着滚轮向上看历史，向下看未来

        self.update()

    def toggle_orientation(self):
        """切换横/竖模式"""
        self.is_vertical = not self.is_vertical
        self.update()


# =============================================================================
# 测试窗口
# =============================================================================

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified Coordinate System Time Axis")
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        self.time_axis = UniversalTimeAxis()

        btn = QPushButton("Toggle Orientation (Horizontal / Vertical)")
        btn.clicked.connect(self.time_axis.toggle_orientation)

        layout.addWidget(self.time_axis)
        layout.addWidget(btn)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec_())
