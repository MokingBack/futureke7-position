#!/usr/bin/env python3
"""多空行为连续性评定规则。

只基于公开持仓增减做客观描述，主语为多头席位 / 空头席位 / 外资背景席位，
不推断席位背后的客户身份（机构 / 家人 / 散户等）。

口径：
- 阈值 TH=300 手，单日增减未过阈值记为“变动不大”，不展示动作标签；
- 延续 / 转向：昨日同为明确方向才标“继续”，昨日反向才标“转”，昨日中性不冠前缀；
- 连续天数：往回数同向天数，封顶 3 日，仅连续 >=2 日才标注；
- 近 5 日累计：最近 5 个交易日同方向增减之和；
- 强弱对照：两侧同向增持时，比哪边合计更大。
"""
import os, json, glob
from collections import defaultdict

TH = 300
STREAK_MAX = 3
WIN = 5

AGG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agg')

# 用语：多头侧 / 空头侧
LONG_UP, LONG_DN = '加多', '减多'
SHORT_UP, SHORT_DN = '加空', '减空'


def side_eval(cur, prev, hist, field, up, dn):
    """评定一侧（多头或空头）的当日动作、延续/转向、连续天数。

    hist: 前序交易日同品种同组的 {lp, sp} 列表，按时间升序。
    返回 dict: base, cont, streak。
    """
    if cur >= TH:
        base = up
    elif cur <= -TH:
        base = dn
    else:
        base = None

    cont = None
    if base and prev is not None:
        if base == up:
            if prev <= -TH:
                cont = '转' + up
            elif prev >= TH:
                cont = '继续' + up
        else:
            if prev >= TH:
                cont = '转' + dn
            elif prev <= -TH:
                cont = '继续' + dn

    streak = 0
    if base:
        sign = 1 if base == up else -1
        for h in reversed(hist):
            v = h[field]
            if (v > 0) if sign > 0 else (v < 0):
                streak += 1
            else:
                break
        streak = min(streak, STREAK_MAX)

    return {'base': base, 'cont': cont, 'streak': streak}


def evaluate(today, hist, sym, group):
    """评定某品种某组。

    today: 当日某组聚合 {sym: {lp, sp}}
    hist: 前序交易日日期级聚合列表（升序），每项 {group: {sym: {lp, sp}}}
    返回评定 dict；品种当日无数据返回 None。
    """
    t = today.get(sym)
    if not t:
        return None
    cur_lp, cur_sp = t['lp'], t['sp']

    prev = hist[-1][group].get(sym) if hist else None
    prev_lp = prev['lp'] if prev else None
    prev_sp = prev['sp'] if prev else None

    long_hist = [h[group].get(sym, {'lp': 0, 'sp': 0}) for h in hist]
    short_hist = long_hist  # 同一份历史，两侧共用

    long = side_eval(cur_lp, prev_lp, long_hist, 'lp', LONG_UP, LONG_DN)
    short = side_eval(cur_sp, prev_sp, short_hist, 'sp', SHORT_UP, SHORT_DN)

    # 近 5 日累计（含今日）
    prev_win = hist[-(WIN - 1):]
    cum_lp = today.get(sym, {'lp': 0})['lp'] + sum(h[group].get(sym, {'lp': 0})['lp'] for h in prev_win)
    cum_sp = today.get(sym, {'sp': 0})['sp'] + sum(h[group].get(sym, {'sp': 0})['sp'] for h in prev_win)

    # 强弱对照
    strong = ''
    if cur_lp > 0 and cur_sp > 0:
        strong = '多头占优' if cur_lp > cur_sp else '空头占优'
    elif cur_lp < 0 and cur_sp < 0:
        strong = '多空双减'

    return {
        'lp': cur_lp, 'sp': cur_sp,
        'long': long, 'short': short,
        'cum_lp': cum_lp, 'cum_sp': cum_sp,
        'strong': strong,
    }


def load_history():
    """读取 agg 目录全部历史聚合，返回 (dates, history)。

    history: 升序 list，每项 {group: {sym: {lp, sp}}}
    """
    dates = []
    history = []
    for fp in sorted(glob.glob(os.path.join(AGG_DIR, '*.json'))):
        d = os.path.basename(fp)[:-5]
        try:
            history.append(json.load(open(fp)))
            dates.append(d)
        except Exception as e:
            print(f"  读取 {fp} 失败: {e}")
    return dates, history


def save_agg(date, today):
    """落一份轻量当日聚合（all / foreign），供跨日连续性使用。"""
    os.makedirs(AGG_DIR, exist_ok=True)
    out = {'date': date, 'all': today.get('all', {}), 'foreign': today.get('foreign', {})}
    with open(os.path.join(AGG_DIR, f'{date}.json'), 'w') as f:
        json.dump(out, f, ensure_ascii=False)
