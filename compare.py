#!/usr/bin/env python3
"""对照v2：单边仓位变化（不是净仓位）"""
import json, os, glob
from collections import defaultdict

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

# 外资：QFII背景
FOREIGN = {
    '高盛期货','高盛期货(深圳)','摩根大通','摩根大通期货','瑞银期货',
    '摩根士丹利期货(中国)','上海东亚','东亚期货','中银国际','中银国际期货','中银期货',
}

# 机构：投票top30
INST = {
    '中信期货','东证期货','国泰君安','国泰君安期货','华泰期货','瑞达期货','永安期货',
    '海通期货','银河期货','中金财富','中金财富期货','广发期货','浙商期货','东吴期货',
    '国投期货','国投安信','中信建投','中信建投期货','南华期货','中粮期货','招商期货',
    '中辉期货','创元期货','国信期货','五矿期货','平安期货','中泰期货','宏源期货',
    '方正中期','方正中期期货','光大期货','申银万国','申银万国期货','一德期货',
    '大地期货','东海期货','海证期货','中财期货','上海中财','混沌天成','金瑞期货','兴证期货',
}

def norm(n):
    if not n: return ''
    return n.replace('（代客）','').replace('(代客)','').strip()

def group_of(name):
    n = norm(name)
    if n in FOREIGN: return '外资'
    if n in INST: return '机构'
    return '家人'

# 只跑数据完整日期
GOOD_DATES = set()
for fp in glob.glob(f'{BASE}/raw/*.json'):
    rows = json.load(open(fp))
    if len(rows) > 5000:
        GOOD_DATES.add(os.path.basename(fp).replace('.json',''))

results = []
for day in bp['days']:
    date = day['date']
    if date not in GOOD_DATES: continue
    rows = json.load(open(f'{BASE}/raw/{date}.json'))
    for gkey, gname in [('retail','家人'),('inst','机构'),('foreign','外资')]:
        for item in day[gkey]:
            act = item['act']
            parts = item['sym'].replace('和','、').split('、')
            for part in parts:
                code = SYM_MAP.get(part.strip())
                if not code: continue
                # 按组汇总LP和SP
                glp = defaultdict(int); gsp = defaultdict(int)
                for r in rows:
                    if r['TRADE_CODE'] != code: continue
                    g = group_of(r.get('ORG_NAME_ABBR_NEW'))
                    glp[g] += r.get('LP_CHANGE') or 0
                    gsp[g] += r.get('SP_CHANGE') or 0
                # 判断蓝图说的动作方向
                # 加多/做多/抄底 = LP↑ ; 减多/平多 = LP↓
                # 加空/做空 = SP↑ ; 减空/平空 = SP↓
                if '加多' in act or '做多' in act or '抄底' in act:
                    actual = glp[gname]
                    ok = actual > 100  # 显著正
                    direction = 'LP'
                elif '减多' in act or '平多' in act:
                    actual = glp[gname]
                    ok = actual < -100
                    direction = 'LP'
                elif '加空' in act or '做空' in act:
                    actual = gsp[gname]
                    ok = actual > 100
                    direction = 'SP'
                elif '减空' in act or '平空' in act:
                    actual = gsp[gname]
                    ok = actual < -100
                    direction = 'SP'
                else:
                    continue
                results.append({
                    'date':date,'group':gname,'act':act,'sym':part.strip(),
                    '实际值':round(actual),'对':ok,'方向':direction,
                    '家LP':round(glp['家人']),'家SP':round(gsp['家人']),
                    '机LP':round(glp['机构']),'机SP':round(gsp['机构']),
                    '外LP':round(glp['外资']),'外SP':round(gsp['外资']),
                })

total = len(results)
right = sum(1 for r in results if r['对'])
print(f"总条目: {total}, 对: {right}, 准确率: {right/total*100:.1f}%")
for g in ['家人','机构','外资']:
    sub = [r for r in results if r['group']==g]
    ok = sum(1 for r in sub if r['对'])
    print(f"  {g}: {ok}/{len(sub)} = {ok/len(sub)*100:.1f}%")

print("\n=== 错配样例 ===")
wrong = [r for r in results if not r['对']]
for r in wrong[:25]:
    print(f"  {r['date']} {r['group']:3s} {r['act']:6s}{r['sym']:5s} [{r['方向']}={r['实际值']:+6.0f}] 家L{r['家LP']:+6.0f}S{r['家SP']:+6.0f} 机L{r['机LP']:+6.0f}S{r['机SP']:+6.0f} 外L{r['外LP']:+6.0f}S{r['外SP']:+6.0f}")
