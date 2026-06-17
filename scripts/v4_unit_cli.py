#!/usr/bin/env python3
"""v4_unit_cli.py — v4 编排器辅助 CLI（供 workflow-v4-advisor.js 通过 Bash 调用）

把单元锁、信封写入、上游版本解析、指纹计算等存储操作收敛到此，
让 JS 编排器保持轻薄、只管 agent 辩论编排。

子命令：
  lock     <unit_id>                    获取运行锁（已锁→退出码 3，AC4.7）
  unlock   <unit_id>                    释放锁
  upstream <unit_id>                    打印上游单元当前 {version,fingerprint}（JSON）
  fingerprint <file1> [file2 ...]       计算输入文件集指纹
  write    <unit_id> --payload <f> [opts]  写单元信封（version+1，更新索引）
  build-upstream <ref1> [ref2 ...]      根据上游 unit_id 列表组装 upstream[]（JSON）
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from app.services.v4 import v4_state, v4_unit_store as store  # noqa: E402


def _build_upstream(unit_ids):
    """根据上游 unit_id 组装 upstream[]（取各上游当前 version+fingerprint）。"""
    out = []
    for uid in unit_ids:
        env = store.read_unit(uid)
        if env is None:
            idx = store.load_index().get("units", {}).get(uid)
            if idx:
                out.append({"unit_id": uid, "version": idx.get("version"),
                            "fingerprint": idx.get("fingerprint")})
            else:
                out.append({"unit_id": uid, "version": None, "fingerprint": None})
        else:
            out.append({"unit_id": uid, "version": env.get("version"),
                        "fingerprint": env.get("fingerprint")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 编排器辅助 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s_lock = sub.add_parser("lock"); s_lock.add_argument("unit_id")
    s_unlock = sub.add_parser("unlock"); s_unlock.add_argument("unit_id")
    s_up = sub.add_parser("upstream"); s_up.add_argument("unit_id")
    s_fp = sub.add_parser("fingerprint"); s_fp.add_argument("files", nargs="+")
    s_bu = sub.add_parser("build-upstream"); s_bu.add_argument("refs", nargs="*")

    s_w = sub.add_parser("write")
    s_w.add_argument("unit_id")
    s_w.add_argument("--payload", required=True, help="payload JSON 文件路径")
    s_w.add_argument("--fingerprint", default="")
    s_w.add_argument("--upstream", default="", help="upstream JSON 数组（或 unit_id 逗号列表）")
    s_w.add_argument("--run-mode", default="local")
    s_w.add_argument("--status", default="green")
    s_w.add_argument("--error", default="")
    s_w.add_argument("--ttl-days", type=int, default=None)
    # D0-5 (2026-06-13) critic 接入编排: payload.credibility.final_verdict 必须 ACCEPT 才落盘
    s_w.add_argument("--skip-critic", action="store_true",
                     help="跳过 credibility.final_verdict ACCEPT 校验(紧急情况;默认必须 ACCEPT)")

    args = ap.parse_args()

    if args.cmd == "lock":
        try:
            store.acquire_lock(args.unit_id)
            print("LOCKED_OK")
            return 0
        except store.LockError as e:
            print(f"ALREADY_LOCKED {e}", file=sys.stderr)
            return 3

    if args.cmd == "unlock":
        store.release_lock(args.unit_id)
        print("UNLOCKED")
        return 0

    if args.cmd == "upstream":
        env = store.read_unit(args.unit_id)
        if env:
            print(json.dumps({"unit_id": args.unit_id, "version": env.get("version"),
                              "fingerprint": env.get("fingerprint"),
                              "status": env.get("status")}, ensure_ascii=False))
        else:
            print(json.dumps({"unit_id": args.unit_id, "version": None}, ensure_ascii=False))
        return 0

    if args.cmd == "fingerprint":
        print(v4_state.fingerprint(args.files))
        return 0

    if args.cmd == "build-upstream":
        print(json.dumps(_build_upstream(args.refs), ensure_ascii=False))
        return 0

    if args.cmd == "write":
        payload = {}
        pf = Path(args.payload)
        if pf.exists():
            try:
                payload = json.loads(pf.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                print(f"payload 读取失败: {e}", file=sys.stderr)
                return 1
        # upstream：JSON 数组 或 逗号分隔 unit_id 列表
        upstream = []
        up_raw = (args.upstream or "").strip()
        if up_raw:
            if up_raw.startswith("["):
                try:
                    upstream = json.loads(up_raw)
                except ValueError:
                    upstream = []
            else:
                upstream = _build_upstream([x.strip() for x in up_raw.split(",") if x.strip()])

        # D0-5 critic 接入编排: 校验 credibility.final_verdict ACCEPT
        # 仅对 stock:/industry:/asset:* 单元强制(plan/alloc 单元绕过)
        if not args.skip_critic and args.unit_id.startswith(("stock:", "industry:", "asset:")):
            cred = (payload or {}).get("credibility") or {}
            verdict = cred.get("final_verdict")
            if verdict != "ACCEPT":
                fatal = cred.get("fatal_flaws") or cred.get("challenges") or []
                fatal_str = "; ".join(fatal[:3]) if isinstance(fatal, list) else str(fatal)[:200]
                msg = (
                    f"BLOCKED: credibility.final_verdict={verdict!r} (need 'ACCEPT'). "
                    f"director 必须根据 critic 反馈迭代 verdict 直到 ACCEPT 才落盘。"
                    f" fatal_flaws/challenges: {fatal_str}"
                )
                print(json.dumps({
                    "unit_id": args.unit_id,
                    "blocked_by_critic": True,
                    "final_verdict": verdict,
                    "message": msg,
                }, ensure_ascii=False), file=sys.stderr)
                return 4

        # 🚨 RULE-DATA-VERIFIED 强制校验(2026-06-14 用户血泪固化, 防通富$157B事故再现)
        # 仅对 stock:* 单元启用(industry/asset 已有 critic 6.11/6.12 必查)
        if args.unit_id.startswith("stock:"):
            try:
                from app.services.v4.stock_data_contract import (
                    check_expert_valuation_verified,
                    render_data_verified_report,
                )
                check = check_expert_valuation_verified(payload or {})
                if check["block_write"]:
                    msg = (
                        f"🚨 RULE-DATA-VERIFIED 违规, 拒绝落盘! "
                        f"expert_valuation 字段未通过 verified 校验。"
                        f" violations={len(check['violations'])} warnings={len(check['warnings'])}"
                    )
                    print(json.dumps({
                        "unit_id": args.unit_id,
                        "blocked_by_rule_data_verified": True,
                        "violations": check["violations"],
                        "warnings": check["warnings"],
                        "message": msg,
                        "report": render_data_verified_report(check),
                    }, ensure_ascii=False, indent=2), file=sys.stderr)
                    return 4
                # 通过但有 warning 时打印提示, 不阻止落盘
                if check["warnings"]:
                    print(f"⚠️  RULE-DATA-VERIFIED 警告({len(check['warnings'])}项, 不阻止但建议改进): "
                          + "; ".join(w["issue"] for w in check["warnings"][:3]),
                          file=sys.stderr)
            except ImportError:
                pass  # 契约模块不可用时跳过(向前兼容)

            # 🚨 v4_verify_audit 强制审计 (2026-06-17 iteration 2 GATE attempt#1 fatal_flaw 修复)
            # 协议 Part 7 #13: director write_unit 落盘前必跑, fatal 违规 ≥1 → 阻断写盘
            # 这是 RULE-DATA-VERIFIED 红线从"认知层规则"升级为"代码层强制"的最后一道闸
            try:
                # 同目录 import: scripts/v4_verify_audit.py
                _here = Path(__file__).resolve().parent
                if str(_here) not in sys.path:
                    sys.path.insert(0, str(_here))
                from v4_verify_audit import audit_payload  # type: ignore
                vio = audit_payload(payload or {})
                fatal_vios = [v for v in vio if v.get("severity") == "fatal"]
                if fatal_vios:
                    print(json.dumps({
                        "unit_id": args.unit_id,
                        "blocked_by_v4_verify_audit": True,
                        "fatal_count": len(fatal_vios),
                        "should_count": sum(1 for v in vio if v.get("severity") == "should"),
                        "violations": fatal_vios[:10],
                        "message": (
                            f"🚨 v4_verify_audit fatal 违规 {len(fatal_vios)} 项, 拒绝落盘! "
                            f"协议 Part 7 #13: 数字字段必须配 verified_source URL/数据源, "
                            f"凭训练记忆填阈值=fatal_flaw (通富 $157B 同型)"
                        ),
                    }, ensure_ascii=False, indent=2), file=sys.stderr)
                    return 4
                if vio:
                    print(f"⚠️  v4_verify_audit should 警告 {len(vio)} 项 (不阻止落盘): "
                          + "; ".join(v["issue"][:60] for v in vio[:3]),
                          file=sys.stderr)
            except ImportError:
                # v4_verify_audit 不可用时降级为警告 (但应在 CI/CD 测发现)
                print("⚠️  v4_verify_audit 模块未加载, 跳过审计 (协议 Part 7 #13 期望此处必跑)",
                      file=sys.stderr)

        env = store.new_envelope(
            args.unit_id,
            payload,
            fingerprint=args.fingerprint,
            upstream=upstream,
            run_mode=args.run_mode,
            status=args.status,
            error=(args.error or None),
            ttl_days=args.ttl_days,
        )
        written = store.write_unit(env, bump_version=True)
        print(json.dumps({"unit_id": args.unit_id, "version": written["version"],
                          "status": written["status"]}, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
