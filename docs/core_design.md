这份整理后的设计规范突出了**架构的严谨性**和**实现的确定性**，语言更加精炼，适合作为项目的核心文档（Core Design Doc）。

---

# 通用历史时间系统 (Universal History Time System) 设计规范

## 1. 核心设计哲学 (Core Philosophy)

### 1.1 绝对单一事实来源 (Single Source of Truth)

* **时空分离**：严格区分“物理时间流”（绝对的）与“历法标签”（相对的）。
* **数据存储**：底层仅存储 **定点整数 JDN (Integer Fixed-Point JDN)**。禁止在核心层存储 (Y, M, D) 元组。
* **精度标准**：单位为**微秒 (Microseconds)**。利用 Python `int` 的无限精度特性，支持任意时间跨度（从宇宙起源到未来无限）。

### 1.2 算术逻辑：零误差 (Zero Error Arithmetic)

* **拒绝浮点**：彻底摒弃浮点运算，消除 `23:59:59.999999` 进位精度丢失问题。
* **定点计算**：所有加减运算均为整数位移。
* 1 天 =  微秒。



### 1.3 统一度量衡：外推格里高利历 (Proleptic Gregorian)

* **数学连续性**：强制向过去无限外推格里高利历规则（400年周期闰法）。即使在历史上未实行该历法的时期（如1582年前或恐龙时代），依然以此作为唯一的数学坐标轴。
* **天文纪年法 (Astronomical Year Numbering)**：
* 系统内部使用 **Year 0**。
* 映射关系：`1 BC` = `Year 0`, `2 BC` = `Year -1`。
* 公式：。



---

## 2. 核心算法 (Core Algorithms)

### 2.1 日期转换：Fliegel & Van Flandern

* **算法选型**：Fliegel & Van Flandern (1968) 整数算法。
* **特性**：
* 专为整数运算优化，无浮点除法。
* 通过 `+4800` 偏移量消除负年份计算差异，保证数学上的单调连续性。



### 2.2 相位对齐：午夜偏移 (Midnight Offset)

* **冲突**：JDN 定义起点为 **12:00 (Noon)**，公历/日常使用起点为 **00:00 (Midnight)**。
* **解决方案**：核心类内部维护半天偏移 (`HALF_DAY_UNIT`)。
* `Value (Internal)` = `JDN_Noon` - `0.5 Days` + `TimeOffset`
* 对外表现为自然日午夜起算，对内保持 JDN 数学兼容。



---

## 3. 架构与实现 (Implementation)

### 3.1 核心类 `JDNTimestamp` (Pure Python)

不依赖任何第三方库，仅依赖 Python 标准库。

* **存储**：`value: int` (Total Microseconds from JDN Epoch).
* **常量**：
* `SCALE = 1_000_000`
* `DAY_UNIT = 86_400_000_000`


* **属性**：只读属性 `year`, `month`, `day` 等均通过实时计算得出（View），不占用存储空间。

### 3.2 桥接层 (Bridge Layer)

负责“绝对时间”与“人类历法/库”之间的脏活累活。

| Bridge | 职责 | 关键约束 |
| --- | --- | --- |
| **`PythonTimeBridge`** | 与 `datetime` 互转 | 必须处理 `datetime` 的 `1-9999` 年份限制；时区必须归一化为 UTC。 |
| **`LunarDateBridge`** | 与 `lunar_python` 互转 | **输入**：JDN  Solar  Lunar。<br>

<br>**输出**：统一正整数 Month，配合 `is_leap` 标记位。 |

---

## 4. 关键基准与陷阱 (Benchmarks & Gotchas)

### 4.1 JDN 0 锚点

在 **Proleptic Gregorian** 体系下，JDN `0` (value=0) 对应的时间点是：

* **-4713年 (4714 BC) 11月 24日 12:00:00**
* *注意：不是 Jan 1，也不是 Julian Calendar 的日期。*

### 4.2 历史连续性 vs 历史事实

* **不存在的日期**：历史上的 `1582-10-05` 被跳过，但在本系统中**存在**。
* **理由**：系统是数学标尺，不是历史模拟器。UI 层负责处理“历史空白期”的显示，底层逻辑必须保持连续。

### 4.3 精度完备性 (Round-trip Integrity)

* **测试金标准**：任意时间点 ，经过 `T -> Gregorian -> T` 转换后，误差必须为 **0 微秒**。
* **边界测试**：跨越午夜 (`23:59:59.999999` + `1us`)、跨越零年 (`-1 Dec 31`  `0 Jan 1`) 必须平滑无缝。

---

## 5. I/O 映射策略 (I/O Strategy)

### 5.1 输入解析 (Input)

* **公元前输入**：用户输入 "5000 BC"  转换为天文年 `-4999`  存入 JDN。
* **年号输入**：用户输入 "康熙十年"  查表得 1671 AD  `LunarDateBridge` 获取对应日期  存入 JDN。

### 5.2 视图呈现 (Output)

系统根据时间跨度自动降级显示策略：

1. **近代 (Historical Era)**: 完整显示公历 (YMD-HMS) + 农历/干支/年号。
2. **史前 (Prehistoric)**: 仅显示公历年份 (Astronomical Year)。
3. **远古 (Deep Time)**: `Year < -10,000`，转换为 **BP (Before Present)** 格式显示（如 "1.5 Million Years BP"）。
