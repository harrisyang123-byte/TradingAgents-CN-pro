# 归档：一次性开发/诊断脚本

这里存放从 `scripts/` 根目录归档的 **194 个一次性脚本**（`test_* / check_* / debug_*`），
它们是上游 TradingAgents-CN 历史遗留的临时验证、排查、诊断脚本，与当前 v3 advisor 主流程无关，
也不被 `run.sh` / 应用代码 import（pytest 只扫 `tests/`）。

| 子目录 | 内容 | 数量 |
|--------|------|------|
| `tests/`  | `test_*.py`  临时验证脚本 | 132 |
| `checks/` | `check_*.py` 数据/配置诊断脚本 | 50 |
| `debug/`  | `debug_*.py` 排查脚本 | 12 |

## ⚠️ 重新运行的注意事项

这些脚本原本位于 `scripts/` 根目录，多数用
`os.path.dirname(os.path.dirname(__file__))` 一类**两级向上**的方式定位项目根。
归档后路径深度 +1，若需重新运行，请把项目根加入 `PYTHONPATH` 或在脚本里多加一级
（例如改成三级向上），否则 `import app` / `import tradingagents` 会失败。

正式测试请用 `tests/` 目录 + `pytest`。
