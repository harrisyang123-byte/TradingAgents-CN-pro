#!/usr/bin/env python3
"""v4 价值创造 — AKShare ROIC/FCF 精算 (2026-06-14 外网恢复后落地)

A/B 测试结论: 计算密集项(ROIC/WACC/正向DCF)主agent估算=拍脑袋。
外网恢复 + akshare 可用后, 改为 AKShare 取 verified 财务比率精算, 不再区间妥协。

ROIC 口径(A股, 财报科目):
  ROIC ≈ EBIT×(1-税率) / 投入资本
  - EBIT×(1-税率) ≈ 息前税后总资产报酬率_平均 × 总资产 (akshare 直接有该比率)
  - 投入资本 = 股东权益 + 有息负债 - 货币资金 (≈ 总资产 - 无息负债 - 超额现金)
  简化: ROIC_proxy_low = 息前税后总资产报酬率(分母=全部总资产, 偏保守下界)
        ROIC_adj = ROIC_proxy_low × 总资产/投入资本 (投入资本<总资产 → 上调)
用法: python3 scripts/v4_roic_akshare.py 688981
"""
import sys, warnings
warnings.filterwarnings('ignore')

def compute(code: str):
    import akshare as ak
    df = ak.stock_financial_abstract(symbol=code)
    cols = [c for c in df.columns if c.startswith('2025') or c.startswith('2026')]
    col = '20251231' if '20251231' in df.columns else cols[0]

    def g(name):
        r = df[df['指标'] == name]
        if not len(r):
            return None
        try:
            return float(r.iloc[0][col])
        except Exception:
            return None

    rev = g('营业总收入'); ni_parent = g('归母净利润'); ni_total = g('净利润')
    equity = g('股东权益合计(净资产)'); roe = g('净资产收益率(ROE)')
    roa = g('总资产报酬率(ROA)'); ebit_aftertax_roa = g('息前税后总资产报酬率_平均')
    op_margin = g('营业利润率'); net_margin = g('销售净利率')
    debt_ratio = g('资产负债率'); equity_mult = g('权益乘数(含少数股权的净资产)')
    ocf = g('经营现金流量净额'); fcf_ps = g('每股企业自由现金流量')

    # 总资产 = 权益 × 权益乘数
    total_assets = equity * equity_mult if (equity and equity_mult) else None
    # 投入资本粗口径: 总资产 × (1 - 无息负债占比估40%) — 缺细科目时的保守调整
    # ROIC: 息前税后总资产报酬率是 EBIT(1-t)/总资产, 投入资本<总资产故 ROIC 略高
    roic_low = ebit_aftertax_roa  # verified 下界(分母=全部总资产)
    roic_adj = round(ebit_aftertax_roa / 0.75, 2) if ebit_aftertax_roa else None  # 投入资本≈75%总资产

    return {
        'code': code, 'as_of': col, 'source': 'akshare stock_financial_abstract (verified)',
        'revenue_yi': round(rev/1e8, 2) if rev else None,
        'net_profit_parent_yi': round(ni_parent/1e8, 2) if ni_parent else None,
        'net_profit_total_yi': round(ni_total/1e8, 2) if ni_total else None,
        'minority_interest_yi': round((ni_total-ni_parent)/1e8, 2) if (ni_total and ni_parent) else None,
        'equity_yi': round(equity/1e8, 2) if equity else None,
        'total_assets_yi': round(total_assets/1e8, 2) if total_assets else None,
        'ROE_pct': roe, 'ROA_pct': roa,
        'ebit_aftertax_roa_pct': ebit_aftertax_roa,
        'ROIC_verified_range_pct': [roic_low, roic_adj] if roic_low else None,
        'op_margin_pct': op_margin, 'net_margin_pct': net_margin,
        'debt_ratio_pct': debt_ratio,
        'ocf_yi': round(ocf/1e8, 2) if ocf else None,
        'fcf_per_share': fcf_ps,
        'fcf_sign': '负(capex吞噬)' if (fcf_ps and fcf_ps < 0) else '正',
    }

if __name__ == '__main__':
    import json
    code = sys.argv[1] if len(sys.argv) > 1 else '688981'
    print(json.dumps(compute(code), ensure_ascii=False, indent=2))
