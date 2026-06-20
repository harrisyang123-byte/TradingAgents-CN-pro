# AI 产业链情报管线 (AI Industry Intel Pipeline)

> 从 22 个半导体/AI 产业链 X(Twitter) 信源每日抓取、结构化存储，为 v4 行业投研提供一手信息补充。

## 信源清单 (22 账号)

### Tier 1 — 产业链核心

| 账号 | 身份 | 粉丝 | 覆盖领域 |
|------|------|------|---------|
| `@dylan522p` | Dylan Patel，SemiAnalysis 创始人 | 13.9万 | 半导体 & AI 基础设施，芯片/GPU/数据中心/云 CapEx |
| `@SemiAnalysis_` | SemiAnalysis 官方号 | 11万 | AI 网络、半导体产业数据、GPU 集群、工业产出 |
| `@tengyanai` | Teng Yan，前医生，AI infra 情报 | 4.7万 | AI 基础设施 & 供应链，HBM、chiplet、封装 |
| `@aleabitoreddit` | Serenity，AI 供应链分析师 | 86.5万 | AI 瓶颈（Photonics/Memory/Neocloud）、MLCC、CPO |
| `@blockspace` | Compute's daily show | 1.2万 | AI/HPC/能源/Powered Land，数据中心选址 |

### Tier 2 — AI + 投资交集

| 账号 | 身份 | 粉丝 | 覆盖领域 |
|------|------|------|---------|
| `@firstadopter` | Tae Kim，Nvidia/AI Substack 作者 | 9.4万 | 半导体/芯片/存储，Key Context |
| `@xingpt` | XinGPT，AI 产业链分析 | 5.5万 | AI 产业链上游（玻璃基板/MLCC/覆铜板）、semiconductor 周期 |
| `@xiaomustock` | 川沐 Trumoo，交易员 | 25.9万 | 海力士/HBM 重仓、存储产业链、ADR 催化剂 |
| `@lordwilliamuk` | Lord William，1024 Capital | 2.2万 | 台湾半导体，TSM/ASX，半导体设备 |
| `@degentradinglsd` | degentrading，前 tradfi 期权做市商 | 6.6万 | AI 算力/数据中心/Neocloud 交易 |
| `@LambdaAPI` | Lambda GPU Cloud 官方 | 2万 | GPU 云基建、物理 AI |
| `@CoreWeave` | CoreWeave 官方 | 2.3万 | GPU 云、MLPerf 训练纪录、Blackwell/Rubin |
| `@karpathy` | Andrej Karpathy，AI 大神 | 306.8万 | 模型评测、AI 前沿进展 |
| `@sama` | Sam Altman，OpenAI CEO | 523万 | OpenAI 收购/人事、AI 行业风向 |
| `@bitfool1` | 比特傻，职业投资人+AI投研 | 12.8万 | 美光/SpaceX、美股投资策略、独立观点 |
| `@yiqifacai` | 一起发财 Zoe，AI 投研 | 9.1万 | 海上数据中心、AI 领域投研 |
| `@bboczeng` | 勃勃OC，美股投资日报 | 21.6万 | 半导体板块、存储利润率、FOMC |
| `@lianyanshe` | 链研社 AI First | 8.1万 | AI 前沿、美股投研、政策跟踪 |
| `@tj_research` | 投资TALK君，AI观察员 | 8.3万 | Intel 高管团队、纳指估值、FOMC |

### 产业链背景

| 账号 | 身份 | 粉丝 | 覆盖领域 |
|------|------|------|---------|
| `@bitfurygeorge` | George Kikvadze，Bitfury Group | 3.9万 | FOMC、AI 需求展望 |
| `@0xxsmart` | 加密大聪明 | 1.4万 | FOMC 前瞻、加密/美股交叉 |
| `@kobeissiletter` | The Kobeissi Letter | 210.2万 | 全球宏观（黄金/利率/中国零售） |

## 技术链路

### 抓取

`~/.claude/skills/follow-builders/scripts/scrape-custom-x.py`

- **浏览器**: CloakBrowser（58 项 C++ 指纹修补的隐形 Chromium，通过 CF/Turnstile）
- **认证**: X `auth_token` + `ct0` cookie 注入（储于 `~/.follow-builders/.env`，不进 git）
- **模式**: headless + humanize（模拟真人浏览节奏）
- **提取**: `article[data-testid="tweet"]` JS evaluate，每条取 text/url/datetime
- **去重**: `~/.follow-builders/state-custom-x.json` 追踪已抓推文 ID
- **频率**: 每天一次（对应 digest 周期），22 账号 × 间隔 1.5s

### 存储

```
data/v4/custom-feed-x.json    ← 抓取产出（108 条推文，git 跟踪）
data/v4/custom-sources.json   ← 账号清单（22 账号，git 跟踪）
~/.follow-builders/.env       ← X auth_token（不进 git）
~/.follow-builders/state-custom-x.json ← 去重状态（不进 git）
```

### 产出 JSON 结构

```json
{
  "x": [
    {
      "name": "SemiAnalysis_",
      "username": "SemiAnalysis_",
      "bio": "",
      "tweets": [
        {
          "text": "推文内容...",
          "url": "https://x.com/SemiAnalysis_/status/2068136869011861897",
          "created_at": "2026-06-20T01:00:28.000Z"
        }
      ]
    }
  ],
  "generatedAt": "2026-06-20T08:40:48Z",
  "stats": {
    "totalTweets": 108,
    "newTweets": 108,
    "sources": 22,
    "sourcesWithContent": 21,
    "sourcesBlocked": 1
  }
}
```

### 运行

```bash
cd ~/.claude/skills/follow-builders/scripts
python3 scrape-custom-x.py   # → data/v4/custom-feed-x.json
```

### Digest 生成

1. 跑 `node prepare-digest.js` 拿标准 Builder feed
2. 合并 `custom-feed-x.json` 的 `x` 数组
3. LLM 按中文 digest 模板 remix（每条必须带 URL，不编造内容）

## 覆盖的产业链环节

```
GPU/NPU         Blackwell Ultra, Rubin, Cerebras Wafer-Scale
  ├─ HBM 内存     SK Hynix HBM4e, 美光, Samsung, ADR 催化剂
  ├─ 先进封装     CoWoS, Intel 梦之队, 日月光 ASX, AMKR
  ├─ 光模块/光子  InP 衬底, CPO, 硅光, AAOI, COHR, LITE
  ├─ MLCC/被动    太阳诱电 +211%, 村田 +155%, VSH +146%
  ├─ 上游材料      玻璃基板, 覆铜板, 日本卡脖子龙头
  ├─ Neocloud     NBIS, CoreWeave CRWV, Lambda, 电网约束
  └─ 数据中心电力  FERC 快速审批, PJM 电网, CIFR, WULF
```

## 设计决策

- **为什么不用 X API**: 游客 token 过期快、限流严重；auth_token cookie 直连最稳定
- **为什么 CloakBrowser 不用裸 Playwright**: x.com 对 headless 检测严格，CloakBrowser 的指纹修补是唯一在非登录态能稳定返回内容的方案
- **为什么每个账号只抓 10 条**: balance 信息量 vs 抓取时间，22 账号 × 10 条 = 220 条上限，实际 108 条（部分账号推文不足 10）
- **为什么存 data/v4/ 不由 follow-builders 管理**: 本项目 v4 投研链消费此数据，存项目内 git 可追溯；follow-builders 是通用消化系统，二者解耦
