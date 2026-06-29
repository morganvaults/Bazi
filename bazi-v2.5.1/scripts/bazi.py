#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
融合版八字排盘与评分工具。

纯 Python 内置实现，支持完整生日排盘和四柱结构评分。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calendar_core import (  # type: ignore
    DIZHI,
    DIZHI_CANGGAN,
    DIZHI_WUXING,
    JIEQI_DATES,
    SHICHEN,
    TIANGAN,
    TIANGAN_WUXING,
    TIANGAN_YINYANG,
    get_day_ganzhi,
    get_hour_ganzhi,
    get_jieqi_month,
    get_month_ganzhi,
    get_year_ganzhi,
    gregorian_to_lunar,
)
from xing_chong_he_hai import XingChongHeHai  # type: ignore


GAN_WUXING = dict(zip(TIANGAN, TIANGAN_WUXING))
ZHI_WUXING = dict(zip(DIZHI, DIZHI_WUXING))
GAN_YINYANG = dict(zip(TIANGAN, TIANGAN_YINYANG))

WUXING = ["木", "火", "土", "金", "水"]
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
DEFAULT_WRAP_WIDTH = 72

TIANGAN_HE = {
    frozenset(("甲", "己")): "土",
    frozenset(("乙", "庚")): "金",
    frozenset(("丙", "辛")): "水",
    frozenset(("丁", "壬")): "木",
    frozenset(("戊", "癸")): "火",
}

LIUHE_HUA = {
    frozenset(("子", "丑")): "土",
    frozenset(("寅", "亥")): "木",
    frozenset(("卯", "戌")): "火",
    frozenset(("辰", "酉")): "金",
    frozenset(("巳", "申")): "水",
    frozenset(("午", "未")): "土",
}

SANHE_HUA = {
    frozenset(("申", "子", "辰")): "水",
    frozenset(("亥", "卯", "未")): "木",
    frozenset(("寅", "午", "戌")): "火",
    frozenset(("巳", "酉", "丑")): "金",
}

BANHE_HUA = {
    frozenset(("申", "辰")): "水", frozenset(("申", "子")): "水", frozenset(("子", "辰")): "水",
    frozenset(("亥", "未")): "木", frozenset(("亥", "卯")): "木", frozenset(("卯", "未")): "木",
    frozenset(("寅", "戌")): "火", frozenset(("寅", "午")): "火", frozenset(("午", "戌")): "火",
    frozenset(("巳", "丑")): "金", frozenset(("巳", "酉")): "金", frozenset(("酉", "丑")): "金",
}

POSITION_NAMES = ["年柱", "月柱", "日柱", "时柱"]

LIU_SHI_JIA_ZI = [
    "甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉",
    "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未",
    "甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳",
    "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑",
    "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥",
]

# Exact solar-term overrides used when a chart is close enough that day-level
# approximations distort the starting age of luck pillars.
JIEQI_EXACT_OVERRIDES = {
    2008: {
        "白露": datetime(2008, 9, 7, 15, 14),
    },
    2024: {
        "小寒": datetime(2024, 1, 6, 4, 49),
        "立春": datetime(2024, 2, 4, 16, 26),
        "驚蟄": datetime(2024, 3, 5, 10, 23),
        "惊蛰": datetime(2024, 3, 5, 10, 23),
        "清明": datetime(2024, 4, 4, 15, 2),
        "立夏": datetime(2024, 5, 5, 8, 10),
        "芒種": datetime(2024, 6, 5, 12, 10),
        "芒种": datetime(2024, 6, 5, 12, 10),
        "小暑": datetime(2024, 7, 6, 22, 20),
        "立秋": datetime(2024, 8, 7, 8, 9),
        "白露": datetime(2024, 9, 7, 11, 11),
        "寒露": datetime(2024, 10, 8, 2, 59),
        "立冬": datetime(2024, 11, 7, 6, 20),
        "大雪": datetime(2024, 12, 6, 23, 17),
    },
    1995: {
        "芒種": datetime(1995, 6, 6, 11, 42, 28),
        "芒种": datetime(1995, 6, 6, 11, 42, 28),
        "夏至": datetime(1995, 6, 22, 4, 34, 22),
        "小暑": datetime(1995, 7, 7, 22, 1, 0),
    },
    2004: {
        "小寒": datetime(2004, 1, 6, 8, 58),
        "立春": datetime(2004, 2, 4, 18, 48),
    },
    2006: {
        "清明": datetime(2006, 4, 5, 6, 15),
    },
    2025: {
        "小寒": datetime(2025, 1, 5, 10, 33),
        "立春": datetime(2025, 2, 3, 22, 10),
        "驚蟄": datetime(2025, 3, 5, 16, 7),
        "惊蛰": datetime(2025, 3, 5, 16, 7),
        "清明": datetime(2025, 4, 4, 20, 48),
        "立夏": datetime(2025, 5, 5, 13, 57),
        "芒種": datetime(2025, 6, 5, 17, 56),
        "芒种": datetime(2025, 6, 5, 17, 56),
        "小暑": datetime(2025, 7, 7, 4, 4),
        "立秋": datetime(2025, 8, 7, 13, 51),
        "白露": datetime(2025, 9, 7, 16, 52),
        "寒露": datetime(2025, 10, 8, 8, 41),
        "立冬": datetime(2025, 11, 7, 12, 3),
        "大雪": datetime(2025, 12, 7, 5, 5),
    }
}

JIE_TERMS = {"立春", "驚蟄", "惊蛰", "清明", "立夏", "芒種", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"}

JIE_MONTH_NUMBERS = {
    "立春": 1,
    "驚蟄": 2,
    "惊蛰": 2,
    "清明": 3,
    "立夏": 4,
    "芒種": 5,
    "芒种": 5,
    "小暑": 6,
    "立秋": 7,
    "白露": 8,
    "寒露": 9,
    "立冬": 10,
    "大雪": 11,
    "小寒": 12,
}

HIDDEN_WEIGHTS = {
    1: [1.0],
    2: [1.0, 0.6],
    3: [1.0, 0.6, 0.3],
}

GE_JU_SCORES = {
    "正官格": 13, "七杀格": 10, "正印格": 13, "偏印格": 9,
    "正财格": 12, "偏财格": 10, "食神格": 12, "伤官格": 8,
    "建禄格": 10, "羊刃格": 7,
}

MU_KU_BY_ZHI = {
    "辰": "水",
    "戌": "火",
    "丑": "金",
    "未": "木",
}

MU_KU_CHONG = {
    frozenset(("辰", "戌")): "辰戌冲，水火墓库被冲动",
    frozenset(("丑", "未")): "丑未冲，金木墓库被冲动",
}

KONG_WANG = {
    "甲子": ("戌", "亥"), "乙丑": ("戌", "亥"), "丙寅": ("戌", "亥"), "丁卯": ("戌", "亥"), "戊辰": ("戌", "亥"), "己巳": ("戌", "亥"), "庚午": ("戌", "亥"), "辛未": ("戌", "亥"), "壬申": ("戌", "亥"), "癸酉": ("戌", "亥"),
    "甲戌": ("申", "酉"), "乙亥": ("申", "酉"), "丙子": ("申", "酉"), "丁丑": ("申", "酉"), "戊寅": ("申", "酉"), "己卯": ("申", "酉"), "庚辰": ("申", "酉"), "辛巳": ("申", "酉"), "壬午": ("申", "酉"), "癸未": ("申", "酉"),
    "甲申": ("午", "未"), "乙酉": ("午", "未"), "丙戌": ("午", "未"), "丁亥": ("午", "未"), "戊子": ("午", "未"), "己丑": ("午", "未"), "庚寅": ("午", "未"), "辛卯": ("午", "未"), "壬辰": ("午", "未"), "癸巳": ("午", "未"),
    "甲午": ("辰", "巳"), "乙未": ("辰", "巳"), "丙申": ("辰", "巳"), "丁酉": ("辰", "巳"), "戊戌": ("辰", "巳"), "己亥": ("辰", "巳"), "庚子": ("辰", "巳"), "辛丑": ("辰", "巳"), "壬寅": ("辰", "巳"), "癸卯": ("辰", "巳"),
    "甲辰": ("寅", "卯"), "乙巳": ("寅", "卯"), "丙午": ("寅", "卯"), "丁未": ("寅", "卯"), "戊申": ("寅", "卯"), "己酉": ("寅", "卯"), "庚戌": ("寅", "卯"), "辛亥": ("寅", "卯"), "壬子": ("寅", "卯"), "癸丑": ("寅", "卯"),
    "甲寅": ("子", "丑"), "乙卯": ("子", "丑"), "丙辰": ("子", "丑"), "丁巳": ("子", "丑"), "戊午": ("子", "丑"), "己未": ("子", "丑"), "庚申": ("子", "丑"), "辛酉": ("子", "丑"), "壬戌": ("子", "丑"), "癸亥": ("子", "丑"),
}

CHANG_SHENG_START = {
    "甲": ("亥", 1), "乙": ("午", -1),
    "丙": ("寅", 1), "丁": ("酉", -1),
    "戊": ("寅", 1), "己": ("酉", -1),
    "庚": ("巳", 1), "辛": ("子", -1),
    "壬": ("申", 1), "癸": ("卯", -1),
}

CHANG_SHENG_STAGES = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]


def gan_zhi(indices: Tuple[int, int]) -> str:
    return TIANGAN[indices[0]] + DIZHI[indices[1]]


def parse_time(value: str) -> Tuple[int, int]:
    if ":" in value:
        hour, minute = value.split(":", 1)
        return int(hour), int(minute)
    return int(value), 0


def get_shi_shen(day_gan: str, target_gan: str) -> str:
    day_wx = GAN_WUXING[day_gan]
    target_wx = GAN_WUXING[target_gan]
    same_yinyang = GAN_YINYANG[day_gan] == GAN_YINYANG[target_gan]

    if target_wx == day_wx:
        return "比肩" if same_yinyang else "劫财"
    if SHENG[day_wx] == target_wx:
        return "食神" if same_yinyang else "伤官"
    if KE[day_wx] == target_wx:
        return "偏财" if same_yinyang else "正财"
    if KE[target_wx] == day_wx:
        return "七杀" if same_yinyang else "正官"
    if SHENG[target_wx] == day_wx:
        return "偏印" if same_yinyang else "正印"
    return "未知"


def jie_candidates_around(moment: datetime) -> List[Tuple[str, datetime]]:
    candidates = []
    for year in [moment.year - 1, moment.year, moment.year + 1]:
        for month, terms in JIEQI_DATES.items():
            for name, day in terms:
                if name not in JIE_TERMS:
                    continue
                exact = JIEQI_EXACT_OVERRIDES.get(year, {}).get(name)
                candidates.append((name, exact or datetime(year, month, day, 0, 0)))
    return candidates


def get_year_ganzhi_at(moment: datetime) -> Tuple[int, int]:
    lichun = JIEQI_EXACT_OVERRIDES.get(moment.year, {}).get("立春") or datetime(moment.year, 2, JIEQI_DATES[2][0][1], 0, 0)
    ganzhi_year = moment.year if moment >= lichun else moment.year - 1
    offset = ganzhi_year - 1984
    return offset % 10, offset % 12


def get_jie_month_at(moment: datetime) -> int:
    previous = [(name, dt) for name, dt in jie_candidates_around(moment) if dt <= moment and name in JIE_MONTH_NUMBERS]
    if not previous:
        return get_jieqi_month(moment.year, moment.month, moment.day)
    name, _ = max(previous, key=lambda item: item[1])
    return JIE_MONTH_NUMBERS[name]


def pillars_from_datetime(moment: datetime) -> Dict[str, str]:
    year = get_year_ganzhi_at(moment)
    jieqi_month = get_jie_month_at(moment)
    month = get_month_ganzhi(year[0], jieqi_month)
    day_pillar = get_day_ganzhi(moment.year, moment.month, moment.day)
    hour_pillar = get_hour_ganzhi(day_pillar[0], moment.hour)
    return {
        "年柱": gan_zhi(year),
        "月柱": gan_zhi(month),
        "日柱": gan_zhi(day_pillar),
        "时柱": gan_zhi(hour_pillar),
    }


def parse_pillars(value: str) -> Dict[str, str]:
    parts = value.replace(",", " ").replace("，", " ").split()
    if len(parts) != 4 or any(len(p) != 2 for p in parts):
        raise ValueError("四柱格式应为：乙亥 壬午 己巳 甲子")
    for pillar in parts:
        if pillar[0] not in GAN_WUXING or pillar[1] not in ZHI_WUXING:
            raise ValueError(f"无效干支：{pillar}")
    return dict(zip(["年柱", "月柱", "日柱", "时柱"], parts))




WENZHEN_SIZHU_URL = "https://bzapi2.iwzbz.com/szbz.php"
WENZHEN_BASE_URL = "https://bzapi4.iwzbz.com/getbasebz8.php"


def _http_get_json(url: str, timeout: int = 12):
    req = urllib.request.Request(url, headers={"User-Agent": "bazi-v2/2.5"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def wenzhen_birth_candidates(pillars: Dict[str, str]) -> List[str]:
    bz = "".join(pillars[pos] for pos in POSITION_NAMES)
    url = WENZHEN_SIZHU_URL + "?bz=" + urllib.parse.quote(bz)
    data = _http_get_json(url)
    if not isinstance(data, list):
        raise RuntimeError("问真四柱反查返回格式异常")
    return [str(item) for item in data]


def parse_wenzhen_datetime(value: str) -> datetime:
    date_part, time_part = value.strip().split(" ", 1)
    year, month, day = [int(x) for x in date_part.split("-")]
    time_bits = [int(x) for x in time_part.split(":")]
    while len(time_bits) < 3:
        time_bits.append(0)
    return datetime(year, month, day, time_bits[0], time_bits[1], time_bits[2])


def wenzhen_base_chart(birth: datetime, gender: str) -> Dict:
    sex = 1 if gender == "男" else 0
    params = {
        "d": birth.strftime("%Y-%m-%d %H:%M:%S"),
        "s": str(sex),
        "today": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vip": "0",
        "userguid": "",
        "yzs": "0",
    }
    data = _http_get_json(WENZHEN_BASE_URL + "?" + urllib.parse.urlencode(params))
    if not isinstance(data, dict) or "bz" not in data:
        raise RuntimeError("问真排盘返回格式异常")
    return data


def wenzhen_pillars(data: Dict) -> Dict[str, str]:
    bz = data.get("bz", {})
    return {
        "年柱": str(bz.get("0", "")) + str(bz.get("1", "")),
        "月柱": str(bz.get("2", "")) + str(bz.get("3", "")),
        "日柱": str(bz.get("4", "")) + str(bz.get("5", "")),
        "时柱": str(bz.get("6", "")) + str(bz.get("7", "")),
    }


def format_wenzhen_qiyun(qiyunarr: List[int]) -> str:
    labels = ["年", "月", "天", "时", "分"]
    parts = []
    for value, label in zip(qiyunarr[:5], labels):
        if value or label in ("年", "月"):
            parts.append(f"{value}{label}")
    return "出生后" + "".join(parts) + "起运"


def add_wenzhen_age(qiyunarr: List[int], offset_years: int) -> str:
    years = int(qiyunarr[0]) + offset_years if len(qiyunarr) > 0 else offset_years
    months = int(qiyunarr[1]) if len(qiyunarr) > 1 else 0
    days = int(qiyunarr[2]) if len(qiyunarr) > 2 else 0
    hours = int(qiyunarr[3]) if len(qiyunarr) > 3 else 0
    minutes = int(qiyunarr[4]) if len(qiyunarr) > 4 else 0
    result = f"{years}岁{months}月"
    if days or hours or minutes:
        result += f"{days}天"
    if hours or minutes:
        result += f"{hours}时"
    if minutes:
        result += f"{minutes}分"
    return result


def wenzhen_dayun_info(data: Dict) -> Dict:
    qiyunarr = [int(x) for x in data.get("qiyunarr", [])]
    dayuns = [str(x) for x in data.get("dayun", [])]
    luck = []
    for i, ganzhi in enumerate(dayuns):
        luck.append({
            "序": i + 1,
            "干支": ganzhi,
            "年龄段": f"{add_wenzhen_age(qiyunarr, i * 10)}-{add_wenzhen_age(qiyunarr, (i + 1) * 10)}",
            "来源": "问真八字",
        })
    return {
        "来源": "问真八字",
        "起运": format_wenzhen_qiyun(qiyunarr) if qiyunarr else "未知",
        "起运数组": qiyunarr,
        "虚岁": data.get("qiyunsui"),
        "交运": data.get("jiaoyun", ""),
        "大运": luck,
        "说明": "起运和大运来自问真八字公开接口。",
    }


def attach_wenzhen_result(result: Dict, data: Dict, birth: datetime) -> None:
    wz_dayun = wenzhen_dayun_info(data)
    result["问真八字"] = {
        "出生时间": birth.strftime("%Y-%m-%d %H:%M:%S"),
        "农历": data.get("bz", {}).get("8", ""),
        "四柱": wenzhen_pillars(data),
        "起运": wz_dayun,
    }
    result["大运"] = wz_dayun
    result["资料等级"] = "A/S：完整生日排盘（问真接口校准起运）"


def print_wenzhen_candidates(candidates: List[str]) -> None:
    print("【问真八字反查候选】")
    if not candidates:
        print("  1801-2099 范围内未找到匹配出生时间。")
        return
    for idx, item in enumerate(candidates, 1):
        print(f"  {idx}. {item}")
    recommended = len(candidates)
    print(f"\n请用 --candidate-index 选择候选，例如：--wenzhen --pillars \"乙亥 壬午 己巳 甲子\" --gender 女 --candidate-index {recommended}")


def hidden_stems(pillars: Dict[str, str]) -> Dict[str, List[str]]:
    return {k: DIZHI_CANGGAN[v[1]] for k, v in pillars.items()}


def simple_wuxing(pillars: Dict[str, str]) -> Dict[str, int]:
    result = {wx: 0 for wx in WUXING}
    for pillar in pillars.values():
        result[GAN_WUXING[pillar[0]]] += 1
        result[ZHI_WUXING[pillar[1]]] += 1
    return result


def weighted_wuxing(pillars: Dict[str, str]) -> Dict[str, float]:
    result = {wx: 0.0 for wx in WUXING}
    for key, pillar in pillars.items():
        result[GAN_WUXING[pillar[0]]] += 1.0
        stems = DIZHI_CANGGAN[pillar[1]]
        weights = HIDDEN_WEIGHTS[len(stems)]
        for stem, weight in zip(stems, weights):
            result[GAN_WUXING[stem]] += weight
        if key == "月柱":
            for stem, weight in zip(stems, weights):
                extra = 1.5 if weight == 1.0 else 0.6 if weight == 0.6 else 0.3
                result[GAN_WUXING[stem]] += extra
    return {k: round(v, 2) for k, v in result.items()}


def ten_gods(pillars: Dict[str, str]) -> Dict[str, str]:
    day_gan = pillars["日柱"][0]
    return {
        key: "日主" if key == "日柱" else get_shi_shen(day_gan, pillar[0])
        for key, pillar in pillars.items()
    }


def month_strength(day_wx: str, month_zhi: str) -> Tuple[str, float]:
    month_wx = ZHI_WUXING[month_zhi]
    if day_wx == month_wx:
        return "旺", 3.0
    if SHENG[month_wx] == day_wx:
        return "相", 2.0
    if SHENG[day_wx] == month_wx:
        return "休", -0.5
    if KE[day_wx] == month_wx:
        return "囚", -1.5
    if KE[month_wx] == day_wx:
        return "死", -2.5
    return "平", 0.0


def analyze_strength(pillars: Dict[str, str], xing_chong: Optional[Dict] = None) -> Dict:
    day_gan = pillars["日柱"][0]
    day_wx = GAN_WUXING[day_gan]
    weighted = weighted_wuxing(pillars)
    month_zhi = pillars["月柱"][1]
    month_state, month_score = month_strength(day_wx, month_zhi)

    roots = []
    root_score = 0.0
    for key, pillar in pillars.items():
        stems = DIZHI_CANGGAN[pillar[1]]
        weights = HIDDEN_WEIGHTS[len(stems)]
        for stem, weight in zip(stems, weights):
            if GAN_WUXING[stem] == day_wx:
                position_weight = {"月柱": 1.3, "日柱": 1.2, "年柱": 0.8, "时柱": 0.8}[key]
                root_score += weight * position_weight
                roots.append(f"{key}{pillar[1]}藏{stem}")

    support_wx = [day_wx, next(wx for wx, born in SHENG.items() if born == day_wx)]
    output_wx = SHENG[day_wx]
    wealth_wx = KE[day_wx]
    officer_wx = next(wx for wx, controlled in KE.items() if controlled == day_wx)

    support = weighted[day_wx] + weighted[support_wx[1]]
    drain = weighted[output_wx] * 0.8 + weighted[wealth_wx] + weighted[officer_wx] * 1.1
    raw_score = month_score + root_score * 0.9 + support * 0.45 - drain * 0.35

    correction = 0.0
    notes = []
    if xing_chong:
        day_branch = pillars["日柱"][1]
        for item in xing_chong.get("六冲", []):
            if day_branch in item.get("关系", ""):
                correction -= 0.4
                notes.append("日支逢冲，根气与稳定度有折损")
        for item in xing_chong.get("六合", []):
            if day_branch in item.get("关系", ""):
                correction += 0.2
                notes.append("日支逢合，结构有和合缓冲")

    score = raw_score + correction
    if score <= -3:
        level = "身弱"
    elif score < -1:
        level = "偏弱"
    elif score <= 1:
        level = "中和"
    elif score < 3:
        level = "偏旺"
    else:
        level = "身旺"

    special = None
    if support >= drain * 2.5 and month_state in {"旺", "相"}:
        special = "从旺/专旺候选"
    if drain >= support * 2.8 and not roots and month_state in {"囚", "死"}:
        special = "从弱候选"

    return {
        "日主": f"{day_gan}{day_wx}",
        "月令": f"{month_zhi}{ZHI_WUXING[month_zhi]}",
        "月令旺衰": month_state,
        "通根": roots,
        "生扶力量": round(support, 2),
        "克泄耗力量": round(drain, 2),
        "强弱分": round(score, 2),
        "综合判断": level,
        "特殊格局提示": special,
        "修正说明": notes,
    }


def yongshen(pillars: Dict[str, str], strength: Dict) -> Dict:
    day_wx = GAN_WUXING[pillars["日柱"][0]]
    output_wx = SHENG[day_wx]
    wealth_wx = KE[day_wx]
    officer_wx = next(wx for wx, controlled in KE.items() if controlled == day_wx)
    seal_wx = next(wx for wx, born in SHENG.items() if born == day_wx)
    peer_wx = day_wx

    level = strength["综合判断"]
    if level in {"身旺", "偏旺"}:
        primary = [output_wx, wealth_wx, officer_wx]
        avoid = [seal_wx, peer_wx]
        reason = "日主偏旺，宜泄、耗、克，使旺气流通。"
    elif level in {"身弱", "偏弱"}:
        primary = [seal_wx, peer_wx]
        avoid = [wealth_wx, officer_wx, output_wx]
        reason = "日主偏弱，宜印星生身、比劫助身。"
    else:
        primary = [output_wx, wealth_wx]
        avoid = []
        reason = "日主近中和，取流通与成事之神，不宜过度偏补。"

    month_branch = pillars["月柱"][1]
    hot_months = {"巳", "午", "未"}
    cold_months = {"亥", "子", "丑"}
    if month_branch in hot_months:
        tuning = ["水", "金"]
        tuning_reason = "夏令火燥，调候重在水润、金生水。"
    elif month_branch in cold_months:
        tuning = ["火", "木"]
        tuning_reason = "冬令寒湿，调候重在火暖、木引火。"
    else:
        tuning = []
        tuning_reason = "寒暖不极，调候不压过扶抑。"

    weighted = weighted_wuxing(pillars)
    bridge = []
    if weighted["水"] > 3 and weighted["火"] > 3:
        bridge.append("木")
    if weighted["木"] > 3 and weighted["金"] > 2.5:
        bridge.append("水")
    if weighted["土"] > 4 and weighted["水"] > 2.5:
        bridge.append("金")

    merged = []
    for wx in primary + tuning + bridge:
        if wx not in merged:
            merged.append(wx)
    final_avoid = [wx for wx in avoid if wx not in tuning]
    conflict = [wx for wx in avoid if wx in tuning]

    return {
        "第一用神": primary[:2],
        "调候用神": tuning,
        "通关用神": bridge,
        "综合喜用": merged,
        "忌神": final_avoid,
        "扶抑与调候冲突": conflict,
        "取用理由": reason,
        "调候说明": tuning_reason + (" 调候与扶抑相冲突的五行只宜适量，不宜过旺。" if conflict else ""),
    }


def get_geju(pillars: Dict[str, str], gods: Dict[str, str]) -> str:
    month_god = gods["月柱"]
    mapping = {
        "正官": "正官格", "七杀": "七杀格", "正印": "正印格", "偏印": "偏印格",
        "正财": "正财格", "偏财": "偏财格", "食神": "食神格", "伤官": "伤官格",
        "比肩": "建禄格", "劫财": "羊刃格",
    }
    # 月令主气比月干更重要：用月支主气重新计算十神。
    day_gan = pillars["日柱"][0]
    month_main_stem = DIZHI_CANGGAN[pillars["月柱"][1]][0]
    month_main_god = get_shi_shen(day_gan, month_main_stem)
    return mapping.get(month_main_god) or mapping.get(month_god, "杂气格")


def ten_god_for_wuxing(day_gan: str, target_wx: str) -> str:
    candidates = [gan for gan, wx in GAN_WUXING.items() if wx == target_wx]
    gods = [get_shi_shen(day_gan, gan) for gan in candidates]
    if set(gods) == {"比肩", "劫财"}:
        return "比劫"
    if set(gods) == {"食神", "伤官"}:
        return "食伤"
    if set(gods) == {"正财", "偏财"}:
        return "财星"
    if set(gods) == {"正官", "七杀"}:
        return "官杀"
    if set(gods) == {"正印", "偏印"}:
        return "印星"
    return "/".join(gods)


def analyze_mu_ku(pillars: Dict[str, str]) -> Dict:
    day_gan = pillars["日柱"][0]
    visible_stems = [pillar[0] for pillar in pillars.values()]
    branches = [pillar[1] for pillar in pillars.values()]
    items = []
    day_master_tombs = []

    for position, pillar in pillars.items():
        zhi = pillar[1]
        if zhi not in MU_KU_BY_ZHI:
            continue
        stored_wx = MU_KU_BY_ZHI[zhi]
        stored_gods = ten_god_for_wuxing(day_gan, stored_wx)
        changsheng = chang_sheng_stage(day_gan, zhi)
        is_day_master_tomb = changsheng == "墓"
        stored_stems = [gan for gan, wx in GAN_WUXING.items() if wx == stored_wx]
        exposed = [gan for gan in visible_stems if gan in stored_stems]
        chong = []
        for pair, meaning in MU_KU_CHONG.items():
            if zhi in pair and pair.issubset(set(branches)):
                chong.append(meaning)
        if is_day_master_tomb:
            day_master_tombs.append({
                "位置": position,
                "地支": zhi,
                "说明": f"{position}{zhi}为日主{day_gan}之墓",
            })
        items.append({
            "位置": position,
            "地支": zhi,
            "层级": "日主墓+五行库" if is_day_master_tomb else "五行库",
            "五行库": f"{stored_wx}库",
            "十神库": f"{stored_gods}库",
            "十二长生": changsheng,
            "是否日主墓": is_day_master_tomb,
            "藏干": DIZHI_CANGGAN[zhi],
            "对应五行透干": exposed,
            "是否透出": bool(exposed),
            "是否被冲开": bool(chong),
            "冲开说明": chong,
            "状态": "日主入墓且冲开可动" if is_day_master_tomb and chong else "日主入墓" if is_day_master_tomb else "冲开可动" if chong else "藏而待引",
        })

    wuxing_count = {}
    god_count = {}
    for item in items:
        wuxing_count[item["五行库"]] = wuxing_count.get(item["五行库"], 0) + 1
        god_count[item["十神库"]] = god_count.get(item["十神库"], 0) + 1

    suggestions = []
    if len(items) >= 3:
        suggestions.append("四墓库支偏多，资源、情绪和事务多藏于内，遇冲运流年更易出现阶段性转折。")
    if day_master_tombs:
        suggestions.append("日主入墓，主自我状态、承载力或行动力有收束闭藏之象，需看是否透出、冲开和运年引动。")
    if any(item["是否透出"] for item in items):
        suggestions.append("库中五行有透干者，较容易从隐藏资源转为现实可用。")
    if any(item["是否被冲开"] for item in items):
        suggestions.append("原局已有冲库，主变动中开库，得失常随迁动、关系调整或资产事项而来。")

    return {
        "墓库数量": len(items),
        "墓库明细": items,
        "四墓库支数量": len(items),
        "日主墓数量": len(day_master_tombs),
        "日主墓明细": day_master_tombs,
        "五行库统计": wuxing_count,
        "十神库统计": god_count,
        "分层说明": "四墓库支不等于日主皆入墓；日主墓以十二长生为准，五行库/十神库按辰戌丑未所藏五行转换。",
        "综合判断": "；".join(suggestions) if suggestions else "四墓库支不重，按常规藏干与冲合判断即可。",
    }


def analyze_kong_wang(pillars: Dict[str, str]) -> Dict:
    day_pillar = pillars["日柱"]
    kong = KONG_WANG[day_pillar]
    hits = []
    day_gan = day_pillar[0]
    for position, pillar in pillars.items():
        if pillar[1] in kong:
            hits.append({
                "位置": position,
                "地支": pillar[1],
                "十神": "日支" if position == "日柱" else get_shi_shen(day_gan, pillar[0]),
            })
    if hits:
        judgment = "原局有空亡，相关宫位/十神有虚、迟、落空或需待冲填实之象。"
    else:
        judgment = "原局四支未落日旬空亡。"
    return {
        "日柱": day_pillar,
        "旬空": list(kong),
        "落空": hits,
        "综合判断": judgment,
    }


def chang_sheng_stage(day_gan: str, branch: str) -> str:
    start_branch, direction = CHANG_SHENG_START[day_gan]
    start_index = DIZHI.index(start_branch)
    branch_index = DIZHI.index(branch)
    if direction == 1:
        offset = (branch_index - start_index) % 12
    else:
        offset = (start_index - branch_index) % 12
    return CHANG_SHENG_STAGES[offset]


def analyze_chang_sheng(pillars: Dict[str, str]) -> Dict:
    day_gan = pillars["日柱"][0]
    items = []
    strong = {"长生", "冠带", "临官", "帝旺"}
    weak = {"病", "死", "墓", "绝"}
    for position, pillar in pillars.items():
        stage = chang_sheng_stage(day_gan, pillar[1])
        if stage in strong:
            quality = "有力"
        elif stage in weak:
            quality = "偏弱/受藏"
        else:
            quality = "过渡"
        items.append({
            "位置": position,
            "地支": pillar[1],
            "十二长生": stage,
            "力量提示": quality,
        })
    stage_counts = {}
    for item in items:
        stage_counts[item["十二长生"]] = stage_counts.get(item["十二长生"], 0) + 1
    return {
        "日干": day_gan,
        "长生明细": items,
        "阶段统计": stage_counts,
        "综合判断": "十二长生用于辅助判断日主在四支的生旺墓绝，不单独决定格局高低。",
    }


def relation_breaks_pair(pair: List[str], xing_chong: Dict) -> List[str]:
    breaks = []
    pair_set = set(pair)
    for key in ["六冲", "三刑", "六害", "相破"]:
        for item in xing_chong.get(key, []):
            relation = item.get("关系", "")
            if all(zhi in relation for zhi in pair_set) or (key == "六冲" and any(zhi in relation for zhi in pair_set)):
                breaks.append(f"{key}:{relation}")
    return breaks


def classify_hehua(score: int, broken: bool, support_is_favorable: bool) -> str:
    if broken:
        return "被破"
    if score >= 78:
        return "成化"
    if score >= 58:
        return "半化"
    if score >= 38:
        return "合而不化" if support_is_favorable else "合绊"
    return "合绊"


def score_transform_power(hua_wx: str, pillars: Dict[str, str], positions: List[str], favorable: List[str], xing_chong: Dict, branches: List[str]) -> Tuple[int, List[str], bool]:
    weighted = weighted_wuxing(pillars)
    month_zhi = pillars["月柱"][1]
    visible = [pillar[0] for pillar in pillars.values()]
    roots = [pillar[1] for pillar in pillars.values() if ZHI_WUXING[pillar[1]] == hua_wx or any(GAN_WUXING[g] == hua_wx for g in DIZHI_CANGGAN[pillar[1]])]
    reasons = []
    score = 20
    if ZHI_WUXING[month_zhi] == hua_wx or any(GAN_WUXING[g] == hua_wx for g in DIZHI_CANGGAN[month_zhi]):
        score += 25
        reasons.append("化神得月令")
    if any(GAN_WUXING[g] == hua_wx for g in visible):
        score += 18
        reasons.append("化神透干")
    if roots:
        score += min(20, len(roots) * 7)
        reasons.append("化神有根")
    if weighted[hua_wx] >= 3:
        score += 15
        reasons.append("化神原局有力")
    elif weighted[hua_wx] >= 1.5:
        score += 8
        reasons.append("化神有气")
    if any(abs(POSITION_NAMES.index(a) - POSITION_NAMES.index(b)) == 1 for a in positions for b in positions if a != b):
        score += 8
        reasons.append("位置相邻")
    breaks = relation_breaks_pair(branches, xing_chong) if branches else []
    if breaks:
        score -= 25
        reasons.append("合局受冲刑害破")
    if hua_wx in favorable:
        score += 8
        reasons.append("化神为喜用")
    score = max(0, min(100, score))
    return score, reasons, bool(breaks)


def analyze_he_hua(pillars: Dict[str, str], strength: Dict, xing_chong: Dict, yong: Dict) -> Dict:
    items = []
    favorable = yong.get("综合喜用", [])
    keys = POSITION_NAMES

    for i in range(4):
        for j in range(i + 1, 4):
            gan1, gan2 = pillars[keys[i]][0], pillars[keys[j]][0]
            hua = TIANGAN_HE.get(frozenset((gan1, gan2)))
            if not hua:
                continue
            score, reasons, broken = score_transform_power(hua, pillars, [keys[i], keys[j]], favorable, xing_chong, [])
            state = classify_hehua(score, broken, hua in favorable)
            items.append({
                "类型": "天干五合",
                "关系": f"{gan1}{gan2}合{hua}",
                "位置": f"{keys[i]}-{keys[j]}",
                "化神": hua,
                "成化分": score,
                "状态": state,
                "成败理由": reasons or ["只见合象，化神力量不足"],
            })

    branches = [pillars[k][1] for k in keys]
    for i in range(4):
        for j in range(i + 1, 4):
            z1, z2 = branches[i], branches[j]
            hua = LIUHE_HUA.get(frozenset((z1, z2)))
            if not hua:
                continue
            score, reasons, broken = score_transform_power(hua, pillars, [keys[i], keys[j]], favorable, xing_chong, [z1, z2])
            state = classify_hehua(score, broken, hua in favorable)
            items.append({
                "类型": "地支六合",
                "关系": f"{z1}{z2}合{hua}",
                "位置": f"{keys[i]}-{keys[j]}",
                "化神": hua,
                "成化分": score,
                "状态": state,
                "成败理由": reasons or ["只见合象，化神力量不足"],
            })

    branch_set = set(branches)
    for combo, hua in SANHE_HUA.items():
        if combo.issubset(branch_set):
            combo_list = [z for z in branches if z in combo]
            positions = [keys[i] for i, z in enumerate(branches) if z in combo]
            score, reasons, broken = score_transform_power(hua, pillars, positions, favorable, xing_chong, combo_list)
            items.append({
                "类型": "三合局",
                "关系": f"{''.join(combo_list)}三合{hua}局",
                "位置": "-".join(positions),
                "化神": hua,
                "成化分": max(score, 72),
                "状态": classify_hehua(max(score, 72), broken, hua in favorable),
                "成败理由": reasons or ["三支齐全，成局基础足"],
            })

    for combo, hua in BANHE_HUA.items():
        if combo.issubset(branch_set) and not any(combo.issubset(full) and full.issubset(branch_set) for full in SANHE_HUA):
            combo_list = [z for z in branches if z in combo]
            positions = [keys[i] for i, z in enumerate(branches) if z in combo]
            score, reasons, broken = score_transform_power(hua, pillars, positions, favorable, xing_chong, combo_list)
            score = min(score, 68)
            items.append({
                "类型": "半合/拱合",
                "关系": f"{''.join(combo_list)}半合/拱{hua}",
                "位置": "-".join(positions),
                "化神": hua,
                "成化分": score,
                "状态": classify_hehua(score, broken, hua in favorable),
                "成败理由": reasons or ["半合拱局，待运年补足"],
            })

    if not items:
        judgment = "原局无明显天干五合或地支合局，按五行旺衰与刑冲主线判断。"
    else:
        formed = [i for i in items if i["状态"] in {"成化", "半化"}]
        blocked = [i for i in items if i["状态"] in {"合绊", "被破"}]
        judgment = f"合化关系{len(items)}组，成化/半化{len(formed)}组，合绊/被破{len(blocked)}组。"
    return {"合化明细": items, "综合判断": judgment}


def analyze_geju_quality(pillars: Dict[str, str], gods: Dict[str, str], strength: Dict, yong: Dict, hehua: Dict, xing_chong: Dict) -> Dict:
    geju = get_geju(pillars, gods)
    day_gan = pillars["日柱"][0]
    visible_gods = [god for key, god in gods.items() if key != "日柱"]
    clear_sources = []
    turbid_sources = []
    blocks = []
    score = 58

    month_main = DIZHI_CANGGAN[pillars["月柱"][1]][0]
    month_main_god = get_shi_shen(day_gan, month_main)
    if geju != "杂气格":
        score += 10
        clear_sources.append(f"月令主气为{month_main_god}，格局有根")
    else:
        turbid_sources.append("月令格神不专，需看组合取清")

    favorable = yong.get("综合喜用", [])
    avoid = yong.get("忌神", [])
    weighted = weighted_wuxing(pillars)
    if any(weighted[wx] >= 1.5 for wx in favorable):
        score += 10
        clear_sources.append("喜用有根有气")
    if any(GAN_WUXING[p[0]] in favorable for p in pillars.values()):
        score += 8
        clear_sources.append("喜用透干")
    if any(GAN_WUXING[p[0]] in avoid for p in pillars.values()):
        score -= 8
        turbid_sources.append("忌神透干混局")

    if "正官" in visible_gods and "七杀" in visible_gods:
        score -= 12
        turbid_sources.append("官杀混杂")
        blocks.append("官杀同透，事业/规则压力来源不一")
    if "食神" in visible_gods and "伤官" in visible_gods:
        score -= 8
        turbid_sources.append("食伤混杂")
    if "正印" in visible_gods and "偏印" in visible_gods:
        score -= 8
        turbid_sources.append("印枭混杂")
    if "伤官" in visible_gods and "正官" in visible_gods:
        score -= 12
        turbid_sources.append("伤官见官")
        blocks.append("表达输出与规则职位相冲")
    if any(g in visible_gods for g in ["比肩", "劫财"]) and any(g in visible_gods for g in ["正财", "偏财"]):
        score -= 8
        turbid_sources.append("比劫夺财")
    if any(g in visible_gods for g in ["偏印", "正印"]) and any(g in visible_gods for g in ["食神", "伤官"]):
        score -= 6
        turbid_sources.append("印食互碍")

    if xing_chong.get("六冲"):
        score -= min(12, len(xing_chong["六冲"]) * 4)
        blocks.append("原局冲动较多，格局稳定度下降")
    for item in hehua.get("合化明细", []):
        if item["化神"] in favorable and item["状态"] in {"成化", "半化"}:
            score += 5
            clear_sources.append(f"{item['关系']}助喜用")
        if item["化神"] in avoid and item["状态"] in {"成化", "半化"}:
            score -= 5
            turbid_sources.append(f"{item['关系']}助忌神")
        if item["状态"] in {"合绊", "被破"}:
            score -= 3
            blocks.append(f"{item['关系']}{item['状态']}")

    score = max(0, min(100, score))
    if score >= 82:
        level = "清"
    elif score >= 70:
        level = "偏清"
    elif score >= 58:
        level = "清中带浊"
    elif score >= 45:
        level = "浊中有清"
    else:
        level = "偏浊"
    advice = []
    if turbid_sources:
        advice.append("取清重点在扶喜用、制忌神，避免同时加强相互冲突的十神。")
    if "官杀混杂" in turbid_sources:
        advice.append("事业上宜用专业成果和规则化流程化杀，不宜多头承压。")
    if not advice:
        advice.append("格局主线较清，顺喜用方向放大即可。")

    return {
        "格局": geju,
        "清气分": score,
        "清浊等级": level,
        "清气来源": clear_sources or ["清气不显，需靠运年引动"],
        "浊气来源": turbid_sources,
        "成格阻点": blocks,
        "取清建议": advice,
    }


def score_chart(pillars: Dict[str, str], full_birth: bool = False, geju_quality: Optional[Dict] = None) -> Dict:
    gods = ten_gods(pillars)
    xing_chong = XingChongHeHai.analyze([p[1] for p in pillars.values()])
    strength = analyze_strength(pillars, xing_chong)
    use = yongshen(pillars, strength)
    weighted = weighted_wuxing(pillars)
    geju = get_geju(pillars, gods)

    values = list(weighted.values())
    avg = sum(values) / 5
    balance = max(0, 15 - int(max(abs(v - avg) for v in values) * 3))

    strength_score = max(8, 20 - int(abs(strength["强弱分"]) * 2.2))
    if strength["特殊格局提示"]:
        strength_score = min(20, strength_score + 2)

    geju_score = GE_JU_SCORES.get(geju, 8)
    if geju_quality:
        geju_score = max(3, min(15, round(geju_quality["清气分"] / 100 * 15)))
    present_use = sum(1 for wx in use["综合喜用"] if weighted[wx] > 0.8)
    yong_score = min(15, 8 + present_use * 2)

    useful_gods = {"正官", "正印", "正财", "食神"}
    combo_score = 5 + sum(1 for god in gods.values() if god in useful_gods)
    combo_score = min(10, combo_score)

    stability = 10
    stability -= len(xing_chong.get("六冲", [])) * 2
    stability -= len(xing_chong.get("三刑", [])) * 2
    stability -= len(xing_chong.get("六害", []))
    stability -= len(xing_chong.get("相破", []))
    stability += min(2, len(xing_chong.get("六合", [])))
    stability = max(0, min(10, stability))

    shensha = 3 if full_birth else 2
    raw_parts = {
        "五行流通与平衡": balance,
        "日主强弱与承载力": strength_score,
        "格局清纯度与成格程度": geju_score,
        "用神得力程度": yong_score,
        "财官印食组合质量": combo_score,
        "刑冲合害稳定度": stability,
        "神煞辅助": shensha,
    }
    # 资料完整度只影响“能不能精排”的提示，不再参与命局结构打分。
    scale = 100 / 90
    scaled_parts = {key: round(value * scale, 1) for key, value in raw_parts.items()}
    total = round(sum(raw_parts.values()) * scale)
    total = max(0, min(100, total))
    grade = "上上" if total >= 85 else "上吉" if total >= 75 else "中上" if total >= 65 else "中平" if total >= 55 else "中下" if total >= 45 else "下平" if total >= 35 else "下下"
    return {
        "总分": total,
        "等级": grade,
        "评分类型": "完整命盘评分" if full_birth else "四柱结构评分",
        "分项": scaled_parts,
        "原始分项": raw_parts,
        "计分说明": "资料完整度与历法可信度不参与结构评分；分项按剩余90分归一到100分。",
        "说明": "只给四柱时不含精确神煞、大运起运和流年校正。" if not full_birth else "完整生日输入下可进一步结合大运流年。",
    }


def grade_score(total: int) -> str:
    return "上上" if total >= 85 else "上吉" if total >= 75 else "中上" if total >= 65 else "中平" if total >= 55 else "中下" if total >= 45 else "下平" if total >= 35 else "下下"


def bounded_score(value: float) -> int:
    return max(0, min(100, round(value)))


def score_domain(pillars: Dict[str, str], strength: Dict, yong: Dict, xing_chong: Dict, geju_quality: Dict, hehua: Dict) -> Dict:
    gods = ten_gods(pillars)
    visible_gods = [god for key, god in gods.items() if key != "日柱"]
    weighted = weighted_wuxing(pillars)
    favorable = yong["综合喜用"]
    avoid = yong["忌神"]
    useful_present = sum(1 for wx in favorable if weighted[wx] >= 1.0)
    avoid_pressure = sum(1 for wx in avoid if weighted[wx] >= 3.0)
    stability_penalty = len(xing_chong.get("六冲", [])) * 4 + len(xing_chong.get("三刑", [])) * 4 + len(xing_chong.get("六害", [])) * 2 + len(xing_chong.get("相破", [])) * 2
    clear_bonus = (geju_quality["清气分"] - 55) * 0.25

    career = 50 + useful_present * 6 + clear_bonus
    if any(g in visible_gods for g in ["正官", "七杀"]):
        career += 8
    if any(g in visible_gods for g in ["正印", "偏印", "食神", "伤官"]):
        career += 6
    if "官杀混杂" in geju_quality.get("浊气来源", []):
        career -= 8
    career -= stability_penalty * 0.4 + avoid_pressure * 3

    wealth = 50 + useful_present * 5
    if any(g in visible_gods for g in ["正财", "偏财"]):
        wealth += 10
    if any(g in visible_gods for g in ["食神", "伤官"]):
        wealth += 6
    if any(g in visible_gods for g in ["比肩", "劫财"]):
        wealth -= 6
    wealth -= avoid_pressure * 3 + stability_penalty * 0.3

    marriage = 55
    day_branch = pillars["日柱"][1]
    if any(day_branch in item.get("关系", "") for item in xing_chong.get("六冲", [])):
        marriage -= 14
    if any(day_branch in item.get("关系", "") for item in xing_chong.get("六合", [])):
        marriage += 8
    if "官杀混杂" in geju_quality.get("浊气来源", []):
        marriage -= 8
    if any(item["位置"] == "日柱" for item in analyze_kong_wang(pillars)["落空"]):
        marriage -= 8
    marriage += min(8, useful_present * 3) - stability_penalty * 0.5

    health = 58 + useful_present * 4 - avoid_pressure * 5 - stability_penalty * 0.5
    if strength["综合判断"] in {"身弱", "身旺"}:
        health -= 8
    if max(weighted.values()) - min(weighted.values()) >= 5:
        health -= 8

    volatility = 35 + stability_penalty * 4
    muku_for_score = analyze_mu_ku(pillars)
    if result_muku_count := muku_for_score["四墓库支数量"]:
        volatility += result_muku_count * 4
    if muku_for_score["日主墓数量"]:
        volatility += muku_for_score["日主墓数量"] * 5
    if hehua.get("合化明细"):
        volatility += min(8, len(hehua["合化明细"]) * 2)

    domains = {
        "事业": bounded_score(career),
        "财运": bounded_score(wealth),
        "婚姻": bounded_score(marriage),
        "健康倾向": bounded_score(health),
        "变动适配度": bounded_score(volatility),
        "动荡指数": bounded_score(volatility),
    }
    return {
        **domains,
        "说明": {
            "事业": "看官杀、印食、清浊、喜用与稳定度。",
            "财运": "看财星、食伤生财、比劫夺财、喜忌与稳定度。",
            "婚姻": "看日支、官杀/财星、冲合、空亡与稳定度。",
            "健康倾向": "只看五行偏枯与冲刑压力，不作医学判断。",
            "变动适配度": "分数越高代表越适合通过迁移、转型、换环境、资源重组来打开局面，不代表吉凶。",
            "动荡指数": "旧字段别名；同变动适配度。",
        }
    }


def score_luck_realization(result: Dict) -> Dict:
    yn = result.get("大运流年交互", {})
    items = yn.get("年份", [])
    if not items:
        return {
            "当前/指定运年": None,
            "未来区间": None,
            "说明": "未指定流年或未提供完整生日，暂不计算运势兑现评分。",
        }
    values = []
    for item in items:
        base = 55
        if item["喜忌判定"] == "助喜":
            base += 15
        elif item["喜忌判定"] == "喜忌交战":
            base += 3
        elif item["喜忌判定"] == "助忌":
            base -= 12
        base -= len(item.get("流年与原局", {}).get("六冲", [])) * 4
        base -= len(item.get("大运与流年", [])) * 2
        base += min(6, len(item.get("动态合化", [])) * 2)
        values.append(bounded_score(base))
    avg = bounded_score(sum(values) / len(values))
    return {
        "当前/指定运年": values[0] if len(values) == 1 else None,
        "未来区间": avg if len(values) > 1 else None,
        "逐年": [
            {
                "年份": item["年份"],
                "年份显示": item.get("年份显示", str(item["年份"])),
                "流年": item["流年"],
                "分数": values[index],
                "喜忌判定": item["喜忌判定"],
            }
            for index, item in enumerate(items)
        ],
        "说明": "运势兑现分表示指定大运流年对原局喜忌的激活程度，不改变原局结构分。",
    }


def build_score_system(result: Dict) -> Dict:
    structure = result["综合评分"]
    domains = score_domain(
        result["四柱"],
        result["日主强弱"],
        result["用神喜忌"],
        result["刑冲合害"],
        result["格局清浊"],
        result["合化成败"],
    )
    luck = score_luck_realization(result)
    return {
        "原局结构分": {
            "总分": structure["总分"],
            "等级": structure["等级"],
            "分项": structure["分项"],
            "说明": "只代表原局结构顺畅度，不等同人生好坏。",
        },
        "领域评分": domains,
        "运势兑现评分": luck,
        "使用说明": "原局结构分看先天结构；领域评分看不同主题；运势兑现评分看指定大运流年是否补到喜用或引动压力。",
    }


def next_prev_jieqi(birth: datetime, forward: bool) -> Tuple[str, datetime]:
    # Luck-pillar starting age is counted to the next/previous jie (节),
    # not to the nearest zhongqi (中气).
    candidates = jie_candidates_around(birth)
    if forward:
        later = [(n, d) for n, d in candidates if d > birth]
        return min(later, key=lambda x: x[1])
    earlier = [(n, d) for n, d in candidates if d < birth]
    return max(earlier, key=lambda x: x[1])


def add_months(moment: datetime, months: int) -> datetime:
    year = moment.year + (moment.month - 1 + months) // 12
    month = (moment.month - 1 + months) % 12 + 1
    day = min(moment.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return moment.replace(year=year, month=month, day=day)


def split_age_hours(total_hours: int) -> Tuple[int, int, int, int]:
    total_days, hours = divmod(total_hours, 24)
    years = total_days // 360
    remainder = total_days % 360
    months = remainder // 30
    days = remainder % 30
    return years, months, days, hours


def format_age_hours(total_hours: int) -> str:
    years, months, days, hours = split_age_hours(total_hours)
    result = f"{years}岁{months}月"
    if days or hours:
        result += f"{days}天"
    if hours:
        result += f"{hours}时"
    return result


def add_age_hours(birth: datetime, total_hours: int) -> datetime:
    years, months, days, hours = split_age_hours(total_hours)
    moment = add_months(birth, years * 12 + months)
    return moment + timedelta(days=days, hours=hours)


def dayun(pillars: Dict[str, str], birth: datetime, gender: str) -> Dict:
    year_gan = pillars["年柱"][0]
    month_pillar = pillars["月柱"]
    direction = 1 if (GAN_YINYANG[year_gan] == "陽" and gender == "男") or (GAN_YINYANG[year_gan] == "陰" and gender == "女") else -1
    term_name, term_dt = next_prev_jieqi(birth, direction == 1)
    delta_seconds = abs((term_dt - birth).total_seconds())
    # 三天一岁：1实际日=4个月=120起运日；换成小时精度即 1实际小时=5起运日=120起运小时。
    start_age_hours = round(delta_seconds / 3600 * 120)
    start_year, start_month, start_day, start_hour = split_age_hours(start_age_hours)

    idx = LIU_SHI_JIA_ZI.index(month_pillar)
    luck = []
    ten_year_hours = 3600 * 24
    for i in range(8):
        p = LIU_SHI_JIA_ZI[(idx + direction * (i + 1)) % 60]
        age_start_hours = start_age_hours + i * ten_year_hours
        age_end_hours = age_start_hours + ten_year_hours - 1
        start_dt = add_age_hours(birth, age_start_hours)
        end_dt = add_age_hours(birth, age_end_hours)
        luck.append({
            "序": i + 1,
            "干支": p,
            "年龄段": f"{format_age_hours(age_start_hours)}-{format_age_hours(age_end_hours)}",
            "起始年龄月": age_start_hours // (30 * 24),
            "结束年龄月": age_end_hours // (30 * 24),
            "起始年龄日": age_start_hours // 24,
            "结束年龄日": age_end_hours // 24,
            "起始年龄时": age_start_hours,
            "结束年龄时": age_end_hours,
            "起始日期": start_dt.strftime("%Y-%m-%d %H:%M"),
            "结束日期": end_dt.strftime("%Y-%m-%d %H:%M"),
            "起始年份": start_dt.year,
            "结束年份": end_dt.year,
            "顺逆来源": f"年干{year_gan}{GAN_YINYANG[year_gan]}，{gender}命",
        })

    return {
        "顺逆": "顺排" if direction == 1 else "逆排",
        "取节气": term_name,
        "节气日期": term_dt.strftime("%Y-%m-%d %H:%M"),
        "起运": format_age_hours(start_age_hours),
        "起运年": start_year,
        "起运月": start_month,
        "起运日": start_day,
        "起运时": start_hour,
        "说明": "起运按内置节气日期估算；贴近节气交接者建议用专业万年历复核。",
        "大运": luck,
    }


def get_liunian_ganzhi(year: int) -> str:
    return gan_zhi(get_year_ganzhi_at(datetime(year, 2, 4, 12, 0)))


def parse_year_range(value: Optional[str]) -> List[int]:
    if not value:
        return []
    if "-" in value:
        start, end = value.split("-", 1)
        start_i, end_i = int(start), int(end)
        if end_i < start_i:
            raise ValueError("--yun-years 结束年份不能早于开始年份")
        return list(range(start_i, end_i + 1))
    return [int(value)]


def find_dayun_for_year(dayun_info: Dict, year: int) -> Optional[Dict]:
    for item in dayun_info.get("大运", []):
        if item.get("起始年份") <= year <= item.get("结束年份"):
            return item
    return None


def display_age_for_year(result: Dict, year: int) -> Optional[int]:
    birth_year = result.get("出生信息", {}).get("出生年份")
    if birth_year is None:
        return None
    return max(0, year - birth_year)


def format_year_age(year: int, age: Optional[int]) -> str:
    return f"{year}（{age}岁）" if age is not None else str(year)


def branch_pair_relation(source_label: str, source_zhi: str, target_label: str, target_zhi: str) -> List[Dict]:
    relations = []
    if LIUHE_HUA.get(frozenset((source_zhi, target_zhi))):
        relations.append({"关系": f"{source_label}{source_zhi}合{target_label}{target_zhi}", "类型": "六合", "五行": LIUHE_HUA[frozenset((source_zhi, target_zhi))]})
    if {source_zhi, target_zhi} in [set(x) for x in [("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]]:
        relations.append({"关系": f"{source_label}{source_zhi}冲{target_label}{target_zhi}", "类型": "六冲"})
    if {source_zhi, target_zhi} in [set(x) for x in [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")]]:
        relations.append({"关系": f"{source_label}{source_zhi}害{target_label}{target_zhi}", "类型": "六害"})
    if {source_zhi, target_zhi} in [set(x) for x in [("子", "酉"), ("丑", "辰"), ("寅", "亥"), ("卯", "午"), ("巳", "申"), ("未", "戌")]]:
        relations.append({"关系": f"{source_label}{source_zhi}破{target_label}{target_zhi}", "类型": "相破"})
    return relations


def analyze_dynamic_hehua(pillars: Dict[str, str], extras: List[Tuple[str, str]], yong: Dict, xing_chong: Dict) -> List[Dict]:
    items = []
    favorable = yong.get("综合喜用", [])
    base = [(name, pillar) for name, pillar in pillars.items()]
    all_items = base + extras
    for i in range(len(all_items)):
        for j in range(i + 1, len(all_items)):
            name1, p1 = all_items[i]
            name2, p2 = all_items[j]
            gan_hua = TIANGAN_HE.get(frozenset((p1[0], p2[0])))
            if gan_hua and (name1 not in POSITION_NAMES or name2 not in POSITION_NAMES):
                score, reasons, broken = score_transform_power(gan_hua, pillars, [n for n in [name1, name2] if n in POSITION_NAMES], favorable, xing_chong, [])
                items.append({
                    "类型": "动态天干五合",
                    "关系": f"{name1}{p1[0]}与{name2}{p2[0]}合{gan_hua}",
                    "化神": gan_hua,
                    "成化分": score,
                    "状态": classify_hehua(score, broken, gan_hua in favorable),
                    "成败理由": reasons or ["运年见合，需看原局化神力量"],
                })
            zhi_hua = LIUHE_HUA.get(frozenset((p1[1], p2[1])))
            if zhi_hua and (name1 not in POSITION_NAMES or name2 not in POSITION_NAMES):
                score, reasons, broken = score_transform_power(zhi_hua, pillars, [n for n in [name1, name2] if n in POSITION_NAMES], favorable, xing_chong, [p1[1], p2[1]])
                items.append({
                    "类型": "动态地支六合",
                    "关系": f"{name1}{p1[1]}与{name2}{p2[1]}合{zhi_hua}",
                    "化神": zhi_hua,
                    "成化分": score,
                    "状态": classify_hehua(score, broken, zhi_hua in favorable),
                    "成败理由": reasons or ["运年见合，需看原局化神力量"],
                })
    return items


def enrich_muku_analysis(result: Dict) -> None:
    mk = result["墓库"]
    if not mk.get("墓库明细"):
        mk["联动解析"] = ["原局四墓库支不重。"]
        return
    notes = []
    kong_hits = {item["位置"] for item in result["空亡"].get("落空", [])}
    if kong_hits:
        affected = [item for item in mk["墓库明细"] if item["位置"] in kong_hits]
        if affected:
            notes.append("墓库逢空：" + "；".join(f"{item['位置']}{item['地支']}({item['十神库']})" for item in affected) + "，主相关资源/宫位有虚、迟、待填实。")
    tombs = mk.get("日主墓明细", [])
    if tombs:
        notes.append("日主墓：" + "；".join(f"{item['位置']}{item['地支']}" for item in tombs) + "，需结合透干、冲开和运年判断闭藏还是可用。")
    opened = [item for item in mk["墓库明细"] if item["是否被冲开"]]
    if opened:
        notes.append("冲库：" + "；".join(f"{item['位置']}{item['地支']}={item['十神库']}" for item in opened) + "，事件常随变动、迁移、关系或资产调整而起。")
    exposed = [item for item in mk["墓库明细"] if item["是否透出"]]
    if exposed:
        notes.append("透库：" + "；".join(f"{item['位置']}{item['地支']}藏{item['五行库']}透出{''.join(item['对应五行透干'])}" for item in exposed) + "，隐藏资源较容易落地。")
    hehua_hits = []
    for h in result["合化成败"].get("合化明细", []):
        if any(item["地支"] in h["关系"] for item in mk["墓库明细"]):
            hehua_hits.append(h)
    if hehua_hits:
        notes.append("合化牵动墓库：" + "；".join(f"{h['关系']}={h['状态']}" for h in hehua_hits[:3]) + "。")
    if not notes:
        notes.append("墓库未明显逢空、冲开或合化牵动，主要按藏干资源与大运流年引动判断。")
    mk["联动解析"] = notes


def analyze_yun_nian_interaction(result: Dict, years: List[int], focus: str = "general") -> Dict:
    if not years or "大运" not in result:
        return {"年份": [], "综合判断": "未提供完整生日或未指定流年，暂不做大运流年交互。"}
    pillars = result["四柱"]
    day_gan = pillars["日柱"][0]
    favorable = result["用神喜忌"]["综合喜用"]
    avoid = result["用神喜忌"]["忌神"]
    original_branches = [pillars[k][1] for k in POSITION_NAMES]
    year_items = []

    for year in years:
        liunian = get_liunian_ganzhi(year)
        display_age = display_age_for_year(result, year)
        dy = find_dayun_for_year(result["大运"], year) or {}
        dy_pillar = dy.get("干支", "")
        dy_gan, dy_zhi = (dy_pillar[0], dy_pillar[1]) if dy_pillar else ("", "")
        ln_gan, ln_zhi = liunian[0], liunian[1]
        dy_god = get_shi_shen(day_gan, dy_gan) if dy_gan else "未知"
        ln_god = get_shi_shen(day_gan, ln_gan)

        original_rel = XingChongHeHai.analyze(original_branches, liu_nian_zhi=ln_zhi)
        yun_nian_rel = branch_pair_relation("大运", dy_zhi, "流年", ln_zhi) if dy_zhi else []
        wx_support = []
        wx_pressure = []
        for label, gan, zhi in [("大运", dy_gan, dy_zhi), ("流年", ln_gan, ln_zhi)]:
            if not gan:
                continue
            for wx in [GAN_WUXING[gan], ZHI_WUXING[zhi]]:
                if wx in favorable and wx not in wx_support:
                    wx_support.append(wx)
                if wx in avoid and wx not in wx_pressure:
                    wx_pressure.append(wx)
        if wx_support and not wx_pressure:
            tendency = "助喜"
        elif wx_pressure and not wx_support:
            tendency = "助忌"
        elif wx_support and wx_pressure:
            tendency = "喜忌交战"
        else:
            tendency = "平"

        triggered_muku = [m for m in result["墓库"]["墓库明细"] if any(rel.get("类型") == "六冲" and m["地支"] in rel["关系"] for rel in yun_nian_rel)]
        triggered_muku.extend(m for m in result["墓库"]["墓库明细"] if m["地支"] in {dy_zhi, ln_zhi} and m not in triggered_muku)
        kong_filled = [z for z in result["空亡"]["旬空"] if z in {dy_zhi, ln_zhi}]
        extras = [("流年", liunian)]
        if dy_pillar:
            extras.insert(0, ("大运", dy_pillar))
        hehua_dynamic = analyze_dynamic_hehua(pillars, extras, result["用神喜忌"], original_rel)

        notes = []
        if tendency == "助喜":
            notes.append("运年五行偏向喜用，利推进。")
        elif tendency == "助忌":
            notes.append("运年五行偏向忌神，压力与消耗偏重。")
        elif tendency == "喜忌交战":
            notes.append("喜忌同来，机会与压力并见。")
        if original_rel.get("六冲"):
            notes.append("流年冲动原局，主变化、调整或外部压力。")
        if yun_nian_rel:
            notes.append("大运与流年发生支关系，事件感增强。")
        if kong_filled:
            notes.append(f"运年填实/引动空亡：{'、'.join(kong_filled)}。")
        if triggered_muku:
            notes.append("运年引动墓库：" + "、".join(f"{m['地支']}{m['十神库']}" for m in triggered_muku) + "。")

        if focus == "career":
            focus_note = "事业看职位、压力、成果与平台变化。"
            if any(g in [dy_god, ln_god] for g in ["正官", "七杀"]):
                focus_note += " 官杀被引动，责任、考核、职位机会更明显。"
            if any(g in [dy_god, ln_god] for g in ["食神", "伤官"]):
                focus_note += " 食伤被引动，利专业输出、作品和表达。"
        elif focus == "wealth":
            focus_note = "财运看财星、流通与冲库。"
        elif focus == "marriage":
            focus_note = "婚恋看日支、官杀/财星和冲合。"
        elif focus == "health":
            focus_note = "健康只作五行偏枯与冲刑压力提示，不作医学结论。"
        else:
            focus_note = "综合看机会、压力、变动与喜忌。"

        year_items.append({
            "年份": year,
            "岁数": display_age,
            "年份显示": format_year_age(year, display_age),
            "流年": liunian,
            "所属大运": dy,
            "大运十神": dy_god,
            "流年十神": ln_god,
            "流年与原局": {k: original_rel[k] for k in ["六合", "六冲", "三合", "半三合", "三刑", "六害", "相破", "综合判断"]},
            "大运与流年": yun_nian_rel,
            "墓库引动": triggered_muku,
            "空亡引动": kong_filled,
            "动态合化": hehua_dynamic,
            "喜忌判定": tendency,
            "主题": focus,
            "主题判断": focus_note,
            "提示": notes,
        })

    good = [i for i in year_items if i["喜忌判定"] == "助喜"]
    mixed = [i for i in year_items if i["喜忌判定"] == "喜忌交战"]
    hard = [i for i in year_items if i["喜忌判定"] == "助忌"]
    judgment = f"共分析{len(year_items)}年：助喜{len(good)}年，喜忌交战{len(mixed)}年，助忌{len(hard)}年。"
    return {"年份": year_items, "综合判断": judgment}


def analyze(pillars: Dict[str, str], full_birth: bool = False, birth: Optional[datetime] = None, gender: str = "男", yun_years: Optional[List[int]] = None, focus: str = "general") -> Dict:
    xing_chong = XingChongHeHai.analyze([p[1] for p in pillars.values()])
    strength = analyze_strength(pillars, xing_chong)
    gods = ten_gods(pillars)
    use = yongshen(pillars, strength)
    hehua = analyze_he_hua(pillars, strength, xing_chong, use)
    geju_quality = analyze_geju_quality(pillars, gods, strength, use, hehua, xing_chong)
    result = {
        "资料等级": "A/S：完整生日排盘" if full_birth else "B：四柱结构分析",
        "四柱": pillars,
        "藏干": hidden_stems(pillars),
        "十神": gods,
        "五行": {
            "简单统计": simple_wuxing(pillars),
            "加权力量": weighted_wuxing(pillars),
        },
        "日主强弱": strength,
        "格局": get_geju(pillars, gods),
        "用神喜忌": use,
        "墓库": analyze_mu_ku(pillars),
        "空亡": analyze_kong_wang(pillars),
        "十二长生": analyze_chang_sheng(pillars),
        "合化成败": hehua,
        "格局清浊": geju_quality,
        "刑冲合害": {
            k: xing_chong[k] for k in ["六合", "六冲", "三合", "半三合", "三刑", "六害", "相破", "综合判断", "建议"]
        },
        "综合评分": score_chart(pillars, full_birth, geju_quality=geju_quality),
    }
    enrich_muku_analysis(result)
    if birth:
        result["出生信息"] = {
            "公历": birth.strftime("%Y-%m-%d %H:%M"),
            "出生年份": birth.year,
        }
        result["大运"] = dayun(pillars, birth, gender)
        try:
            lunar = gregorian_to_lunar(birth.year, birth.month, birth.day)
            result["农历"] = {
                "年": lunar[0],
                "月": lunar[1],
                "日": lunar[2],
                "闰月": lunar[3],
            }
        except Exception as exc:
            result["农历"] = {"错误": str(exc)}
    if yun_years:
        result["大运流年交互"] = analyze_yun_nian_interaction(result, yun_years, focus=focus)
    else:
        result["大运流年交互"] = {"年份": [], "综合判断": "未指定流年。"}
    result["评分系统"] = build_score_system(result)
    return result


def _join_values(values: List[str]) -> str:
    return "、".join(values) if values else "无"


def _format_wuxing(values: Dict[str, float]) -> str:
    return "  ".join(f"{k}:{v}" for k, v in values.items())


def _format_key_relations(xing_chong: Dict, limit: int = 4) -> str:
    parts = []
    for key in ["六冲", "三刑", "六害", "相破", "六合", "三合", "半三合"]:
        for item in xing_chong.get(key, []):
            relation = item.get("关系", str(item))
            parts.append(f"{key}:{relation}")
            if len(parts) >= limit:
                return "；".join(parts)
    return xing_chong.get("综合判断", "无明显刑冲合害重点")


def _format_muku_summary(result: Dict) -> str:
    mk = result["墓库"]
    if not mk["墓库明细"]:
        return "四墓库支0处"
    wuxing = "、".join(f"{k}{v}处" for k, v in mk.get("五行库统计", {}).items())
    tomb = "、".join(f"{item['位置']}{item['地支']}" for item in mk.get("日主墓明细", [])) or "无"
    return f"四墓库支{mk['四墓库支数量']}处；日主墓：{tomb}；{wuxing}"


def _format_kongwang_summary(result: Dict) -> str:
    kw = result["空亡"]
    if kw["落空"]:
        hits = "、".join(f"{item['位置']}{item['地支']}" for item in kw["落空"])
        return f"旬空{'、'.join(kw['旬空'])}，落空：{hits}"
    return f"旬空{'、'.join(kw['旬空'])}，原局未落空"


def _format_changsheng_summary(result: Dict) -> str:
    cs = result["十二长生"]
    return "、".join(f"{item['位置']}{item['地支']}={item['十二长生']}" for item in cs["长生明细"])


def _format_hehua_summary(result: Dict) -> str:
    hehua = result["合化成败"]
    items = hehua.get("合化明细", [])
    if not items:
        return hehua["综合判断"]
    top = sorted(items, key=lambda item: item["成化分"], reverse=True)[:2]
    return "；".join(f"{item['关系']}={item['状态']}({item['成化分']})" for item in top)


def _format_geju_quality_summary(result: Dict) -> str:
    q = result["格局清浊"]
    return f"{q['格局']}，{q['清浊等级']}（清气分{q['清气分']}）"


def _format_yun_nian_summary(result: Dict) -> str:
    yn = result.get("大运流年交互", {})
    items = yn.get("年份", [])
    if not items:
        return yn.get("综合判断", "未指定流年。")
    if len(items) == 1:
        item = items[0]
        dy = item["所属大运"].get("干支", "未知大运") if item.get("所属大运") else "未知大运"
        return f"{item.get('年份显示', item['年份'])} {item['流年']}，{dy}运，{item['喜忌判定']}；{' '.join(item['提示']) or item['主题判断']}"
    return "；".join(f"{item.get('年份显示', item['年份'])}{item['流年']}={item['喜忌判定']}" for item in items[:6])


def _format_domain_scores(result: Dict) -> str:
    domains = result.get("评分系统", {}).get("领域评分", {})
    keys = ["事业", "财运", "婚姻", "健康倾向", "变动适配度"]
    return "；".join(f"{key}{domains[key]}" for key in keys if key in domains)


def _print_wrapped(text: str, wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    if not text or wrap_width <= 0 or len(text) <= wrap_width:
        print(text)
        return
    leading = len(text) - len(text.lstrip(" "))
    indent = " " * leading
    content = text[leading:]
    wrapped = textwrap.wrap(
        content,
        width=max(20, wrap_width - leading),
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=True,
        break_on_hyphens=False,
    )
    for line in wrapped:
        print(line)


def _print_dayun_brief(result: Dict, count: int = 2, wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    if "大运" not in result:
        return
    dy = result["大运"]
    shown = dy["大运"][:count]
    print("\n【大运】")
    if dy.get("来源") == "问真八字":
        print(f"  {dy['起运']}。{dy.get('交运', '')}")
    else:
        print(f"  {dy['顺逆']}，取{dy['取节气']}，约 {dy['起运']} 起运。")
    _print_wrapped("  " + "；".join(f"{x['年龄段']} {x['干支']}" for x in shown), wrap_width)
    if len(dy["大运"]) > count:
        print("  完整大运请用 --detail full 查看。")


def print_summary(result: Dict, wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    pillars = result["四柱"]
    score = result["综合评分"]
    strength = result["日主强弱"]
    yong = result["用神喜忌"]

    print(f"【资料等级】{result['资料等级']}")
    print(f"【四柱】{'  '.join(pillars.values())}")
    _print_wrapped(f"【核心】日主{strength['日主']}，{result['格局']}，{strength['综合判断']}（强弱分 {strength['强弱分']}），原局结构 {score['总分']}/100 {score['等级']}", wrap_width)
    _print_wrapped(f"【五行】简单：{_format_wuxing(result['五行']['简单统计'])}", wrap_width)
    _print_wrapped(f"【五行】加权：{_format_wuxing(result['五行']['加权力量'])}", wrap_width)
    _print_wrapped(f"【用神】喜用：{_join_values(yong['综合喜用'])}；忌：{_join_values(yong['忌神'])}", wrap_width)
    if yong["扶抑与调候冲突"]:
        _print_wrapped(f"【用神】冲突：{_join_values(yong['扶抑与调候冲突'])}宜适量", wrap_width)
    _print_wrapped(f"【结构】{_format_muku_summary(result)}；{_format_kongwang_summary(result)}", wrap_width)
    _print_wrapped(f"【长生】{_format_changsheng_summary(result)}", wrap_width)
    _print_wrapped(f"【合化/清浊】{_format_hehua_summary(result)}；{_format_geju_quality_summary(result)}", wrap_width)
    _print_wrapped(f"【领域】{_format_domain_scores(result)}", wrap_width)
    _print_wrapped(f"【刑冲】{_format_key_relations(result['刑冲合害'])}", wrap_width)
    if result.get("大运流年交互", {}).get("年份"):
        _print_wrapped(f"【运年】{_format_yun_nian_summary(result)}", wrap_width)
    _print_dayun_brief(result, count=2, wrap_width=wrap_width)


def print_standard(result: Dict, wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    print(f"【资料等级】{result['资料等级']}")
    print("\n【四柱/十神】")
    print("  四柱：" + "  ".join(result["四柱"].values()))
    print("  十神：" + "  ".join(result["十神"].values()))
    print("\n【五行与强弱】")
    print("  简单统计：" + _format_wuxing(result["五行"]["简单统计"]))
    print("  加权力量：" + _format_wuxing(result["五行"]["加权力量"]))
    s = result["日主强弱"]
    print(f"  {s['日主']} 生于 {s['月令']}，月令{s['月令旺衰']}，判断：{s['综合判断']}（强弱分 {s['强弱分']}）")
    if s["特殊格局提示"]:
        print(f"  特殊提示：{s['特殊格局提示']}")

    y = result["用神喜忌"]
    print("\n【格局与用神】")
    print(f"  格局：{result['格局']}")
    _print_wrapped(f"  第一用神：{_join_values(y['第一用神'])}；调候：{_join_values(y['调候用神'])}；通关：{_join_values(y['通关用神'])}", wrap_width)
    _print_wrapped(f"  综合喜用：{_join_values(y['综合喜用'])}；忌神：{_join_values(y['忌神'])}", wrap_width)
    _print_wrapped(f"  {y['取用理由']} {y['调候说明']}", wrap_width)

    print("\n【墓库/空亡/十二长生】")
    _print_wrapped(f"  {_format_muku_summary(result)}；{result['墓库']['综合判断']}", wrap_width)
    if result["墓库"].get("联动解析"):
        _print_wrapped("  联动：" + "；".join(result["墓库"]["联动解析"][:2]), wrap_width)
    _print_wrapped(f"  {_format_kongwang_summary(result)}；{result['空亡']['综合判断']}", wrap_width)
    _print_wrapped(f"  {_format_changsheng_summary(result)}", wrap_width)

    print("\n【合化成败】")
    hehua_items = result["合化成败"]["合化明细"][:5]
    if hehua_items:
        for item in hehua_items:
            _print_wrapped(f"  {item['关系']}（{item['位置']}）：{item['状态']}，成化分{item['成化分']}，化神{item['化神']}", wrap_width)
    else:
        _print_wrapped(f"  {result['合化成败']['综合判断']}", wrap_width)

    print("\n【格局清浊】")
    q = result["格局清浊"]
    _print_wrapped(f"  {q['格局']}：{q['清浊等级']}，清气分{q['清气分']}", wrap_width)
    _print_wrapped(f"  清气：{'；'.join(q['清气来源'])}", wrap_width)
    if q["浊气来源"]:
        _print_wrapped(f"  浊气：{'；'.join(q['浊气来源'])}", wrap_width)
    _print_wrapped(f"  建议：{'；'.join(q['取清建议'])}", wrap_width)

    score = result["综合评分"]
    print("\n【评分】")
    print(f"  原局结构：{score['总分']}/100，{score['等级']}（{score['评分类型']}）")
    _print_wrapped(f"  领域：{_format_domain_scores(result)}", wrap_width)
    luck_score = result["评分系统"]["运势兑现评分"]
    if luck_score["当前/指定运年"] is not None:
        print(f"  运年兑现：{luck_score['当前/指定运年']}/100")
    elif luck_score["未来区间"] is not None:
        print(f"  区间兑现：{luck_score['未来区间']}/100")
    print("\n【刑冲合害】")
    _print_wrapped(f"  {_format_key_relations(result['刑冲合害'], limit=6)}", wrap_width)
    _print_dayun_brief(result, count=4, wrap_width=wrap_width)
    if result.get("大运流年交互", {}).get("年份"):
        print("\n【大运流年交互】")
        for item in result["大运流年交互"]["年份"][:10]:
            dy = item["所属大运"].get("干支", "未知") if item.get("所属大运") else "未知"
            _print_wrapped(f"  {item.get('年份显示', item['年份'])} {item['流年']}：{dy}运，{item['喜忌判定']}，{' '.join(item['提示']) or item['主题判断']}", wrap_width)


def print_full(result: Dict, wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    print(f"【资料等级】{result['资料等级']}")
    print("\n【四柱】")
    print("  " + "  ".join(result["四柱"].values()))
    print("\n【十神】")
    print("  " + "  ".join(result["十神"].values()))
    print("\n【五行】")
    print("  简单统计：" + "  ".join(f"{k}:{v}" for k, v in result["五行"]["简单统计"].items()))
    print("  加权力量：" + "  ".join(f"{k}:{v}" for k, v in result["五行"]["加权力量"].items()))
    s = result["日主强弱"]
    print("\n【日主强弱】")
    print(f"  {s['日主']} 生于 {s['月令']}，月令{s['月令旺衰']}，判断：{s['综合判断']}（强弱分 {s['强弱分']}）")
    if s["特殊格局提示"]:
        print(f"  特殊提示：{s['特殊格局提示']}")
    print("\n【格局】")
    print(f"  {result['格局']}")
    y = result["用神喜忌"]
    print("\n【用神喜忌】")
    print(f"  第一用神：{'、'.join(y['第一用神']) or '无'}")
    print(f"  调候用神：{'、'.join(y['调候用神']) or '无'}")
    print(f"  通关用神：{'、'.join(y['通关用神']) or '无'}")
    print(f"  综合喜用：{'、'.join(y['综合喜用']) or '无'}")
    print(f"  忌神：{'、'.join(y['忌神']) or '无'}")
    if y["扶抑与调候冲突"]:
        _print_wrapped(f"  扶抑与调候冲突：{'、'.join(y['扶抑与调候冲突'])}宜适量，不宜过旺", wrap_width)
    _print_wrapped(f"  {y['取用理由']} {y['调候说明']}", wrap_width)
    print("\n【墓库】")
    mk = result["墓库"]
    print(f"  四墓库支：{mk['四墓库支数量']}处；日主墓：{mk['日主墓数量']}处")
    _print_wrapped(f"  五行库统计：{mk.get('五行库统计', {})}", wrap_width)
    _print_wrapped(f"  十神库统计：{mk.get('十神库统计', {})}", wrap_width)
    if mk["墓库明细"]:
        _print_wrapped("  " + "；".join(
            f"{item['位置']}{item['地支']}={item['层级']}，{item['五行库']}/{item['十神库']}，长生{item['十二长生']}，{item['状态']}"
            for item in mk["墓库明细"]
        ), wrap_width)
    _print_wrapped(f"  {mk['综合判断']}", wrap_width)
    if mk.get("联动解析"):
        _print_wrapped("  联动解析：" + "；".join(mk["联动解析"]), wrap_width)
    print("\n【空亡】")
    kw = result["空亡"]
    print(f"  日柱{kw['日柱']}，旬空：{'、'.join(kw['旬空'])}")
    if kw["落空"]:
        _print_wrapped("  落空：" + "；".join(f"{item['位置']}{item['地支']}({item['十神']})" for item in kw["落空"]), wrap_width)
    _print_wrapped(f"  {kw['综合判断']}", wrap_width)
    print("\n【十二长生】")
    cs = result["十二长生"]
    _print_wrapped("  " + "；".join(
        f"{item['位置']}{item['地支']}={item['十二长生']}"
        for item in cs["长生明细"]
    ), wrap_width)
    score = result["综合评分"]
    print("\n【合化成败】")
    hehua = result["合化成败"]
    if hehua["合化明细"]:
        for item in hehua["合化明细"]:
            _print_wrapped(f"  {item['类型']} {item['关系']}（{item['位置']}）：{item['状态']}，成化分{item['成化分']}，化神{item['化神']}；理由：{'、'.join(item['成败理由'])}", wrap_width)
    else:
        _print_wrapped(f"  {hehua['综合判断']}", wrap_width)

    print("\n【格局清浊】")
    q = result["格局清浊"]
    _print_wrapped(f"  {q['格局']}：{q['清浊等级']}，清气分{q['清气分']}", wrap_width)
    _print_wrapped(f"  清气来源：{'；'.join(q['清气来源'])}", wrap_width)
    _print_wrapped(f"  浊气来源：{'；'.join(q['浊气来源']) or '无明显浊气'}", wrap_width)
    _print_wrapped(f"  成格阻点：{'；'.join(q['成格阻点']) or '无明显阻点'}", wrap_width)
    _print_wrapped(f"  取清建议：{'；'.join(q['取清建议'])}", wrap_width)

    print("\n【评分系统】")
    scoring = result["评分系统"]
    print(f"  原局结构：{scoring['原局结构分']['总分']}/100，{scoring['原局结构分']['等级']}（{score['评分类型']}）")
    _print_wrapped("  结构分项：" + "；".join(f"{k}:{v}" for k, v in scoring["原局结构分"]["分项"].items()), wrap_width)
    _print_wrapped("  领域评分：" + _format_domain_scores(result), wrap_width)
    luck_score = scoring["运势兑现评分"]
    if luck_score["当前/指定运年"] is not None:
        print(f"  运年兑现：{luck_score['当前/指定运年']}/100")
    if luck_score["未来区间"] is not None:
        print(f"  区间兑现：{luck_score['未来区间']}/100")
    if luck_score.get("逐年"):
        _print_wrapped("  逐年兑现：" + "；".join(f"{x['年份显示']}{x['流年']}={x['分数']}" for x in luck_score["逐年"]), wrap_width)
    print("\n【刑冲合害】")
    _print_wrapped(f"  {result['刑冲合害']['综合判断']}", wrap_width)
    if "大运" in result:
        dy = result["大运"]
        print("\n【大运】")
        if dy.get("来源") == "问真八字":
            print(f"  {dy['起运']}。{dy.get('交运', '')}")
        else:
            print(f"  {dy['顺逆']}，取{dy['取节气']}，约 {dy['起运']} 起运。")
        _print_wrapped("  " + "；".join(f"{x['年龄段']} {x['干支']}" for x in dy["大运"]), wrap_width)
        _print_wrapped(f"  {dy['说明']}", wrap_width)
    if result.get("大运流年交互", {}).get("年份"):
        print("\n【大运流年交互】")
        for item in result["大运流年交互"]["年份"]:
            dy = item["所属大运"].get("干支", "未知") if item.get("所属大运") else "未知"
            _print_wrapped(f"  {item.get('年份显示', item['年份'])} {item['流年']}：所属{dy}运（大运十神{item['大运十神']}，流年十神{item['流年十神']}），{item['喜忌判定']}；{item['主题判断']}", wrap_width)
            if item["大运与流年"]:
                _print_wrapped("    运年关系：" + "；".join(rel["关系"] for rel in item["大运与流年"]), wrap_width)
            if item["提示"]:
                _print_wrapped("    提示：" + " ".join(item["提示"]), wrap_width)


def ai_interpret(result: Dict, api_key: str, model: str = "gpt-4o-mini", focus: str = "general") -> str:
    # Integrating OpenAI GPT-4 for expert-level narrative synthesis
    """Send chart result to OpenAI and return natural-language interpretation."""
    focus_map = {
        "career": "重点分析事业运势",
        "wealth": "重点分析财运",
        "marriage": "重点分析婚恋感情",
        "health": "重点分析健康运势",
        "general": "综合分析命盘",
    }
    focus_hint = focus_map.get(focus, "综合分析命盘")

    # Build a concise summary dict to keep the prompt compact
    summary: Dict = {}
    for key in ["四柱", "日主强弱", "格局", "用神喜忌", "评分系统", "综合评分",
                "墓库", "空亡", "合化成败", "格局清浊", "刑冲合害", "大运"]:
        if key in result:
            summary[key] = result[key]
    if "大运流年交互" in result:
        summary["大运流年交互"] = result["大运流年交互"]

    system_prompt = (
        "你是一位专业的中国传统八字命理师，擅长用清晰、平实的语言解读命盘。"
        "不使用恐吓式断语，多用'倾向、较容易、需注意'等表达。"
        "回答使用中文，结构清晰，分段说明。"
    )
    user_prompt = (
        f"以下是八字排盘的结构化分析结果，请{focus_hint}，"
        "输出易读的命理解读，包括：日主强弱与格局、用神喜忌、大运走势与当前运势建议。"
        "如有流年数据请一并解读。\n\n"
        f"```json\n{json.dumps(summary, ensure_ascii=False, indent=2)}\n```"
    )

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API 错误 {e.code}：{body}") from e


def print_text(result: Dict, detail: str = "summary", wrap_width: int = DEFAULT_WRAP_WIDTH) -> None:
    if detail == "full":
        print_full(result, wrap_width=wrap_width)
    elif detail == "standard":
        print_standard(result, wrap_width=wrap_width)
    else:
        print_summary(result, wrap_width=wrap_width)


def main() -> int:
    parser = argparse.ArgumentParser(description="融合版八字排盘与评分工具")
    parser.add_argument("--date", "-d", help="公历出生日期 YYYY-MM-DD")
    parser.add_argument("--time", "-t", help="出生时间 HH:MM 或小时")
    parser.add_argument("--hour", "-H", type=int, help="出生小时 0-23")
    parser.add_argument("--gender", "-g", choices=["男", "女"], default="男")
    parser.add_argument("--place", default="", help="出生地，仅记录展示")
    parser.add_argument("--pillars", "-p", help="直接输入四柱，如：乙亥 壬午 己巳 甲子")
    parser.add_argument("--score-only", action="store_true", help="只输出综合评分摘要")
    parser.add_argument("--json", "-j", action="store_true", help="输出 JSON")
    parser.add_argument("--detail", choices=["summary", "standard", "full"], default="summary", help="文本输出详细程度：summary 默认短版，standard 中版，full 完整版")
    parser.add_argument("--wrap-width", type=int, default=DEFAULT_WRAP_WIDTH, help="文本输出自动换行宽度；设为 0 可关闭脚本级换行")
    parser.add_argument("--liu-nian", type=int, help="指定流年年份，如 2026")
    parser.add_argument("--yun-years", help="指定流年区间，如 2026-2035；也可只填单年")
    parser.add_argument("--focus", choices=["career", "wealth", "marriage", "health", "general"], default="general", help="大运流年交互主题")
    parser.add_argument("--wenzhen", action="store_true", help="调用问真八字公开接口反查候选生日或校准起运大运")
    parser.add_argument("--candidate-index", type=int, help="问真四柱反查候选序号，1 开始")
    parser.add_argument("--ai", action="store_true", help="启用 OpenAI 解读（需要 OPENAI_API_KEY 或 --ai-key）")
    parser.add_argument("--ai-key", default="", help="OpenAI API Key（也可设置环境变量 OPENAI_API_KEY）")
    parser.add_argument("--ai-model", default="gpt-4o-mini", help="OpenAI 模型，默认 gpt-4o-mini")
    args = parser.parse_args()

    birth = None
    wenzhen_data = None
    if args.pillars:
        pillars = parse_pillars(args.pillars)
        full_birth = False
        if args.wenzhen:
            try:
                candidates = wenzhen_birth_candidates(pillars)
            except Exception as exc:
                parser.error(f"问真四柱反查失败：{exc}")
            if not args.candidate_index:
                print_wenzhen_candidates(candidates)
                return 0
            if args.candidate_index < 1 or args.candidate_index > len(candidates):
                parser.error(f"--candidate-index 超出范围：共有 {len(candidates)} 个候选")
            birth = parse_wenzhen_datetime(candidates[args.candidate_index - 1])
            try:
                wenzhen_data = wenzhen_base_chart(birth, args.gender)
            except Exception as exc:
                parser.error(f"问真排盘失败：{exc}")
            pillars = wenzhen_pillars(wenzhen_data)
            full_birth = True
    else:
        if not args.date:
            parser.error("请提供 --date 或 --pillars")
        hour = args.hour
        minute = 0
        if args.time:
            hour, minute = parse_time(args.time)
        if hour is None:
            parser.error("完整排盘请提供 --time 或 --hour")
        day = datetime.strptime(args.date, "%Y-%m-%d").date()
        birth = datetime(day.year, day.month, day.day, hour, minute)
        pillars = pillars_from_datetime(birth)
        full_birth = True
        if args.wenzhen:
            try:
                wenzhen_data = wenzhen_base_chart(birth, args.gender)
                pillars = wenzhen_pillars(wenzhen_data)
            except Exception as exc:
                parser.error(f"问真排盘失败：{exc}")

    yun_years = []
    if args.liu_nian:
        yun_years.append(args.liu_nian)
    yun_years.extend(year for year in parse_year_range(args.yun_years) if year not in yun_years)

    result = analyze(pillars, full_birth=full_birth, birth=birth, gender=args.gender, yun_years=yun_years, focus=args.focus)
    if wenzhen_data and birth:
        attach_wenzhen_result(result, wenzhen_data, birth)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.score_only:
        score = result["综合评分"]
        print(f"{score['总分']}/100 {score['等级']}（{score['评分类型']}）")
        print(json.dumps(score["分项"], ensure_ascii=False))
    else:
        print_text(result, detail=args.detail, wrap_width=args.wrap_width)

    if args.ai:
        api_key = args.ai_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("\n[AI 解读] 未找到 API Key，请设置环境变量 OPENAI_API_KEY 或使用 --ai-key 传入。", file=sys.stderr)
            return 1
        print("\n" + "=" * 72)
        print("【AI 命理解读】")
        print("=" * 72)
        try:
            interpretation = ai_interpret(result, api_key=api_key, model=args.ai_model, focus=args.focus)
            print(interpretation)
        except Exception as exc:
            print(f"[AI 解读失败] {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
