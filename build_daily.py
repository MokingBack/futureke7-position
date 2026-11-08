#!/usr/bin/env python3
"""每日生成蓝图HTML"""
import json, os, sys, requests
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(f'{BASE}/classify.json'))

FOREIGN = set(CFG['foreign'])
INST = set(CFG['inst'])

SYM_NAME = {
    'AG':'白银','AU':'黄金','CU':'沪铜','AL':'沪铝','ZN':'沪锌','PB':'沪铅','NI':'沪镍','SN':'沪锡',
    'RB':'螺纹钢','HC':'热卷','I':'铁矿石','J':'焦炭','JM':'焦煤','SM':'锰硅','SF':'硅铁',
    'FG':'玻璃','SA':'纯碱','SH':'烧碱','AO':'氧化铝','SP':'纸浆','RU':'橡胶','NR':'20号胶',
    'BR':'合成橡胶',
    'A':'豆一','B':'豆二','M':'豆粕','Y':'豆油','RM':'菜粕','OI':'菜油','P':'棕榈油',
    'C':'玉米','CS':'淀粉','JD':'鸡蛋','LH':'生猪','AP':'苹果','CJ':'红枣','PK':'花生',
    'SR':'白糖','CF':'棉花','CY':'棉纱','UR':'尿素','ZC':'动力煤',
    'MA':'甲醇','EG':'乙二醇','V':'PVC','L':'塑料','PP':'PP','EB':'苯乙烯','TA':'PTA',
    'PF':'短纤','PR':'瓶片','PX':'对二甲苯','PG':'LPG',
    'FU':'燃料油','BU':'沥青','LU':'低硫燃油',
    'SI':'工业硅','PS':'多晶硅','LC':'碳酸锂','SS':'不锈钢','EC':'欧线',
    'IM':'中证1000','IC':'中证500','IF':'沪深300','IH':'上证50',
}

def norm(n):
    if not n: return ''
    return n.replace('（代客）','').replace('(代客)','').strip()

def group_of(name):
    n = norm(name)
    if n in FOREIGN: return 'foreign'
    if n in INST: return 'inst'
    return 'retail'

def fetch_day(date):
    """拉一天数据"""
    url = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
    all_rows = []
    page = 1
    while True:
        params = {
            'sortColumns': 'TRADE_CODE',
            'sortTypes': '1',
            'pageSize': '500',
            'pageNumber': str(page),
            'reportName': 'RPT_FUTU_DAILYPOSITION',
            'columns': 'TRADE_CODE,SECURITY_CODE,ORG_NAME_ABBR_NEW,LONG_POSITION,SHORT_POSITION,LP_CHANGE,SP_CHANGE',
            'source': 'WEB',
            'client': 'WEB',
            'filter': f"(TRADE_DATE='{date}')(TYPE=\"0\")"
        }
        r = requests.get(url, params=params, headers={'Referer':'https://data.eastmoney.com/'}, timeout=30)
        d = r.json()
        if not d.get('result'): break
        rows = d['result']['data']
        all_rows.extend(rows)
        if page >= d['result']['pages']: break
        page += 1
    return all_rows

def analyze(rows):
    """按品种按组汇总LP/SP变化"""
    # {sym: {group: {lp, sp}}}
    data = defaultdict(lambda: defaultdict(lambda: {'lp':0,'sp':0}))
    for r in rows:
        sym = r['TRADE_CODE']
        g = group_of(r.get('ORG_NAME_ABBR_NEW'))
        data[sym][g]['lp'] += r.get('LP_CHANGE') or 0
        data[sym][g]['sp'] += r.get('SP_CHANGE') or 0
    return data

def to_actions(sym, g, vals):
    """把一组数值转成蓝图动作描述"""
    lp = vals['lp']; sp = vals['sp']
    actions = []
    # 阈值：变化>=300手才列
    TH = 300
    if lp >= TH: actions.append(('加多', lp))
    elif lp <= -TH: actions.append(('减多', -lp))
    if sp >= TH: actions.append(('加空', sp))
    elif sp <= -TH: actions.append(('减空', -sp))
    return actions

def render(date, data):
    """生成HTML"""
    groups = [('retail','五大家人'),('inst','五大机构'),('foreign','外资')]
    # 收集每组要展示的品种
    cols_html = []
    for gkey, gname in groups:
        items = []
        for sym, gd in data.items():
            if sym not in SYM_NAME: continue
            v = gd[gkey]
            acts = to_actions(sym, gkey, v)
            if acts:
                items.append((sym, SYM_NAME[sym], acts, v))
        # 按总变化绝对值排序
        items.sort(key=lambda x: -(abs(x[3]['lp'])+abs(x[3]['sp'])))
        rows_html = ''
        for sym, name, acts, v in items[:25]:
            act_str = '、'.join(f'{a}{n}' for a,n in acts)
            rows_html += f'<div class="row"><span class="sym">{name}</span><span class="act">{act_str}</span></div>'
        cols_html.append(f'<div class="col"><h2>{gname}</h2>{rows_html}</div>')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>期货席位蓝图 - {date}</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#1a1a2e;color:#eee;margin:0;padding:16px}}
h1{{font-size:18px;text-align:center;margin:8px 0 4px}}
.sub{{text-align:center;color:#888;font-size:12px;margin-bottom:16px}}
.board{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;max-width:1200px;margin:0 auto}}
.col{{background:#16213e;border-radius:8px;padding:12px}}
.col h2{{font-size:14px;margin:0 0 10px;padding-bottom:8px;border-bottom:1px solid #333}}
.row{{display:flex;justify-content:space-between;padding:4px 0;font-size:13px;border-bottom:1px solid #222}}
.sym{{color:#aaa;min-width:60px}}
.act{{text-align:right}}
@media(max-width:700px){{.board{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>期货席位蓝图</h1>
<div class="sub">{date} · 数据来源：东方财富</div>
<div class="board">{''.join(cols_html)}</div>
<div style="text-align:center;color:#555;font-size:11px;margin-top:20px">futureke7 · 未来可期工作室</div>
</body></html>'''
    return html

if __name__ == '__main__':
    date = sys.argv[1] if len(sys.argv)>1 else datetime.now().strftime('%Y-%m-%d')
    print(f"拉取 {date} ...")
    rows = fetch_day(date)
    print(f"  {len(rows)} 行")
    if not rows:
        print("无数据"); sys.exit(1)
    data = analyze(rows)
    html = render(date, data)
    out = f'{BASE}/docs/{date}.html'
    os.makedirs(f'{BASE}/docs', exist_ok=True)
    open(out,'w').write(html)
    print(f"已生成 {out}")
    # 同时更新index.html指向最新
    open(f'{BASE}/docs/index.html','w').write(f'<meta http-equiv="refresh" content="0;url={date}.html">')
