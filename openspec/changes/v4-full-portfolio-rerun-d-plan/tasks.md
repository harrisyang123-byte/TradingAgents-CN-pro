# Tasks — v4 全量分析 D 方案

## 持仓 (9/9 ✅ 全完)

- [x] P1 603236 移远通信 8 step (commit 052318a, critic v1=62→v4=86)
- [x] P2 000063 中兴通讯 8 step (commit 441247f, critic v1=86 一次过)
- [x] P3 002415 海康威视 8 step (commit 7c6972e, critic v1=86 一次过)
- [x] P4 01810 小米集团 8 step (commit eee54e9, critic v1=72→v2=86 spawn 失败主 agent 接管)
- [x] P5 002001 新和成 8 step (commit dfe29db, critic v1=86 一次过)
- [x] P6 002050 三花智控 8 step (commit 91a945b, critic v1=87 一次过)
- [x] 中期 commit + rerun-memory 更新 (commit 1882793)

## 推荐池 (0/18 进行中)

### 互联网 (2)
- [ ] P7 00700 腾讯 8 step
- [ ] P8 09988 阿里 8 step

### AI 算力 (3)
- [ ] P9 300308 中际旭创 8 step (重跑深度, 旧 v8 是简化版)
- [ ] P10 300394 天孚通信 8 step
- [ ] P11 300502 新易盛 8 step

### 半导体 (4)
- [ ] P12 688981 中芯国际 8 step (重跑深度)
- [ ] P13 002371 北方华创 8 step (重跑, 002371 自评偏差教训)
- [ ] P14 688012 中微公司 8 step
- [ ] P15 688268 华特气体 8 step

### 创新药 (3)
- [ ] P16 06160 百济神州 8 step
- [ ] P17 600276 恒瑞医药 8 step (重跑深度)
- [ ] P18 06990 科伦博泰 8 step

### 有色资源 (3)
- [ ] P19 601899 紫金矿业 8 step
- [ ] P20 600111 北方稀土 8 step
- [ ] P21 603663 三祥新材 8 step (重跑深度)

### 电力公用事业 (2)
- [ ] P22 600900 长江电力 8 step
- [ ] P23 601985 中国核电 8 step

### 消费电子家电 (1)
- [ ] P24 300433 蓝思科技 8 step (重跑深度)

## 收尾

- [ ] 重跑 6 plan:* (含 forward_view + 四维质量闸门)
  - [ ] plan:fixed_income
  - [ ] plan:cash
  - [ ] plan:commodity
  - [ ] plan:precious_metal
  - [ ] plan:real_estate
  - [ ] plan:alternative
- [ ] 重跑 alloc:portfolio (持仓覆盖度 100%)
- [ ] 辩证 skill 横向终审
- [ ] openspec change 完成 + 最终 commit + push
