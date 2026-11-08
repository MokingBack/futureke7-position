#!/usr/bin/env python3
"""反推：从机构栏条目里，找出真正的机构核心公司"""
import json, os, glob
from collections import defaultdict, Counter

BASE = '/home/user/Doubao/chats/38441425997216770/trade-blueprint-data'
bp = json.load(open(f'{BASE}/blueprint_raw_2026.json'))

SYM_MAP = {
    '白银':'AG','黄金':'AU','沪铜':'CU','沪铝':'AL','沪锌':'ZN','沪铅':'PB','沪镍':'NI','沪锡':'SN',
    '螺纹钢':'RB','热卷':'HC','铁矿石':'I','焦炭':'J','焦煤':'JM','锰硅':'SM','硅铁':'SF',
    '玻璃':'FG','纯碱':'SA','烧碱':'SH','氧化铝':'AO','纸浆':'SP','橡胶':'RU','20号胶':'NR',
    '合成橡胶':'BR','天然橡胶':'RU','丁二烯橡胶':'BR',
    '豆一':'A','豆二':'B','豆粕':'M','豆油':'Y','菜粕':'RM','菜油':'OI','棕榈油':'P',
    '玉米':'C','淀粉':'CS','鸡蛋':'JD','生猪':'LH','苹果':'AP','红枣':'CJ','花生':'PK',
    '白糖':'SR','棉花':'CF','棉纱':'CY','尿素':'UR','动力煤':'ZC',
    '甲醇':'MA','乙二醇':'EG','PVC':'V','塑料':'L','PP':'PP','苯乙烯':'EB','PTA':'TA',
    '短纤':'PF','瓶片':'PR','对二甲苯':'PX','LPG':'PG','液化气':'PG',
    '燃料油':'FU','沥青':'BU','低硫燃油':'LU','石油沥青':'BU',
    '工业硅':'SI','多晶硅':'PS','碳酸锂':'LC','不锈钢':'SS','欧线':'EC',
    '中证1000':'IM','中证500':'IC','沪深300':'IF','上证50':'IH',
}

FOREIGN = {
    '高盛期货','高盛期货(深圳)','摩根大通','摩根大通期货','瑞银期货',
    '摩根士丹利期货(中国)','上海东亚','东亚期货','中银国际','中银国际期货','中银期货',
}

GOOD_DATES = set()
for fp in glob.glob(f'{BASE}/raw/*.json'):
    rows = json.load(open(fp))
    if len(rows) > 5000:
        GOOD_DATES.add(os.path.basename(fp).replace('.json',''))

# 投票：对每个机构条目，找方向一致的top贡献者
votes = Counter()
total_items = 0

for day in bp['days']:
    date = day['date']
    if date not in GOOD_DATES: continue
    rows = json.load(open(f'{BASE}/raw/{date}.json'))
    for item in day['inst']:
        act = item['act']
        parts = item['sym'].replace('和','、').split('、')
        for part in parts:
            code = SYM_MAP.get(part.strip())
            if not code: continue
            # 选LP还是SP
            if any(k in act for k in ['加多','做多','抄底']):
                field = 'LP_CHANGE'; direction = 1
            elif any(k in act for k in ['减多','平多']):
                field = 'LP_CHANGE'; direction = -1
            elif any(k in act for k in ['加空','做空']):
                field = 'SP_CHANGE'; direction = 1
            elif any(k in act for k in ['减空','平空']):
                field = 'SP_CHANGE'; direction = -1
            else: continue
            # 汇总每个公司
            per = defaultdict(float)
            for r in rows:
                if r['TRADE_CODE'] != code: continue
                n = r.get('ORG_NAME_ABBR_NEW','')
                if n in FOREIGN: continue
                per[n] += r.get(field) or 0
            # 方向一致的top
            scored = sorted(per.items(), key=lambda x: -x[1]*direction)
            top = [(n, v*direction) for n,v in scored[:8] if v*direction > 200]
            for n, v in top:
                votes[n] += 1
            total_items += 1

print(f"机构条目数: {total_items}")
print("\n=== 在机构方向上高频出现的公司 ===")
for n, c in votes.most_common(40):
    print(f"  {n:16s} {c}")

# 同样跑家人
print("\n\n=== 反推家人组 ===")
votes2 = Counter()
for day in bp['days']:
    date = day['date']
    if date not in GOOD_DATES: continue
    rows = json.load(open(f'{BASE}/raw/{date}.json'))
    for item in day['retail']:
        act = item['act']
        parts = item['sym'].replace('和','、').split('、')
        for part in parts:
            code = SYM_MAP.get(part.strip())
            if not code: continue
            if any(k in act for k in ['加多','做多','抄底']):
                field = 'LP_CHANGE'; direction = 1
            elif any(k in act for k in ['减多','平多']):
                field = 'LP_CHANGE'; direction = -1
            elif any(k in act for k in ['加空','做空']):
                field = 'SP_CHANGE'; direction = 1
            elif any(k in act for k in ['减空','平空']):
                field = 'SP_CHANGE'; direction = -1
            else: continue
            per = defaultdict(float)
            for r in rows:
                if r['TRADE_CODE'] != code: continue
                n = r.get('ORG_NAME_ABBR_NEW','')
                if n in FOREIGN: continue
                per[n] += r.get(field) or 0
            scored = sorted(per.items(), key=lambda x: -x[1]*direction)
            top = [(n, v*direction) for n,v in scored[:8] if v*direction > 200]
            for n, v in top:
                votes2[n] += 1

for n, c in votes2.most_common(40):
    print(f"  {n:16s} {c}")
