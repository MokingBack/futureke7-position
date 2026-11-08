#!/usr/bin/env python3
"""用蓝图标注反推席位分类"""
import json, glob, os
from collections import defaultdict, Counter

BASE = '/home/user/Doubao/chats/38441425997216770/trade-blueprint-data'
bp = json.load(open(f'{BASE}/blueprint_raw_2026.json'))

# 品种中文->代码映射（蓝图里出现的品种）
SYM_MAP = {
    '白银':'AG','黄金':'AU','沪铜':'CU','沪铝':'AL','沪锌':'ZN','沪铅':'PB','沪镍':'NI','沪锡':'SN',
    '螺纹钢':'RB','热卷':'HC','铁矿石':'I','焦炭':'J','焦煤':'JM','锰硅':'SM','硅铁':'SF',
    '玻璃':'FG','纯碱':'SA','烧碱':'SH','氧化铝':'AO','纸浆':'SP','橡胶':'RU','20号胶':'NR',
    '合成橡胶':'BR','天然橡胶':'RU','丁二烯橡胶':'BR','橡胶':'RU',
    '豆一':'A','豆二':'B','豆粕':'M','豆油':'Y','菜粕':'RM','菜油':'OI','棕榈油':'P',
    '玉米':'C','淀粉':'CS','鸡蛋':'JD','生猪':'LH','苹果':'AP','红枣':'CJ','花生':'PK',
    '白糖':'SR','棉花':'CF','棉纱':'CY','尿素':'UR','纯碱':'SA','动力煤':'ZC',
    '甲醇':'MA','乙二醇':'EG','PVC':'V','塑料':'L','PP':'PP','苯乙烯':'EB','PTA':'TA',
    '短纤':'PF','瓶片':'PR','对二甲苯':'PX','PX':'PX','EB':'EB','LPG':'PG','液化气':'PG',
    '燃料油':'FU','沥青':'BU','低硫燃油':'LU','石油沥青':'BU',
    '工业硅':'SI','多晶硅':'PS','碳酸锂':'LC','不锈钢':'SS','欧线':'EC',
    '中证1000':'IM','中证500':'IC','沪深300':'IF','上证50':'IH',
    '沪银':'AG','沪金':'AU','沪铜':'CU','沪铝':'AL','沪锌':'ZN','沪铅':'PB','沪镍':'NI','沪锡':'SN',
    '沪锡':'SN','沪铜':'CU',
}

def norm_name(n):
    if not n: return ''
    n = n.replace('（代客）','').replace('(代客)','').strip()
    # 合并简称/全称
    alias = {
        '国泰君安':'国泰君安期货','中信建投':'中信建投期货','申银万国':'申银万国期货',
        '方正中期':'方正中期期货','中金财富':'中金财富期货','高盛期货(深圳)':'高盛期货',
    }
    return alias.get(n, n)

def load_day(date):
    fp = f'{BASE}/raw/{date}.json'
    if not os.path.exists(fp): return []
    return json.load(open(fp))

# 按品种汇总会员持仓变动
def agg_by_member(rows, sym_code):
    """返回 {member: {lp: 总多增, sp: 总空增, long: 总多仓, short: 总空仓}}"""
    agg = defaultdict(lambda: {'lp':0,'sp':0,'long':0,'short':0})
    for r in rows:
        if r['TRADE_CODE'] != sym_code: continue
        m = norm_name(r.get('ORG_NAME_ABBR_NEW'))
        if not m: continue
        agg[m]['lp'] += r.get('LP_CHANGE') or 0
        agg[m]['sp'] += r.get('SP_CHANGE') or 0
        agg[m]['long'] += r.get('LONG_POSITION') or 0
        agg[m]['short'] += r.get('SHORT_POSITION') or 0
    return agg

# 反推：对每条蓝图标注，找出贡献最大的会员
# 收集 group -> member -> 出现次数
votes = defaultdict(Counter)
examples = []

for day in bp['days']:
    date = day['date']
    rows = load_day(date)
    if not rows: continue
    for gkey, gname in [('retail','家人'),('inst','机构'),('foreign','外资')]:
        for item in day[gkey]:
            sym_cn = item['sym']
            act = item['act']
            # 解析品种：可能是"A和B"或"A、B"
            parts = sym_cn.replace('和','、').split('、')
            for part in parts:
                part = part.strip()
                code = SYM_MAP.get(part)
                if not code: continue
                agg = agg_by_member(rows, code)
                if not agg: continue
                # 方向判断
                is_long = act in ('加多','做多','抄底','反手做多','平多做空','平空做多')
                is_short = act in ('加空','做空','反手做空')
                if not (is_long or is_short): continue
                # 按净方向排序
                scored = []
                for m, v in agg.items():
                    net = v['lp'] - v['sp']  # 净多增
                    if is_long:
                        scored.append((net, m, v))
                    else:
                        scored.append((-net, m, v))  # 空头方向，净空增=-net
                scored.sort(reverse=True)
                # 取前5家贡献最大的
                for val, m, v in scored[:5]:
                    if abs(val) < 100: continue  # 阈值
                    votes[gname][m] += 1
                examples.append({
                    'date':date,'group':gname,'act':act,'sym':part,
                    'top3':[(round(v,0),m) for v,m,_ in scored[:3]]
                })

print("=== 家人组核心会员（出现次数）===")
for m, c in votes['家人'].most_common(20):
    print(f"  {m:14s} {c}")

print("\n=== 机构组核心会员 ===")
for m, c in votes['机构'].most_common(25):
    print(f"  {m:14s} {c}")

print("\n=== 外资组核心会员 ===")
for m, c in votes['外资'].most_common(15):
    print(f"  {m:14s} {c}")

# 保存例子
with open(f'{BASE}/reverse_examples.json','w') as f:
    json.dump(examples, f, ensure_ascii=False, indent=2)
