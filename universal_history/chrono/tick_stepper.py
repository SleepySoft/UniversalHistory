from dataclasses import dataclass
from typing import List, Optional, Literal
import math

from universal_history.chrono.jdn_timestamp import JDNTimestamp

# 定义刻度类型的枚举/常量
StepUnit = Literal['Day', 'Month', 'Year']


@dataclass
class TickLevel:
    """
    刻度层级定义类
    """
    id: str  # 唯一标识符，如 'year_5', 'month_1'
    name: str  # 显示名称，用于UI调试或默认格式化

    unit: StepUnit  # 基础运算单位
    step_count: int  # 步长数量 (如 5 Years)

    avg_duration_us: int  # 平均微秒数 (用于计算 Zoom 选择权重)

    # 上下文约束 (解决问题4：超出范围不计算)
    # 使用天文纪年法 (0 = 1 BC)
    min_valid_year: float = -float('inf')
    max_valid_year: float = float('inf')

    def is_visible(self, current_year: int) -> bool:
        return self.min_valid_year <= current_year <= self.max_valid_year


class TickStepper:
    """
    刻度计算引擎
    负责 '发现' (Snap) 和 '迭代' (Next) 刻度
    """

    # =========================================================================
    # 1. 精心设计的刻度列表 (The Carefully Crafted Spec)
    # =========================================================================
    LEVELS: List[TickLevel] = []

    @classmethod
    def _register(cls, _id, _name, _unit, _step, _dur, _min_y=None, _max_y=None):
        """内部辅助注册函数"""
        # 默认有效范围
        min_y = _min_y if _min_y is not None else -float('inf')
        max_y = _max_y if _max_y is not None else float('inf')

        cls.LEVELS.append(TickLevel(
            id=_id, name=_name, unit=_unit, step_count=_step,
            avg_duration_us=int(_dur),
            min_valid_year=min_y, max_valid_year=max_y
        ))

    # =========================================================================
    # 2. 核心算法：对齐 (Snap/Floor)
    # =========================================================================

    @staticmethod
    def snap_to_grid(jdn: JDNTimestamp, level: TickLevel) -> JDNTimestamp:
        """
        找到 <= jdn 的最近一个整刻度点。
        例如：当前是 1993年，Step是 5年 -> 返回 1990年1月1日
        """
        # 1. 转换为公历进行计算 (这是处理非线性历法的唯一正确方式)
        y, m, d, h, *_ = jdn.to_gregorian()

        if level.unit == 'Day':
            # 简单天：对齐到午夜 00:00:00
            if level.step_count == 1:
                return JDNTimestamp.from_ymd_hms(y, m, d, 0, 0, 0)
            elif level.step_count == 7:  # 周 (假设对齐到周一)
                # JDN 0 是周一(12:00)。我们需要计算当前周的周一。
                # 这是一个简化的周对齐，实际可能需要根据 weekday 计算
                wd = jdn.weekday  # 1=Mon, 7=Sun
                # 回退到周一
                offset_days = wd - 1
                base_day = jdn - offset_days
                # 重新构造以去除时分秒
                by, bm, bd, *_ = base_day.to_gregorian()
                return JDNTimestamp.from_ymd_hms(by, bm, bd, 0, 0, 0)

        elif level.unit == 'Month':
            # 1月, 2月, 3月...
            if level.step_count == 1:
                return JDNTimestamp.from_ymd_hms(y, m, 1, 0, 0, 0)
            # 季度 (1, 4, 7, 10)
            elif level.step_count == 3:
                # 算法: 映射 m 到最近的 (k*3 + 1)
                # (m-1)//3 得到 0,1,2,3. 乘3加1 得到 1,4,7,10
                snapped_m = ((m - 1) // 3) * 3 + 1
                return JDNTimestamp.from_ymd_hms(y, snapped_m, 1, 0, 0, 0)
            # 半年 (1, 7)
            elif level.step_count == 6:
                snapped_m = 1 if m < 7 else 7
                return JDNTimestamp.from_ymd_hms(y, snapped_m, 1, 0, 0, 0)

        elif level.unit == 'Year':
            # 核心逻辑：年份对齐
            # Python 的 % 运算对于负数表现完美： -4 % 5 = 1, -4 - 1 = -5. (对齐到 -5)
            remainder = y % level.step_count
            snapped_y = y - remainder
            return JDNTimestamp.from_ymd_hms(snapped_y, 1, 1, 0, 0, 0)

        # Fallback
        return jdn

    # =========================================================================
    # 3. 核心算法：迭代 (Next)
    # =========================================================================

    @staticmethod
    def get_next_tick(current: JDNTimestamp, level: TickLevel) -> JDNTimestamp:
        """
        基于当前整刻度，计算下一个刻度。
        """
        y, m, d, *_ = current.to_gregorian()

        if level.unit == 'Day':
            # 直接加天数 (注意：JDNTimestamp + float 是合法的)
            return current + float(level.step_count)

        elif level.unit == 'Month':
            # 逻辑加月
            next_m = m + level.step_count

            # 处理跨年 (递归减 12 直到月份合法)
            # 简单处理通常只加 1, 3, 6
            years_to_add = (next_m - 1) // 12
            final_m = (next_m - 1) % 12 + 1
            final_y = y + years_to_add

            return JDNTimestamp.from_ymd_hms(final_y, final_m, 1, 0, 0, 0)

        elif level.unit == 'Year':
            # 逻辑加年
            return JDNTimestamp.from_ymd_hms(y + level.step_count, 1, 1, 0, 0, 0)

        return current


# =============================================================================
# 初始化配置表 (Configuration)
#
# 范围设定逻辑：
# 1. Day/Week/Month: 仅在有信史以来的范围显示 (-10,000 ~ +10,000)
# 2. Year: 基本上总是显示，但在极宏观视角下可能会被 Culling 掉
# 3. Deep Time: 无限制
# =============================================================================

# 常量辅助
ONE_DAY = 86_400 * 1_000_000
ONE_YEAR = int(ONE_DAY * 365.2425)

# --- Level 1: Micro Scale (Human Log) ---
# 限制：公元前1万年 - 公元1万年
HIST_MIN = -10000
HIST_MAX = 10000

TickStepper._register('day_1', '1 Day', 'Day', 1, ONE_DAY, HIST_MIN, HIST_MAX)
TickStepper._register('week_1', '1 Week', 'Day', 7, ONE_DAY * 7, HIST_MIN, HIST_MAX)
TickStepper._register('month_1', '1 Month', 'Month', 1, ONE_DAY * 30, HIST_MIN, HIST_MAX)
TickStepper._register('month_3', '1 Quarter', 'Month', 3, ONE_DAY * 90, HIST_MIN, HIST_MAX)

# --- Level 2: Historical Scale (Civilization) ---
# 1-2-5 Pattern starts here for Years
TickStepper._register('year_1', '1 Year', 'Year', 1, ONE_YEAR)
TickStepper._register('year_2', '2 Years', 'Year', 2, ONE_YEAR * 2)
TickStepper._register('year_5', '5 Years', 'Year', 5, ONE_YEAR * 5)
TickStepper._register('year_10', '10 Years', 'Year', 10, ONE_YEAR * 10)
TickStepper._register('year_20', '20 Years', 'Year', 20, ONE_YEAR * 20)
TickStepper._register('year_50', '50 Years', 'Year', 50, ONE_YEAR * 50)
TickStepper._register('year_100', '1 Century', 'Year', 100, ONE_YEAR * 100)

# --- Level 3: Macro History ---
TickStepper._register('year_200', '2 Centuries', 'Year', 200, ONE_YEAR * 200)
TickStepper._register('year_500', '5 Centuries', 'Year', 500, ONE_YEAR * 500)
TickStepper._register('year_1k', '1 Millennium', 'Year', 1000, ONE_YEAR * 1000)

# --- Level 4: Deep Time (Geological) ---
# 10k, 20k, 50k, 100k ... 1 Billion
# 使用循环生成，保持代码整洁
base_steps = [1, 2, 5]
magnitudes = [10_000, 100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000]

for mag in magnitudes:
    for step in base_steps:
        total_years = step * mag
        label_suffix = ""
        if mag >= 1_000_000_000:
            label_suffix = "Ga"
        elif mag >= 1_000_000:
            label_suffix = "Ma"
        elif mag >= 1_000:
            label_suffix = "ka"

        # 简单生成 Label: e.g., "5 Ma"
        label_val = total_years
        if total_years >= 1_000_000_000:
            label = f"{total_years // 1_000_000_000} Ga"
        elif total_years >= 1_000_000:
            label = f"{total_years // 1_000_000} Ma"
        else:
            label = f"{total_years // 1000} ka"

        TickStepper._register(
            f'year_{total_years}',
            label,
            'Year',
            total_years,
            ONE_YEAR * total_years
        )
