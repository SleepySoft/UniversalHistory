"""
Chinese numeral -> Arabic digit conversion.

Ported verbatim (minus test entry points) from History/Utility/to_arab.py.
Used by the natural-language time parser (e.g. "公元前二百年").
"""

from __future__ import annotations

import re

CN_NUM = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,

    '〇': 0,
    '一': 1,
    '二': 2,
    '三': 3,
    '四': 4,
    '五': 5,
    '六': 6,
    '七': 7,
    '八': 8,
    '九': 9,

    '零': 0,
    '壹': 1,
    '贰': 2,
    '叁': 3,
    '肆': 4,
    '伍': 5,
    '陆': 6,
    '柒': 7,
    '捌': 8,
    '玖': 9,

    '貮': 2,
    '两': 2,
}
CN_UNIT_L1 = {
    '十': 10,
    '拾': 10,
    '百': 100,
    '佰': 100,
    '千': 1000,
    '仟': 1000,
}
CN_UNIT_L2 = {
    '万': 10000,
    '萬': 10000,
    '亿': 100000000,
    '億': 100000000,
    '兆': 1000000000000,
}


def cn_num_to_digit(cn_num: str):
    """
    Algorithm:
        a.  The best way is parse from lower digit to upper digit.
        b.  The Chinese number has 2 level of unit:
                L1: 十百千; L2: 万亿兆...
            For L1 unit, it cannot be decorated. For L2 unit, it can be decorated by the unit that less than itself.
                Example: 一千万 is OK, but 一百千 or 一亿万 is invalid.
                More complex Example: 五万四千三百二十一万亿 四千三百二十一万 四千三百二十一
            We can figured out that:
                1. The L1 unit should not composite. 四千三百二十一 -> 4 * 1000 + 3 * 100 + 2 * 10 + 1
                2. The L2 unit should be composted. If we meet 万, the base unit should multiple with 10000.
                3. If we meet a larger L2 unit. The base unit should reset to it.
    :param cn_num: A single cn number string.
    :return: The digit that comes from cn number.
    """
    sum_num = 0
    unit_l1 = 1
    unit_l2 = 1
    unit_l2_max = 0
    digit_missing = False
    num_chars = list(cn_num)

    while num_chars:
        num_char = num_chars.pop()
        if num_char in CN_UNIT_L1:
            unit_l1 = CN_UNIT_L1.get(num_char)
            digit_missing = True
        elif num_char in CN_UNIT_L2:
            unit = CN_UNIT_L2.get(num_char)
            if unit > unit_l2_max:
                unit_l2_max = unit
                unit_l2 = unit
            else:
                unit_l2 *= unit
            unit_l1 = 1
            digit_missing = True
        elif num_char in CN_NUM:
            digit = CN_NUM.get(num_char) * unit_l1 * unit_l2
            # For discrete digit. It has no effect to the standard expression.
            unit_l1 *= 10
            sum_num += digit
            digit_missing = False
        else:
            continue
    if digit_missing:
        sum_num += unit_l1 * unit_l2

    return sum_num


pattern = re.compile(r'([0123456789〇一二三四五六七八九零壹贰叁肆伍陆柒捌玖貮两十拾百佰千仟万萬亿億兆]+)')


def text_cn_num_to_arab(text: str) -> str:
    match_text = pattern.findall(text)
    match_text = list(set(match_text))
    match_text.sort(key=lambda x: len(x), reverse=True)
    for cn_num in match_text:
        text = text.replace(cn_num, str(cn_num_to_digit(cn_num)))
    return text
