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
  bull: any
  bear: any
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
  intra_alloc_unit: UnitMeta
  stock_weights: StockWeightRow[]
  stocks: StockUnit[]
}

export interface InvestmentMapRow {
  chokepoint?: string
  recommended?: string
  analyzed?: boolean
  rank?: number
  why?: string
  rating?: string
}

export interface StockDetail {
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
    return ApiClient.get<StockDetail>(`/api/portfolio/v4/stock/${encodeURIComponent(code)}`)
  },
}
