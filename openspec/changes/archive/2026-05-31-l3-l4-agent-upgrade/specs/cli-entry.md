# CLI 入口验收规格

## 1. 完整执行

```bash
python cli/run_advisor.py run --user-id 6a094adc2c14a0b1cc6201ff
```

- [x] 终端打印行业配置表
- [x] 处方覆盖全部持仓（当前 36 只）
- [x] 包含 industry_bucket + fund_role 字段
- [x] 保存到 MongoDB portfolio_advice 集合
- [x] 打印运行耗时和处方数量

## 2. Lite 模式

```bash
python cli/run_advisor.py run --user-id 6a094adc2c14a0b1cc6201ff --lite
```

- [x] L1/L2 辩论轮次设为 1 轮
- [x] 3-5 分钟内完成
- [x] 处方覆盖全部持仓

## 3. 查看最新处方

```bash
python cli/run_advisor.py show --user-id 6a094adc2c14a0b1cc6201ff
```

- [x] 展示最新处方创建时间
- [x] 展示每条处方的 action、目标权重

## 4. 错误处理

- [x] 数据获取失败时有降级提示
- [x] DB 连接失败时有明确的错误信息
- [x] 参数错误时打印 help 信息
