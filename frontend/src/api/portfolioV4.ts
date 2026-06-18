// portfolioV4.ts — v4 分层独立深度投研系统 前端 API 客户端（FR-008 / FR-009）
//
// 只读契约：所有接口只读 Mongo 缓存产物（秒级响应，不触发 LLM，NFR1.2）。
// 触发深度分析走 CLI（cli_hint 提示），前端不提供「点即跑 LLM」按钮（AC4.6）。
//
// 双来源同构（FR-009 / NFR4.1）：
//   VITE_STATIC_SNAPSHOT=1 → fetch frontend/public/snapshot/v4/*.json（无后端降级）
//   否则                   → 走 /api/portfolio/v4/* 接口
// 两来源返回结构一致，调用方无感知。

import { ApiClient } from './request'
import type { ApiResponse } from './request'

const STATIC_SNAPSHOT =
  String(import.meta.env.VITE_STATIC_SNAPSHOT ?? '').trim() === '1'

async function loadSnapshot<T>(file: string): Promise<ApiResponse<T>> {
  const res = await fetch(`/snapshot/v4/${file}`, { cache: 'no-cache' })
  if (!res.ok) {
    throw new Error(`v4 静态快照加载失败 (${res.status}): /snapshot/v4/${file}`)
  }
  const data = (await res.json()) as T
  return { success: true, data, message: '', code: 0 }
}

// ── 单元状态（五色 + stale + cli_hint，FR-004 / FR-005） ──────────────
export type UnitStatus = 'gray' | 'blue' | 'green' | 'yellow' | 'red'

export interface UpstreamRef {
  unit_id: string
  version: number | null
  fingerprint: string | null
}

export interface UnitMeta {
  unit_id: string
  status: UnitStatus
  status_label: string
  stale_reason: string | null
  cli_hint: string
  version: number | null
  generated_at: string | null
  ttl_days: number | null
  upstream: UpstreamRef[]
  run_mode: string | null
  exists: boolean
}

// ── 七大类配置（后端 asset_classes 同源下发） ─────────────────────────
export interface AssetClassConfig {
  key: string
  label_zh: string
  examples: string
  max_drill_depth: 'industry_stock' | 'instrument' | 'holding_structure'
  ttl_days: number
  order: number
}

// ── Tab1 概览 ─────────────────────────────────────────────────────────
export interface AssetCardData extends UnitMeta {
  asset_class: string
  label: string
  max_drill_depth: string
  current_weight: number
  target_weight: number | null
  action: string | null
  actively_zeroed: boolean
  stance: string | null
  direction: string | null
  summary: string | null
}

export interface AllocationInputWarning {
  asset_class: string
  issue: string
  detail?: string
}

export interface AllocationOverview extends UnitMeta {
  equity_quota: number | null
  sum_check: number | null
  input_warnings: AllocationInputWarning[]
  summary: string
}

export interface V4Overview {
  allocation: AllocationOverview
  asset_cards: AssetCardData[]
  equity_quota: number | null
  equity_disabled: boolean
  has_data: boolean
  asset_classes: AssetClassConfig[]
  // D0-6 基金穿透体检 (2026-06-13)
  fund_passthrough?: FundPassthroughSummary | null
}

export interface FundPassthroughSummary {
  summary: {
    total_market_value: number
    direct_market_value: number
    indirect_market_value: number
    industries_count: number
    funds_with_passthrough: number
    funds_without_passthrough: number
    passthrough_coverage_pct: number
    method?: string
  }
  style_factors: {
    size: Record<string, number>
    growth_value: Record<string, number>
    region: Record<string, number>
    fund_type: Record<string, number>
    raw_funds?: any[]
    total_fund_mv: number
  }
  overlap_analysis: {
    theme_overlaps: Array<{
      theme: string
      fund_count: number
      total_mv: number
      funds: Array<{ code: string; name: string; mv: number }>
      advice: string
    }>
    stock_overlaps: Array<{
      code: string
      name: string
      total_indirect_value: number
      fund_count: number
      funds: any[]
    }>
    summary: {
      theme_overlap_count: number
      theme_overlap_total_mv: number
      stock_overlap_count: number
      indirect_concentration_top10: Array<{
        code: string
        name: string
        total_indirect_value: number
        fund_count: number
      }>
    }
  }
  industries_top10?: any[]
  indirect_concentration_top10?: Array<{
    code: string
    name: string
    total_indirect_value: number
    fund_count: number
  }>
}

// ── Tab2 大类详情 ─────────────────────────────────────────────────────
export interface ReflectionData {
  prev_stance?: string | null
  prev_date?: string | null
  what_changed?: string
  why_changed?: string
  self_check?: string
}

export interface AssetVerdict {
  stance?: string
  situation?: string
  direction?: string
  summary?: string
  risks?: string[]
  trend?: string
  confidence?: string
  // Chokepoint 框架：行业 director 的瓶颈落地结论
  chokepoint_conclusion?: string
  // §5.9 B：结果闭环反思（Layer 1，跨版本自省），首跑 self_check='first_run'
  reflection?: ReflectionData | null
  // 前瞻视野（11 维内化前瞻能力，A/B 测试落地）
  forward_view?: ForwardView | null
  // D0-2 投资地图结论(行业层)
  investment_conclusion?: string
}

export interface ForwardCalendarEvent {
  date?: string
  event?: string
  consensus?: string
  our_view?: string
  gap?: string
  impact_on_class?: string
}
export interface PathScenario {
  name?: string  // base|bull|bear
  prob?: number
  trigger?: string
  macro_outcome?: string
  asset_impact?: string
  implied_pe?: number       // 个股层情景估值
  implied_target_price?: number
}
export interface KeyAssumption {
  assumption?: string
  falsification_signal?: string
}
export interface TailRisk {
  event?: string
  prob?: number
  early_warning?: string
  impact?: string
  hedge_action?: string
}
export interface ForwardView {
  near_term_calendar?: ForwardCalendarEvent[]
  mid_term_path?: string
  path_scenarios?: PathScenario[]
  positioning_view?: string
  iv_skew_view?: string
  key_assumptions?: KeyAssumption[]
  tail_risks?: TailRisk[]
  cross_market_leading?: string
  trigger_monitor?: string[]
  // D0-4 新增字段(个股 forward_view)
  consensus_view?: string
  expectation_vs_consensus?: string
  // D0-5 TradingAgents 对齐 - forward_view 6 维多维推演 (2026-06-13)
  market_regime?: string                  // 看多/看空/中性大盘风格 + 概率(决定 PE 中枢)
  liquidity_environment?: string          // LPR/MLF/外资流向对 PE 的影响
  industry_cycle_phase?: string           // 行业周期阶段(起飞/高速/平台/衰退) + 估值修正系数
  systematic_risk_beta?: string | { beta?: number; scenarios?: any }  // β + 大盘各情景下本股影响
  comparable_matrix?: any                 // 对标公司 PE 表 + 我方相对溢价/折价 + 推演路径
  pricing_power_analysis?: string         // 涨价 pass-through 能力 + 历史佐证
}

// D 阶段 5+1 五力深做(2026-06-13)
export interface ForceDynamic {
  force_a?: string
  force_b?: string
  mechanism?: string
}

export interface FiveForces {
  five_forces_summary?: {
    entry?: string
    substitute?: string
    buyer?: string
    supplier?: string
    rivalry?: string
  }
  cross_force_dynamics?: {
    mutual_reinforcement?: ForceDynamic[]
    mutual_offset?: ForceDynamic[]
    weakest_link?: string
    trend?: string
  }
  moat_synthesis?: string
  moat_rating?: string
  moat_durability?: string
  key_risk?: string
  monitoring_signals?: string[]
  implication_for_director?: string
  evidence?: any[]
}

// D0-4 产业链卡位(行业层投资地图反查到个股视角)
export interface ChainPositioningRow {
  rank?: number
  recommended?: string
  chokepoint?: string
  is_self?: boolean
  rating?: string
  target_price_live?: number | null
  why?: string
}

export interface ChainPositioning {
  industry?: string
  chokepoint?: string
  my_rank?: number
  my_why?: string
  industry_top?: ChainPositioningRow[]
  industry_conclusion?: string
  data_source?: string
}

// D0-4 可信度(critic 评审过程)
export interface Credibility {
  critic_score?: number          // 最终 ACCEPT 分数
  critic_iterations?: number     // 迭代轮数
  initial_score?: number         // 初始分数
  challenges?: string[]          // 评审委员会的关键挑战
  final_verdict?: 'ACCEPT' | 'NEEDS_CHANGES' | string
  reviewers?: string[]           // 例如 ['芒格', '段永平', 'Serenity', '达里奥']
}

export interface PlanInstrument {
  instrument?: string
  vehicle?: string
  suggest_pct?: number
  tradable?: boolean
  reasoning?: string
}

export interface AssetPlan {
  holding_structure?: PlanInstrument[]
  duration_view?: string
  instrument_mix?: PlanInstrument[]
  risk_flags?: string[]
  holding_only_note?: string
  note?: string
  // 新扁平 schema(固收/现金/大宗/贵金属/房地产/另类执行方案)
  stance?: string
  summary?: string
  structure_target?: string
  action_plan?: Record<string, string> | string
  valuation_basis?: string
  current_weight?: number | null
  target_weight?: number | null
}

export interface IndustryAllocationRow {
  industry: string
  target_weight: number
  reasoning?: string
}

export interface AssetDetail {
  asset_class: string
  label: string
  is_equity: boolean
  max_drill_depth: string
  asset_unit: UnitMeta
  verdict: AssetVerdict | null
  tradable: Array<{ code?: string; name?: string; note?: string; weight?: number }>
  holding_only_exposure: number
  // §5.9 A：大类多空辩论 + 三专项分析师（所有大类通用，DebateRound 复用 Tab3 类型）
  debate_rounds: DebateRound[]
  analysts?: Record<string, any>
  // 非权益分支
  plan_unit?: UnitMeta
  plan?: AssetPlan | null
  // 权益分支
  equity_industries_unit?: UnitMeta
  industries?: IndustryAllocationRow[]
}

// ── Tab3 行业详情 ─────────────────────────────────────────────────────
export interface DebateRound {
  round: number
  // 旧格式(行业层): {round, bull, bear} 双方一行
  bull?: any
  bear?: any
  // 新格式(个股层 5+1 架构): {round, side, thesis} 单方一行
  side?: 'bull' | 'bear' | string
  thesis?: string
}

export interface StockWeightRow {
  code: string
  target_weight: number
  entry_price_range?: string | number[]
  reasoning?: string
}

export interface StockUnit extends UnitMeta {
  code: string | null
  name: string | null
  rating: string | null
  target_price: number | string | null
}

export interface IndustryDetail {
  industry: string
  industry_unit: UnitMeta
  verdict: AssetVerdict | null
  debate_rounds: DebateRound[]
  // Chokepoint 产业链瓶颈地图（行业层增强）
  chokepoint_map?: ChokepointNode[]
  top_chokepoints?: string[]
  // D0-2 投资地图：瓶颈环节→推荐个股→卡位排序
  investment_map?: InvestmentMapRow[]
  analysts?: Record<string, any>
  // 7 把辩证尺：TAM/CAGR/渗透率/集中度/先行指标/瓶颈迁移/5年驱动力
  industry_future_market?: Record<string, any>
  // 前瞻视野：近端日历 + 中期路径 + 情景推演
  forward_view?: ForwardView | Record<string, any> | null
  // 证据链（54 条 verified/estimated/missing）
  evidence?: any[]
  // 数据质量说明
  data_quality?: string
  data_status?: string
  // 可信度（director 自评/critic）
  credibility?: Credibility | Record<string, any> | null
  reflection?: ReflectionData | Record<string, any> | null
  value_creation_industry?: Record<string, any>
  fund_recommendation?: Record<string, any>
  intra_alloc_unit: UnitMeta
  stock_weights: StockWeightRow[]
  stocks: StockUnit[]
  // D0-6 (2026-06-13) 基金穿透 — 间接持仓
  indirect_holdings?: IndirectHoldings | null
}

export interface IndirectHoldings {
  direct_yi: number       // 直接持股(本行业)总市值(元)
  indirect_yi: number     // 基金间接贡献本行业总市值(元)
  total_yi: number
  contributing_funds: ContributingFund[]
  summary?: {
    total_market_value: number
    direct_market_value: number
    indirect_market_value: number
    industries_count: number
    funds_with_passthrough: number
    funds_without_passthrough: number
    passthrough_coverage_pct: number
  }
}

export interface ContributingFund {
  code: string
  name: string
  market_value: number             // 该基金总持仓市值
  industry_weight_pct: number       // 该基金中本行业占比
  indirect_yi: number               // 间接贡献金额 = market_value × industry_weight_pct
  data_status?: 'verified' | 'estimated' | 'partial' | string
}

export interface InvestmentMapRow {
  chokepoint?: string
  recommended?: string
  analyzed?: boolean
  rank?: number
  why?: string
  rating?: string
  // D0-2 修复(2026-06-13): 后端实时同步个股最新评级到投资地图
  target_price_live?: number | null
  rating_source?: 'stock_unit_latest' | string
}

export interface StockDetail {
  anchoring_check?: {
    user_challenge?: string
    honest_answer?: string
    but_distinction?: string
    the_real_risk?: string
    corrected_framing?: string
    critic_miss?: string
  }
  valuation_cross_check?: {
    comparable?: string
    sotp?: string
    optionality?: string
    methods_divergence?: string
  }
  reverse_dcf?: any
  code: string
  name?: string
  industry?: string
  stock_unit?: UnitMeta
  rating?: string
  target_price?: number | null
  entry_price_range?: number[]
  price_at_judgment?: number | null
  valuation_basis?: string        // D0-1 估值推导链
  expectation_gap?: string
  chokepoint_score?: string
  discovery_level?: string
  business_quality?: string
  position_nature?: string
  worst_case?: string
  downside?: string
  sell_discipline?: string[]
  thesis?: string
  risks?: string[]
  confidence?: string
  forward_view?: ForwardView | null
  five_forces?: FiveForces | null   // D 阶段 5+1 五力深做
  // D0-4 (2026-06-13) 服务"全面/可信"目标的新字段
  verdict_oneliner?: string | null   // 一句话总结(可信:核心判断不绕弯)
  chain_positioning?: ChainPositioning | null   // 产业链卡位(全面:连接行业层)
  industry_weight_pct?: number | null   // 行业内目标权重(可执行:仓位计算器)
  credibility?: Credibility | null   // 可信度(可信+会学习:critic 评审过程)
  // D0-5 (2026-06-13) TradingAgents 对齐字段
  risk_debate_summary?: {
    aggressive_main_attack?: string
    safe_main_attack?: string
    neutral_proposal_adopted?: string
    neutral_proposal_rejected?: string
  } | null
  risk_debate_full?: {
    aggressive?: any
    safe?: any
    neutral?: any
  } | null
  sentiment_view?: string | null
  sentiment_full?: any | null
  memory_used?: string[]
  debate_rounds?: DebateRound[]
  analysts?: Record<string, any>
  reflection?: ReflectionData | null
  historical_alpha?: HistoricalAlpha | null   // C 阶段回测准确率
  evidence?: any[]
}

export interface HistoricalAlpha {
  evaluated_at?: string
  prev_version?: number | null
  prev_judgment?: { rating?: string; target_price?: number | null; date?: string }
  actual_outcome?: { price?: number | null; change_vs_target_pct?: number | null; source?: string }
  hit?: string
  alpha_note?: string
  data_status?: string
}

export interface ChokepointNode {
  layer?: string
  node?: string
  irreplaceability?: string
  supply_concentration?: string
  capacity_rigidity?: string
  value_capture?: string
  substitution_risk?: string
  beneficiaries_a?: string[]
  beneficiaries_qdii?: string[]
  is_top?: boolean
  evidence_status?: string
}

// ── 全单元状态 ────────────────────────────────────────────────────────
export interface UnitsStatusResp {
  units: UnitMeta[]
  has_data: boolean
}

// ── API ───────────────────────────────────────────────────────────────
export const portfolioV4Api = {
  async getOverview() {
    if (STATIC_SNAPSHOT) return loadSnapshot<V4Overview>('overview.json')
    return ApiClient.get<V4Overview>('/api/portfolio/v4/overview')
  },

  async getUnitsStatus() {
    if (STATIC_SNAPSHOT) return loadSnapshot<UnitsStatusResp>('units_status.json')
    return ApiClient.get<UnitsStatusResp>('/api/portfolio/v4/units/status')
  },

  async getAssetDetail(assetClass: string) {
    if (STATIC_SNAPSHOT) return loadSnapshot<AssetDetail>(`asset_${assetClass}.json`)
    return ApiClient.get<AssetDetail>(`/api/portfolio/v4/asset/${encodeURIComponent(assetClass)}`)
  },

  async getIndustryDetail(name: string) {
    if (STATIC_SNAPSHOT) return loadSnapshot<IndustryDetail>(`industry_${name}.json`)
    return ApiClient.get<IndustryDetail>(`/api/portfolio/v4/industry/${encodeURIComponent(name)}`)
  },

  async getStockDetail(code: string) {
    if (STATIC_SNAPSHOT) return loadSnapshot<StockDetail>(`stock_${code}.json`)
    // D0-8: 后端 Mongo 可能没该单元(刚跑出的产物只在 data/v4/stocks/),
    // 静态快照永远是最新(build_snapshot_v4.py 落盘后即更新), 优先尝试快照, 失败再走 API
    try {
      return await loadSnapshot<StockDetail>(`stock_${code}.json`)
    } catch {
      return ApiClient.get<StockDetail>(`/api/portfolio/v4/stock/${encodeURIComponent(code)}`)
    }
  },

  async getHoldingsReview() {
    if (STATIC_SNAPSHOT) return loadSnapshot<HoldingsReview>('holdings_review.json')
    try {
      return await loadSnapshot<HoldingsReview>('holdings_review.json')
    } catch {
      return ApiClient.get<HoldingsReview>('/api/portfolio/v4/holdings-review')
    }
  },

  // ── 选股池 & 产业链瓶颈扫描成果（2026-06-15）─────────────────────────
  // _scan/*.json 是 alpha 扫描/产业链瓶颈深挖产物，只在静态快照里（无后端路由），
  // 始终走 snapshot fetch；调用方异常自行兜底（无数据时显示空态）。
  async getScanIndex() {
    return loadSnapshot<ScanIndex>('_scan/_index.json')
  },
  async getScanFile(file: string) {
    return loadSnapshot<Record<string, unknown>>(`_scan/${file}`)
  },
}

// ── 扫描索引类型 ──────────────────────────────────────────────────────
export interface ScanFileMeta {
  file: string
  method: string
  key: string
}
export interface ScanIndex {
  generated: string
  scan_files: ScanFileMeta[]
}

// ── D0-8 投资决策全景树（持仓挂大类/行业 + 全局配比 + 资金流向）──────
export interface HoldingRow {
  code: string; name: string; market_value: number; weight: number
  instrument_type: string
  analyzed: boolean; stance: string | null; action: string | null
  confidence: number | null; summary: string | null; stop_loss: string | null
}
export interface FundTheme {
  theme: string; fund_count: number; total_mv: number
  keep: Array<{ code: string; name: string; mv: number }>
  sell: Array<{ code: string; name: string; mv: number }>
  release_mv: number; action: string
}
export interface IndustryNode {
  name: string; direct_value: number; indirect_value: number; total_value: number
  has_industry_analysis: boolean
  holdings: HoldingRow[]
  indirect: Array<{ code: string; name: string; indirect_value: number | null }>
  recommendations?: Array<{ code: string; name: string; stance: string | null; target_price: string | null; pe: number | null; roic: string | null; instrument_type?: string; is_recommendation: boolean }>
  fund_holdings?: Array<{ code: string; name: string; market_value: number; weight: number; instrument_type: string }>
  fund_value?: number
  rec_count?: number
}
export interface AssetNode {
  key: string; label: string
  current_value: number; current_pct: number
  target_pct: number | null; action: string | null; gap_value: number | null
  has_class_analysis: boolean
  industries: IndustryNode[]
  direct_holdings: HoldingRow[]
  fund_themes: FundTheme[]
  reasoning?: { current_pct?: number; target_pct?: number; gap?: string; macro?: string; flow?: string; policy?: string; risk?: string }
}
export interface FlowItem { desc: string; amount: number | null; note?: string }
export interface HoldingsReview {
  as_of: string | null
  summary: {
    total_value: number
    analyzed_count: number; total_stocks: number; total_funds: number
    pending_actions: number
    style_region: Record<string, number>
    config_note: string
  }
  asset_tree: AssetNode[]
  capital_flow: { sources: FlowItem[]; uses: FlowItem[] }
  fund_groups: FundTheme[]
  indirect_holdings: Array<{ code: string; name: string; indirect_value: number; fund_count: number; note: string }>
}
