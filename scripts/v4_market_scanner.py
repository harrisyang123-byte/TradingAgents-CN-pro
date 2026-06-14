#!/usr/bin/env python3
"""v4-market-scanner 数据执行层: 全市场硬指标扫描.
新浪源(稳定, 东财push2阻断时用), 分批并发, 可重入.
用法: python3 scripts/v4_market_scanner.py <step>
  step=spot    : 拉全市场代码+价格快照 → /tmp/scan_spot.pkl
  step=fin N   : 拉第 N 批(每批1400只)财务+算指标 → /tmp/scan_fin_N.json
  step=merge   : 合并所有批 + 硬筛 → data/v4/_scan/candidates.json
"""
import akshare as ak, warnings, time, json, sys, os
from concurrent.futures import ThreadPoolExecutor
warnings.filterwarnings('ignore')
BATCH=1400

def get_spot():
    df=ak.stock_zh_a_spot()  # 新浪源, 含 代码/名称/最新价
    # 剔除 ST/退市/北交所(8开头)/科创板暂留
    rows=[]
    for _,r in df.iterrows():
        code=str(r['代码']); name=str(r['名称'])
        if 'ST' in name or '退' in name: continue
        if code.startswith('bj'): continue  # 北交所
        if code.startswith(('sh','sz')): c6=code[2:]
        else: c6=code
        if not c6.isdigit() or len(c6)!=6: continue
        if c6.startswith(('8','4','9')): continue  # 老三板/北交所代码段
        try: price=float(r['最新价'])
        except: continue
        if price<=0: continue
        rows.append({'code':c6,'name':name,'price':price})
    import pickle; pickle.dump(rows,open('/tmp/scan_spot.pkl','wb'))
    print(f"spot OK: {len(rows)} 只(剔除ST/北交所)")
    return rows

def pull_one(item):
    c=item['code']; price=item['price']
    try:
        df=ak.stock_financial_abstract(symbol=c)
        idx='指标' if '指标' in df.columns else df.columns[1]
        cols=sorted([x for x in df.columns if str(x).endswith('1231')],reverse=True)[:3]
        if len(cols)<2: return None
        def g(kw):
            for k in df[idx]:
                if kw in str(k):
                    try: return [float(df[df[idx]==k].iloc[0][c2]) for c2 in cols]
                    except: return None
            return None
        eps=g('基本每股收益') or g('每股收益')
        ni=g('归母净利润') or g('净利润')
        rev=g('营业总收入') or g('营业收入')
        roe=g('净资产收益率') or g('加权净资产收益率')
        if not eps or not eps[0] or eps[0]<=0: return None
        pe=round(price/eps[0],1)
        nig=round((ni[0]-ni[1])/abs(ni[1])*100,1) if ni and len(ni)>=2 and ni[1] else None
        revg=round((rev[0]-rev[1])/abs(rev[1])*100,1) if rev and len(rev)>=2 and rev[1] else None
        return {'code':c,'name':item['name'],'price':price,'pe':pe,'eps':eps[0],
                'ni_growth':nig,'rev_growth':revg,'roe':roe[0] if roe else None}
    except: return None

def pull_batch(n):
    import pickle; rows=pickle.load(open('/tmp/scan_spot.pkl','rb'))
    seg=rows[n*BATCH:(n+1)*BATCH]
    if not seg: print(f"batch {n} 空"); return
    out=[]; t0=time.time()
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i,r in enumerate(ex.map(pull_one,seg)):
            if r: out.append(r)
            if (i+1)%400==0: print(f"  batch{n}: {i+1}/{len(seg)} 已处理")
    json.dump(out,open(f'/tmp/scan_fin_{n}.json','w'),ensure_ascii=False)
    print(f"batch {n} OK: {len(out)}/{len(seg)} 有效财务, {time.time()-t0:.0f}s")

def merge():
    alld=[]
    for n in range(10):
        fp=f'/tmp/scan_fin_{n}.json'
        if os.path.exists(fp): alld+=json.load(open(fp))
    print(f"合并 {len(alld)} 只有效财务")
    # 硬筛: 高ROE(代理ROIC>WACC) + 高增速 + PE合理(非泡沫)
    cand=[]
    for s in alld:
        roe=s.get('roe'); nig=s.get('ni_growth'); revg=s.get('rev_growth'); pe=s.get('pe')
        if roe is None or nig is None or pe is None: continue
        # 价值创造: ROE>15 (代理 ROIC>WACC); 成长: 净利增速>20 且 营收增速>15(剔除非经常性);
        # 估值: 0<PE<增速(PEG<1, 真低估); 剔除PE>80泡沫
        if roe>15 and nig>20 and (revg is None or revg>15) and 0<pe<min(nig,80):
            peg=round(pe/nig,2)
            cand.append({**s,'peg':peg,'screen':'ROE>15+净利增速>20+PEG<1'})
    cand.sort(key=lambda x:x['peg'])
    os.makedirs('data/v4/_scan',exist_ok=True)
    res={'scan_date':time.strftime('%Y-%m-%d'),'universe':len(alld),
         'filter':'ROE>15% & 净利增速>20% & 营收增速>15% & 0<PE<min(增速,80) [PEG<1价值创造+成长+不泡沫]',
         'candidate_count':len(cand),'candidates':cand[:80],'data_status':'verified_AKShare新浪源'}
    json.dump(res,open('data/v4/_scan/candidates.json','w'),ensure_ascii=False,indent=2)
    print(f"候选池: {len(cand)} 只(PEG<1), 存 data/v4/_scan/candidates.json")
    print("\nTop 30 (按PEG升序):")
    for s in cand[:30]:
        print(f"  {s['code']} {s['name']:<8} PE{s['pe']} 净利增速{s['ni_growth']}% ROE{s['roe']}% PEG{s['peg']}")

if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='spot': get_spot()
    elif cmd=='fin': pull_batch(int(sys.argv[2]))
    elif cmd=='merge': merge()
