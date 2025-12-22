import sys
import math
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QTransform, QFontMetrics

# --- 导入核心组件 ---
# 请确保这两个文件在同一目录下，或根据你的包结构修改导入
from JDNTimestamp import JDNTimestamp
from TickStepper import TickStepper, TickLevel


class RealTimeAxis(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- 1. 核心状态 (State) ---
        self.is_vertical = False

        # 初始时间：2000-01-01 12:00:00 (JDN 2000.0)
        self.center_time = JDNTimestamp.from_ymd_hms(2000, 1, 1, 12, 0, 0)

        # 初始缩放：屏幕上 200像素 代表 1年
        # 1年 ≈ 31,536,000,000,000 微秒
        # Scale = px / us
        one_year_us = 365.2425 * 24 * 3600 * 1_000_000
        self.scale = 200.0 / one_year_us

        # --- 2. 交互状态 ---
        self._last_mouse_pos = None

        # --- 3. 样式配置 ---
        self.bg_color = QColor(25, 25, 30)  # 深色背景
        self.axis_color = QColor(100, 100, 100)  # 轴线颜色
        self.tick_color = QColor(180, 180, 180)  # 刻度颜色
        self.text_color = QColor(220, 220, 220)  # 文字颜色
        self.font_ticks = QFont("Segoe UI", 9)
        self.font_debug = QFont("Consolas", 10)

        self.setMouseTracking(True)

    # =========================================================================
    # 坐标系变换 (与之前相同)
    # =========================================================================

    def get_coordinate_transform(self) -> QTransform:
        w, h = self.width(), self.height()
        transform = QTransform()
        transform.translate(w / 2, h / 2)  # 原点移至中心
        if self.is_vertical:
            transform.rotate(90)  # 竖直模式旋转
        return transform

    def map_to_logical(self, screen_pos: QPointF) -> QPointF:
        transform = self.get_coordinate_transform()
        inverted, _ = transform.inverted()
        return inverted.map(screen_pos)

    def get_logical_viewport(self):
        """返回 (length, breadth)"""
        if self.is_vertical:
            return self.height(), self.width()
        else:
            return self.width(), self.height()

    # =========================================================================
    # 绘图逻辑 (Rendering)
    # =========================================================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)

        # 1. 确定当前的 TickLevel (LOD)
        # 理想间距：两个刻度之间约 120 像素
        target_px = 120
        # 计算公式: px = us * scale  =>  us = px / scale
        target_us = target_px / self.scale

        # 从 TickStepper 中寻找最接近 target_us 的层级
        # LEVELS 必须是从小到大排序的
        current_level = TickStepper.LEVELS[-1]  # 默认最大
        for level in TickStepper.LEVELS:
            if level.avg_duration_us >= target_us:
                current_level = level
                break

        # 2. 绘制轴线和刻度
        transform = self.get_coordinate_transform()
        painter.setTransform(transform)
        self.draw_geometry(painter, current_level)

        # 3. 绘制文字 (重置变换，保证文字不歪)
        painter.resetTransform()
        self.draw_labels(painter, transform, current_level)

        # 4. 绘制 Debug 信息 (左上角)
        self.draw_debug_info(painter, current_level)

    def draw_geometry(self, painter: QPainter, level: TickLevel):
        logical_len, _ = self.get_logical_viewport()
        half_len = logical_len / 2

        # A. 主轴线
        painter.setPen(QPen(self.axis_color, 2))
        painter.drawLine(QPointF(-half_len, 0), QPointF(half_len, 0))

        # B. 中心指示器 (红线)
        painter.setPen(QPen(QColor(255, 80, 80), 2))
        painter.drawLine(QPointF(0, -20), QPointF(0, 20))

        # C. 计算视口时间范围
        # logical_x = (tick_time - center_time) * scale
        # tick_time - center_time = logical_x / scale
        start_offset_us = int((-half_len) / self.scale)
        end_offset_us = int((half_len) / self.scale)

        # 利用 JDNTimestamp 的加法 (支持直接加微秒整数，如果之前的实现不支持，需修改 __add__ 或使用 value)
        # 这里假设 JDNTimestamp 构造函数接收 int
        start_jdn = JDNTimestamp(self.center_time.value + start_offset_us)
        end_jdn = JDNTimestamp(self.center_time.value + end_offset_us)

        # D. TickStepper 登场：获取可见刻度
        ticks = self.get_visible_ticks(start_jdn, end_jdn, level)

        painter.setPen(QPen(self.tick_color, 1))
        for jdn_tick in ticks:
            # 计算逻辑坐标 X
            offset_us = jdn_tick - self.center_time  # 返回 int 微秒差
            logical_x = offset_us * self.scale

            # 绘制刻度线
            painter.drawLine(QPointF(logical_x, -6), QPointF(logical_x, 6))

    def draw_labels(self, painter: QPainter, transform: QTransform, level: TickLevel):
        logical_len, _ = self.get_logical_viewport()
        half_len = logical_len / 2

        # 重新计算范围 (为了逻辑清晰，虽然略有重复计算)
        start_offset_us = int((-half_len) / self.scale)
        end_offset_us = int((half_len) / self.scale)
        start_jdn = JDNTimestamp(self.center_time.value + start_offset_us)
        end_jdn = JDNTimestamp(self.center_time.value + end_offset_us)

        ticks = self.get_visible_ticks(start_jdn, end_jdn, level)

        painter.setFont(self.font_ticks)
        painter.setPen(self.text_color)
        fm = QFontMetrics(self.font_ticks)

        for jdn_tick in ticks:
            offset_us = jdn_tick - self.center_time
            logical_x = offset_us * self.scale

            # 生成文字
            text = self.format_tick_label(jdn_tick, level)

            # 映射到屏幕位置 (刻度下方 15px)
            screen_pos = transform.map(QPointF(logical_x, 15))

            text_w = fm.width(text)
            text_h = fm.height()

            # 位置微调
            draw_x = screen_pos.x()
            draw_y = screen_pos.y()

            if self.is_vertical:
                draw_x += 8
                draw_y += text_h / 4
            else:
                draw_x -= text_w / 2
                draw_y += text_h

            painter.drawText(QPointF(draw_x, draw_y), text)

    def draw_debug_info(self, painter: QPainter, level: TickLevel):
        """显示当前的中心时间和层级信息"""
        painter.setFont(self.font_debug)
        painter.setPen(QColor(100, 255, 100))

        y, m, d, h, mn, s, _ = self.center_time.to_gregorian()

        # 格式化中心时间
        era = "AD" if y > 0 else "BC"
        year_str = abs(y) if y != 0 else 1  # 天文年0 = 1 BC
        if y <= 0:
            y_display = -(y - 1)  # 0 -> 1 BC, -1 -> 2 BC
        else:
            y_display = y

        time_str = f"Center: {y_display} {era} - {m:02d}-{d:02d} {h:02d}:{mn:02d}"
        level_str = f"Level: {level.name} ({level.unit})"
        zoom_str = f"Scale: {self.scale:.2e} px/us"

        painter.drawText(10, 20, time_str)
        painter.drawText(10, 40, level_str)
        painter.drawText(10, 60, zoom_str)

    # =========================================================================
    # 辅助逻辑 (Helpers)
    # =========================================================================

    def get_visible_ticks(self, start: JDNTimestamp, end: JDNTimestamp, level: TickLevel):
        """包装 TickStepper 的迭代逻辑"""
        ticks = []

        # 1. 对齐第一个刻度
        curr = TickStepper.snap_to_grid(start, level)

        # 安全断路器 (防止死循环或过密渲染)
        max_ticks = 100
        count = 0

        while curr < end:
            if curr >= start:
                ticks.append(curr)
                count += 1

            curr = TickStepper.get_next_tick(curr, level)

            if count > max_ticks: break
            # 如果下一个刻度甚至小于起点 (Step逻辑错误时)，强制退出
            if curr <= start and count > 0: break

        return ticks

    def format_tick_label(self, tick: JDNTimestamp, level: TickLevel) -> str:
        """根据层级智能格式化日期"""
        y, m, d, h, mn, s, _ = tick.to_gregorian()

        # 处理公元前显示
        era_suffix = ""
        year_val = y
        if y <= 0:
            year_val = -(y - 1)
            era_suffix = " BC"

        if level.unit == 'Year':
            # 如果是世纪或千年，可以加 's
            if level.step_count >= 100:
                return f"{year_val}{era_suffix}"
            return f"{year_val}{era_suffix}"

        elif level.unit == 'Month':
            if m == 1:  # 每年的一月显示年份
                return f"{year_val}{era_suffix}"
            # 简写月份
            months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return months[m]

        elif level.unit == 'Day':
            if d == 1:  # 每月1号显示月份
                return f"{m}/{year_val}"
            return f"{d}"

        return str(tick)

    # =========================================================================
    # 交互逻辑 (Interaction)
    # =========================================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._last_mouse_pos:
            curr_pos = event.pos()

            # 1. 统一坐标系计算像素差
            l_curr = self.map_to_logical(QPointF(curr_pos))
            l_last = self.map_to_logical(QPointF(self._last_mouse_pos))
            delta_px = l_curr.x() - l_last.x()

            # 2. 像素差 -> 微秒差
            # 拖动方向相反：鼠标向右(正)，时间轴应该向左移(看过去)，所以 center_time 减小
            delta_us = int(delta_px / self.scale)

            # 3. 更新中心时间 (JDNTimestamp + int microsecond)
            self.center_time = JDNTimestamp(self.center_time.value - delta_us)

            self._last_mouse_pos = curr_pos
            self.update()

    def mouseReleaseEvent(self, event):
        self._last_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()

        # Ctrl + 滚轮 = 缩放
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            factor = 1.2
            if angle > 0:
                self.scale *= factor
            else:
                self.scale /= factor

            # 限制极值
            # 最小: 1000px 显示 10亿年 -> 1e-13
            # 最大: 100px 显示 1分钟 -> 100 / 60,000,000 = 1.6e-6
            self.scale = max(1e-15, min(self.scale, 1e-3))

        # 普通滚轮 = 移动
        else:
            scroll_px = angle  # 像素量
            delta_us = int(scroll_px / self.scale)
            self.center_time = JDNTimestamp(self.center_time.value - delta_us)

        self.update()

    def toggle_orientation(self):
        self.is_vertical = not self.is_vertical
        self.update()


# --- Demo 启动器 ---
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal History Timeline (JDN + Stepper)")
        self.resize(1000, 600)

        layout = QVBoxLayout(self)
        self.axis = RealTimeAxis()

        btn = QPushButton("切换横/竖视图 (Toggle Orientation)")
        btn.clicked.connect(self.axis.toggle_orientation)

        layout.addWidget(self.axis)
        layout.addWidget(btn)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
