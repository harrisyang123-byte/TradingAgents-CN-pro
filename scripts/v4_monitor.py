#!/usr/bin/env python3
"""v4 止损监控脚本 (D0-5/2026-06-13)

读 data/v4/stocks/<code>.json 中的 sell_discipline + forward_view.trigger_monitor,
按规则类型分两类:

1. 价格型(自动可监控): 跌破/涨破指定价格 → 用 AKShare 取实时价 → 触发即输出 markdown 警报
2. 基本面型(半自动): 净利率 < X% / 应收周转 > Y 天 / 客户 capex > Z 亿 → 季度财报后人工核查
   → 输出"需人工核查"清单 + 每季度提示

输出: data/v4/_monitor/{date}_alerts.md (markdown 警报)
+ stdout 显示当前所有触发项.

不依赖 cron, 用户手动跑或接 GitHub Actions:
  python scripts/v4_monitor.py            # 检查全部 stocks
  python scripts/v4_monitor.py 002371     # 检查单只
  python scripts/v4_monitor.py --json     # 输出 JSON 供编排器消费
"""

from __future__ import annotations
import json
import re
import sys
import datetime
from pathlib import Path
from typing import Any, Optional

STOCKS_DIR = Path("data/v4/stocks")
MONITOR_DIR = Path("data/v4/_monitor")
MONITOR_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.date.today().isoformat()


def _try_fetch_price(code: str) -> Optional[float]:
    """用 AKShare 取实时价; 沙箱无外网时返回 None"""
    try:
        import akshare as ak
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return None
        kv = dict(zip(df["item"], df["value"]))
        return float(kv.get("最新", 0)) or None
    except Exception:
        return None


def _parse_price_rules(sell_discipline: list[str], trigger_monitor: list[str]) -> list[dict]:
    """从 sell_discipline / trigger_monitor 文本解析价格阈值规则"""
    rules: list[dict] = []
    for src_label, items in [("sell_discipline", sell_discipline or []),
                              ("trigger_monitor", trigger_monitor or [])]:
        for s in items:
            # 模式 1: "跌破 X 元" / "X 元 → 减仓"
            m = re.search(r"跌破\s*(\d{2,5}(?:\.\d+)?)\s*元", s)
            if m:
                rules.append({
                    "type": "price_below",
                    "threshold": float(m.group(1)),
                    "action": s,
                    "source": src_label,
                })
                continue
            m = re.search(r"涨破\s*(\d{2,5}(?:\.\d+)?)\s*元", s)
            if m:
                rules.append({
                    "type": "price_above",
                    "threshold": float(m.group(1)),
                    "action": s,
                    "source": src_label,
                })
    return rules


def _parse_fundamental_rules(sell_discipline: list[str], trigger_monitor: list[str]) -> list[dict]:
    """识别基本面型规则(需人工季度核查)"""
    rules: list[dict] = []
    keywords = [
        ("毛利率", "季度毛利率"),
        ("净利率", "季度净利率"),
        ("应收", "应收账款周转"),
        ("库存", "库存周转"),
        ("市场份额", "份额"),
        ("管制", "出口管制"),
        ("capex", "客户资本开支"),
        ("二供", "二供分流"),
        ("订单", "订单兑现"),
    ]
    for src_label, items in [("sell_discipline", sell_discipline or []),
                              ("trigger_monitor", trigger_monitor or [])]:
        for s in items:
            for kw, type_label in keywords:
                if kw in s:
                    # 跳过纯价格型
                    if re.search(r"\d{2,5}\s*元", s) and "毛利率" not in s and "净利率" not in s:
                        continue
                    rules.append({
                        "type": "fundamental",
                        "indicator": type_label,
                        "rule_text": s,
                        "source": src_label,
                        "review_cadence": "quarterly",  # 季度核查
                    })
                    break
    return rules


def check_one(code: str, current_price: Optional[float] = None) -> dict:
    """检查单只股票的所有止损规则"""
    fp = STOCKS_DIR / f"{code}.json"
    if not fp.exists():
        return {"code": code, "error": "stock unit not found"}
    d = json.loads(fp.read_text(encoding="utf-8"))
    p = d.get("payload", {})

    name = p.get("name", code)
    rating = p.get("rating", "?")
    target_price = p.get("target_price")
    judgment_price = p.get("price_at_judgment")

    sell_disc = p.get("sell_discipline") or []
    trigger_mon = (p.get("forward_view") or {}).get("trigger_monitor") or []

    price_rules = _parse_price_rules(sell_disc, trigger_mon)
    fund_rules = _parse_fundamental_rules(sell_disc, trigger_mon)

    # 取实时价
    price = current_price if current_price is not None else _try_fetch_price(code)

    triggered: list[dict] = []
    if price is not None:
        for r in price_rules:
            t = r["threshold"]
            if r["type"] == "price_below" and price < t:
                triggered.append({**r, "current_price": price,
                                  "alert": f"⚠️ 价格 ¥{price:.2f} 跌破阈值 ¥{t:.2f}"})
            elif r["type"] == "price_above" and price > t:
                triggered.append({**r, "current_price": price,
                                  "alert": f"⚠️ 价格 ¥{price:.2f} 涨破阈值 ¥{t:.2f}"})

    return {
        "code": code,
        "name": name,
        "rating": rating,
        "target_price": target_price,
        "judgment_price": judgment_price,
        "current_price": price,
        "price_rules_total": len(price_rules),
        "fundamental_rules_total": len(fund_rules),
        "triggered_price_alerts": triggered,
        "fundamental_review_needed": fund_rules,
        "checked_at": _today(),
        "data_status": "verified" if price is not None else "missing_realtime",
    }


def write_alerts_md(results: list[dict]) -> Path:
    """生成 markdown 警报文件"""
    out_path = MONITOR_DIR / f"{_today()}_alerts.md"
    lines = [f"# v4 止损监控报告 — {_today()}", ""]

    triggered_stocks = [r for r in results if r.get("triggered_price_alerts")]
    if triggered_stocks:
        lines.append(f"## 🔴 价格型告警（{len(triggered_stocks)} 只触发）")
        for r in triggered_stocks:
            lines.append(f"\n### {r['name']} ({r['code']}) - {r['rating']}")
            for t in r["triggered_price_alerts"]:
                lines.append(f"- {t['alert']}")
                lines.append(f"  - 规则来源: {t['source']}")
                lines.append(f"  - 行动: {t['action']}")
        lines.append("")
    else:
        lines.append("## ✅ 价格型: 全部正常,无触发")
        lines.append("")

    fund_total = sum(r.get("fundamental_rules_total", 0) for r in results)
    if fund_total:
        lines.append(f"## ⚠️ 基本面型: {fund_total} 条规则等待季度核查")
        lines.append("> 这些规则需要人工读季度财报/公告核查,程序无法自动判断")
        for r in results:
            if r.get("fundamental_review_needed"):
                lines.append(f"\n### {r['name']} ({r['code']}) - {len(r['fundamental_review_needed'])} 条")
                for f in r["fundamental_review_needed"][:5]:
                    lines.append(f"- [{f['indicator']}] {f['rule_text']}")

    no_data = [r for r in results if r.get("data_status") == "missing_realtime"]
    if no_data:
        lines.append("")
        lines.append(f"## ⚠️ 实时价缺失: {len(no_data)} 只(沙箱无外网或 AKShare 失败)")
        lines.append("生产环境跑此脚本应能自动取价。")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    json_mode = "--json" in argv
    codes = [a for a in argv if not a.startswith("--")]

    if not codes:
        codes = [p.stem for p in STOCKS_DIR.glob("*.json")]

    results = [check_one(c) for c in codes]

    if json_mode:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    out = write_alerts_md(results)
    triggered = sum(1 for r in results if r.get("triggered_price_alerts"))
    fund_total = sum(r.get("fundamental_rules_total", 0) for r in results)
    print(f"✅ v4 止损监控: 检查 {len(results)} 只 / 价格触发 {triggered} 只 / 基本面规则 {fund_total} 条等待人工核查")
    print(f"   → {out}")
    return 0 if triggered == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
