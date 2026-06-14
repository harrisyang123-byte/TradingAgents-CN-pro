"""v4 A股个股硬数据源 — AKShare 程序化取数。

呼应最初规划「所有数据都走 data-desk」：个股层的股价/市值/PE/PB/财务/涨幅
由本模块程序化拉取（可复现、带 as_of），**杜绝分析 subagent 凭空编数字**
（中际旭创"420元 vs 真实~1000元"事故的根因就是无可靠个股数据源 + subagent 编数）。

服务的上层需求：
- 预期差锚1（隐含增速缺口）：需要真实 PE / forward 基数 + 净利增速 → fundamentals。
- 预期差锚2（定价充分度）：需要 PE 历史分位 + 近1年涨幅 → valuation_percentile / change_1y。
- Chokepoint 标的卡位：需要真实市值（区分龙头 vs 小盘）。

设计铁律（对齐 macro_source「降级而非崩溃」）：
- 每个接口独立 try/except；akshare 未装 / 无网 / 接口变更 / 代码不存在 → 对应字段
  留 None + 标 note，绝不抛异常中断采集。
- 只取数、标 verified + 接口 + as_of，不做任何投资研判。
- 取不到就老实标 unavailable，严禁编造。

A股代码规范：6位数字（如 '300308' / '600519'）。港股/美股不在本模块（走联网）。
"""

from __future__ import annotations

import datetime
from typing import Any


def _is_a_share(code: str) -> bool:
    c = (code or "").strip()
    return c.isdigit() and len(c) == 6


def _safe_float(v) -> float | None:
    try:
        import math
        f = float(v)
        return None if math.isnan(f) else f
    except Exception:
        return None


def _today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def _fetch_spot(ak, code: str, out: dict) -> None:
    """实时快照：现价 / 涨跌幅 / 市值 / PE-TTM / PB（东财个股信息口径）。

    2026-06-14: 东财 push2 实时端点(stock_individual_info_em)连接被阻断(RemoteDisconnected),
    降级走 stock_zh_a_hist 取最近收盘价(verified)。
    """
    # 主路径: 新浪源 stock_zh_a_daily(稳定, 2026-06-14实测东财push2阻断后新浪稳定)
    try:
        pfx = ("sh" if code[0] == "6" else "sz") + code
        import datetime
        end = datetime.date.today().strftime("%Y%m%d")
        start = (datetime.date.today() - datetime.timedelta(days=20)).strftime("%Y%m%d")
        h = ak.stock_zh_a_daily(symbol=pfx, start_date=start, end_date=end)
        if h is not None and not h.empty:
            out["price"] = _safe_float(h.iloc[-1]["close"])
            out["price_date"] = str(h.iloc[-1]["date"])
            out["price_source"] = "stock_zh_a_daily(新浪源,稳定)"
            out["_spot_ok"] = True
    except Exception as e:
        out.setdefault("_errors", []).append(f"sina_price:{type(e).__name__}")
    # 补充: 东财个股信息(市值/行业, 间歇可用)
    try:
        df = ak.stock_individual_info_em(symbol=code)  # 两列: item / value
        kv = dict(zip(df["item"], df["value"]))
        out["name"] = kv.get("股票简称") or out.get("name")
        out["industry_em"] = kv.get("行业")
        if not out.get("price"):
            out["price"] = _safe_float(kv.get("最新"))
        out["total_mv"] = _safe_float(kv.get("总市值"))        # 元
        out["circ_mv"] = _safe_float(kv.get("流通市值"))
        out["listing_date"] = kv.get("上市时间")
        out["_spot_ok"] = True
    except Exception as e:
        out.setdefault("_errors", []).append(f"spot:{type(e).__name__}")


def _fetch_valuation(ak, code: str, out: dict) -> None:
    """估值 + 历史分位（服务预期差锚2 定价充分度）：PE-TTM / PB / 股息率 + PE 近年分位。

    接口名随 akshare 版本变化，按可用性探测（stock_a_indicator_lg 旧版 / stock_value_em 新版）。
    """
    # 接口A：stock_a_indicator_lg（旧版，含历史序列，可算分位）
    if hasattr(ak, "stock_a_indicator_lg"):
        try:
            df = ak.stock_a_indicator_lg(symbol=code)
            if df is not None and not df.empty and "pe_ttm" in df.columns:
                df = df.dropna(subset=["pe_ttm"])
                last = df.iloc[-1]
                out["pe_ttm"] = _safe_float(last.get("pe_ttm"))
                out["pb"] = _safe_float(last.get("pb"))
                out["dividend_yield"] = _safe_float(last.get("dv_ratio"))
                out["valuation_as_of"] = str(last.get("trade_date"))[:10]
                ser = df["pe_ttm"].dropna()
                window = ser.tail(750) if len(ser) >= 750 else ser
                cur = out["pe_ttm"]
                if cur is not None and len(window) > 30:
                    pct = (window < cur).sum() / len(window) * 100
                    out["pe_percentile_3y"] = round(float(pct), 1)
                    out["pe_percentile_note"] = f"PE-TTM 近{len(window)}交易日分位（越高=越贵/定价越充分）"
                return
        except Exception as e:
            out.setdefault("_errors", []).append(f"valuation_lg:{type(e).__name__}")
    # 接口B：stock_value_em（新版东财估值快照，PE/PB 模糊列匹配；分位可能无历史，留 missing）
    if hasattr(ak, "stock_value_em"):
        try:
            df = ak.stock_value_em(symbol=code)
            if df is not None and not df.empty:
                row = df.iloc[-1]  # 最新一行
                cols = {str(c): c for c in df.columns}
                def _col(*keys):
                    for name, c in cols.items():
                        if any(k in name for k in keys):
                            return _safe_float(row[c])
                    return None
                out["pe_ttm"] = _col("PE(TTM)", "市盈率(TTM)", "PE-TTM")
                out["pb"] = _col("市净率", "PB")
                out["valuation_as_of"] = str(row.get(cols.get("数据日期", ""), "")) or None
                out["valuation_note"] = "stock_value_em 快照；PE 历史分位需历史序列接口，本接口未提供则留空"
                return
        except Exception as e:
            out.setdefault("_errors", []).append(f"valuation_em:{type(e).__name__}")
    out.setdefault("_errors", []).append("valuation:no_available_interface")


def _fetch_financials(ak, code: str, out: dict) -> None:
    """财务摘要：最新营收/净利 + 同比增速（服务预期差锚1 兑现能力基数）。"""
    try:
        df = ak.stock_financial_abstract(symbol=code)
        if df is None or df.empty:
            return
        # stock_financial_abstract 为宽表：行=指标，列=各报告期。取最近列。
        idx_col = "指标" if "指标" in df.columns else df.columns[0]
        period_cols = [c for c in df.columns if c not in ("指标", "选项")]
        if not period_cols:
            return
        latest = next((c for c in period_cols if str(c).endswith("1231")), period_cols[0])
        rows = dict(zip(df[idx_col], df[latest]))
        out["report_period"] = str(latest)
        # 关键科目（名称随接口版本可能不同，best-effort 模糊匹配）
        def _pick(*keys):
            for k in rows:
                if any(kk in str(k) for kk in keys):
                    return _safe_float(rows[k])
            return None
        out["revenue"] = _pick("营业总收入", "营业收入")
        out["net_profit"] = _pick("归母净利润", "净利润")
        out["roe"] = _pick("净资产收益率", "ROE")
        out["_fin_ok"] = True
    except Exception as e:
        out.setdefault("_errors", []).append(f"fin:{type(e).__name__}")


def _fetch_value_creation(ak, code: str, out: dict) -> None:
    """★价值创造维度 verified 精算（2026-06-14 外网恢复后落地）。

    取 AKShare verified 财务比率精算 ROIC/FCF — 解决"主agent估算ROIC=拍脑袋"问题
    (A/B 测试: 计算法85 完胜 估算法35)。ROIC 口径见 scripts/v4_roic_akshare.py。
    """
    try:
        df = ak.stock_financial_abstract(symbol=code)
        if df is None or df.empty:
            return
        idx_col = "指标" if "指标" in df.columns else df.columns[0]
        cols = [c for c in df.columns if c not in ("指标", "选项")]
        # 取最近年报列(优先 1231 年报, 否则最新)
        col = next((c for c in cols if str(c).endswith("1231")), cols[0] if cols else None)
        if not col:
            return
        rows = dict(zip(df[idx_col], df[col]))

        def _g(name):
            for k in rows:
                if name in str(k):
                    return _safe_float(rows[k])
            return None

        equity = _g("股东权益合计")        # 净资产(含少数股权)
        ebit_aftertax_roa = _g("息前税后总资产报酬率")  # EBIT(1-t)/总资产 = ROIC 下界
        roe = _g("净资产收益率(ROE)") or _g("净资产收益率")
        roa = _g("总资产报酬率")
        debt_ratio = _g("资产负债率")
        equity_mult = _g("权益乘数")
        ocf = _g("经营现金流量净额")
        fcf_ps = _g("每股企业自由现金流量")
        ni_parent = _g("归母净利润")
        ni_total = _g("净利润")
        op_margin = _g("营业利润率")
        net_margin = _g("销售净利率")

        vc: dict[str, Any] = {"as_of": str(col), "source": "akshare stock_financial_abstract (verified)"}
        if ebit_aftertax_roa is not None:
            # ROIC 区间: 下界=息前税后总资产报酬率(分母全部总资产), 上界=投入资本调整(投入资本≈75%总资产)
            vc["roic_low_pct"] = round(ebit_aftertax_roa, 2)
            vc["roic_adj_pct"] = round(ebit_aftertax_roa / 0.75, 2)
            vc["roic_note"] = "ROIC区间: 下界=息前税后总资产报酬率(verified), 上界=投入资本口径调整"
        if roe is not None:
            vc["roe_pct"] = round(roe, 2)
        if roa is not None:
            vc["roa_pct"] = round(roa, 2)
        if debt_ratio is not None:
            vc["debt_ratio_pct"] = round(debt_ratio, 2)
        if equity is not None:
            vc["equity_yi"] = round(equity / 1e8, 2)
        if ocf is not None:
            vc["ocf_yi"] = round(ocf / 1e8, 2)
        if fcf_ps is not None:
            vc["fcf_per_share"] = round(fcf_ps, 3)
            vc["fcf_sign"] = "负(capex吞噬)" if fcf_ps < 0 else "正"
        if op_margin is not None:
            vc["op_margin_pct"] = round(op_margin, 2)
        if net_margin is not None:
            vc["net_margin_pct"] = round(net_margin, 2)
        if ni_parent is not None and ni_total is not None:
            vc["minority_interest_yi"] = round((ni_total - ni_parent) / 1e8, 2)
        if len(vc) > 2:
            out["value_creation_verified"] = vc
    except Exception as e:
        out.setdefault("_errors", []).append(f"vc:{type(e).__name__}")


def _fetch_change(ak, code: str, out: dict) -> None:
    """近1年涨幅（服务预期差锚2：涨幅本身不决定买卖，但定价充分度的参考）。"""
    try:
        ed = datetime.date.today()
        sd = ed - datetime.timedelta(days=400)
        # 东财历史行情（前复权）
        prefix = "sh" if code.startswith(("6", "9")) else "sz"
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                start_date=sd.strftime("%Y%m%d"),
                                end_date=ed.strftime("%Y%m%d"), adjust="qfq")
        if df is None or df.empty or "收盘" not in df.columns:
            return
        closes = df["收盘"].dropna()
        if len(closes) < 2:
            return
        first, last = float(closes.iloc[0]), float(closes.iloc[-1])
        if first > 0:
            out["change_1y_pct"] = round((last / first - 1) * 100, 1)
        out["high_1y"] = round(float(df["收盘"].max()), 2)
        out["low_1y"] = round(float(df["收盘"].min()), 2)
    except Exception as e:
        out.setdefault("_errors", []).append(f"change:{type(e).__name__}")


# ============================================================================
# 5+1 五力深做所需的竞争/产业链数据 (2026-06-13 D 阶段加)
# ============================================================================

# 5 力深做必需但 AKShare 无标准化接口的字段清单 (schema 定义)
# 这些字段当前由主 agent 在模式 A 下联网补 (web_search/web_fetch),取数后塞进 inputs 包
# 未来若有机构接口/财报关键词解析,可在此函数实现自动化
COMPETITIVE_DATA_SCHEMA: dict[str, str] = {
    # 买方力 (buyer_power) 必需
    "customer_concentration_cr1": "第一大客户占营收比例 (%)",
    "customer_concentration_cr3": "前三大客户占营收比例 (%)",
    "customer_concentration_cr5": "前五大客户占营收比例 (%)",
    "customer_type": "客户性质 (国央企/外资/民营/分散零售/B端/C端)",
    "gross_margin_3y_trend": "近 3 年毛利率序列 (eg [42, 39, 37])",
    "net_margin_3y_trend": "近 3 年净利率序列",
    "ar_turnover_days": "应收账款周转天数 (反映客户议价/占款)",
    # 供方力 (supplier_power) 必需
    "key_inputs_top3": "前三大关键投入 (eg ['射频电源', '精密阀门', '真空泵'])",
    "supplier_cr1": "最大供应商占采购比例 (%)",
    "import_dependency": "进口依赖度 (%) 或受管制清单状态",
    "inventory_turnover_days": "库存周转天数 (反映备货/断供风险)",
    # 同业竞争 (rivalry) 必需
    "industry_cr3": "行业 CR3 (前三家份额 %)",
    "industry_cr5": "行业 CR5",
    "industry_hhi": "行业 HHI 集中度指数",
    "capacity_utilization": "产能利用率 (%, 反映供需)",
    "competitor_top3": "前三大竞品 (含份额估计)",
    # 进入威胁 (entry_threat) 必需
    "rd_expense_ratio": "研发费用率 (%, 反映技术壁垒)",
    "patent_count": "累计专利数",
    "certification_cycle_months": "客户验证周期 (月, 反映认证壁垒)",
    # 替代威胁 (substitute_threat) 必需
    "substitute_alternatives": "替代技术清单 (含成熟度/渗透率)",
    "switching_cost_qualitative": "客户切换成本定性 (高/中/低 + 说明)",
}


def _fetch_competitive_data(ak, code: str, out: dict) -> None:
    """5+1 五力深做所需的竞争/产业链数据。

    现状(2026-06-13)：AKShare 无标准化接口直接取这些字段，函数仅声明 schema。
    模式 A 下由主 agent 用 web_search/web_fetch 联网补数据后塞进 inputs/stock_<code>.json。
    未来可在此扩展：
      - 财报附注关键词解析 (前五大客户/供应商集中度)
      - 卷宗/招股书结构化数据 (产能利用率/CR3/CR5)
      - 第三方数据源 (Wind/Choice/同花顺产业链卡)

    out["competitive_data_status"]: "manual" | "auto" | "missing"
    out["competitive_data_schema"]: 字段说明，让主 agent 知道要补什么
    """
    out["competitive_data_status"] = "manual_required"  # 当前需主 agent 联网补
    out["competitive_data_schema"] = COMPETITIVE_DATA_SCHEMA
    out["competitive_data_note"] = (
        "5 力深做需要的客户集中度/CR3/CR5/产能/上游供应商等字段 AKShare 无直接接口，"
        "请主 agent 在模式 A 下用 web_search/web_fetch 按 COMPETITIVE_DATA_SCHEMA 联网补，"
        "缺失字段标 missing 不编造。"
    )


def build_stock_fundamentals(code: str) -> dict[str, Any]:
    """取 A股个股硬数据。返回 {available, data{...}, note, source}。

    失败/非A股/akshare不可用 → available=False + note，绝不抛异常。
    """
    if not _is_a_share(code):
        return {"available": False, "note": f"非A股代码（{code}），个股硬数据走联网/QDII，不在 stock_source"}

    try:
        import akshare as ak  # type: ignore
    except Exception as e:  # noqa: BLE001
        return {"available": False, "note": f"akshare 未安装/不可用: {type(e).__name__}；个股数据降级，需联网核实"}

    data: dict[str, Any] = {"code": code, "as_of": _today(), "source": "akshare"}
    _fetch_spot(ak, code, data)
    _fetch_valuation(ak, code, data)
    _fetch_financials(ak, code, data)
    _fetch_value_creation(ak, code, data)  # ★价值创造 verified ROIC/FCF (2026-06-14)
    _fetch_change(ak, code, data)
    _fetch_competitive_data(ak, code, data)  # 5+1 五力深做必需字段(声明 schema, 当前需主 agent 联网补)

    # 判定可用性：至少拿到价格或估值或财务之一
    ok = any(data.get(k) is not None for k in ("price", "pe_ttm", "net_profit"))
    errors = data.pop("_errors", [])
    data.pop("_spot_ok", None)
    data.pop("_fin_ok", None)
    return {
        "available": ok,
        "data": data if ok else {},
        "note": ("个股硬数据程序化取得（AKShare），价格/PE/财务以此为准，禁止 subagent 另编"
                 if ok else f"AKShare 个股取数未拿到关键字段，降级；errors={errors}"),
        "errors": errors,
    }
