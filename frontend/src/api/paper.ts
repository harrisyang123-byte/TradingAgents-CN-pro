import { ApiClient } from './request'

export interface PortfolioAccountInfo {
  total_invested: number
  available_cash: number
  total_assets: number
  total_pnl: number
  total_pnl_pct: number
  updated_at?: string
}

export interface PortfolioPositionItem {
  code: string
  name?: string
  market: string
  currency: string
  quantity: number
  avg_cost: number
  last_price?: number | null
  market_value?: number
  unrealized_pnl?: number | null
  buy_date?: string | null
  notes?: string | null
  instrument_type?: string
}

export interface PortfolioSummary {
  total_invested: number
  available_cash: number
  total_assets: number
  total_market_value_cny: number
  total_pnl: number
  total_pnl_pct: number
  positions: PortfolioSummaryPosition[]
}

export interface PortfolioSummaryPosition {
  code: string
  name?: string
  market: string
  currency: string
  quantity: number
  avg_cost: number
  last_price?: number | null
  exchange_rate: number
  market_value_cny: number
  pnl_cny?: number | null
  pnl_pct?: number | null
  weight: number
  buy_date?: string | null
  notes?: string | null
  instrument_type?: string
}

export interface PaperOrderItem {
  code: string
  market: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  amount: number
  status: string
  created_at: string
  filled_at?: string
}

export interface AddPositionPayload {
  code: string
  quantity: number
  avg_cost: number
  buy_date?: string
  notes?: string
  market?: string
  instrument_type?: string
}

export interface UpdatePositionPayload {
  quantity?: number
  avg_cost?: number
  notes?: string
  instrument_type?: string
}

export interface UpdateAccountPayload {
  total_invested?: number
  available_cash?: number
}

export interface PlaceOrderPayload {
  code: string
  side: 'buy' | 'sell'
  quantity: number
  price: number
  market?: string
  analysis_id?: string
}

export interface AdviceItem {
  code: string
  name?: string
  instrument_type?: string
  action: 'buy' | 'sell' | 'hold' | 'reduce' | 'add' | 'new_position'
  current_weight: number
  target_weight: number
  reasoning: string
  risk_note: string
  // 决策卡片新字段
  priority?: 'urgent' | 'important' | 'optional'
  timing?: 'immediate' | 'conditional' | 'scheduled'
  suggested_price?: string
  trigger_condition?: string
  l1_context?: string
  l2_context?: string
  max_loss_pct?: string
  five_year_view?: string
  bias_check?: string
  data_sources?: string[]
  industry_bucket?: string
  fund_role?: string
  // v3: 决策层重构新字段
  entry_price_range?: { low: number; high: number } | number[]
  build_strategy?: 'immediate' | 'batch' | 'conditional'
  batch_plan?: Array<{ price: number; weight_pct: number; condition: string }>
  tier1_rating?: string
  pe_percentile?: number
}

export interface MarketIntel {
  industries?: Array<{ name: string; market: string; change_pct?: number }>
  lifecycle_stage?: string
  confidence?: string
  judge_verdict?: string
}

export interface StockCandidate {
  code: string
  name?: string
  market?: string
  filter_result?: string
  action?: string
  reasoning?: string
  risk?: string
  total_score?: number
  valuation?: string
}

export interface PortfolioAdvice {
  advice_id: string
  status: 'GENERATING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  current_step?: string
  prescription?: AdviceItem[]
  cio_verdict?: string
  analyst_assessment?: string
  strategist_assessment?: string
  scout_assessment?: string
  contrarian_assessment?: string
  debate_history?: string
  macro_judge_verdict?: string
  market_intel?: MarketIntel
  stock_candidates?: StockCandidate[]
  stock_judge_verdict?: string
  risk_director_review?: string
  market_debate_history?: string
  stock_debate_history?: string
  elapsed_seconds?: number
  created_at: string
  completed_at?: string
  error?: string
  data_score?: number
  selected_industries?: string[]
  buy_signals?: Record<string, BuySignalItem>
  market_signals?: MarketSignalSnapshot
}

export interface BuySignalItem {
  code: string
  name: string
  signal: string // STRONG_BUY/BUY/HOLD/REDUCE/SELL
  confidence: string // 高/中/低
  total_score: number
  quality_score: number
  valuation_score: number
  sentiment_score: number
  fund_flow_score: number
  lights: Record<string, string> // {quality, valuation, sentiment, fund_flow}
  price_range: string
  timing: string
}

export interface MarketSignalSnapshot {
  north_net: number
  north_days: number
  flow_signal: string
  breadth: { breadth_signal: string; up_ratio: number; limit_up: number; limit_down: number }
  macro: { pmi: number; shibor_on: number }
}

export const portfolioApi = {
  async getAccount() {
    return ApiClient.get<PortfolioAccountInfo>('/api/portfolio/account')
  },
  async updateAccount(data: UpdateAccountPayload) {
    return ApiClient.put<{ message: string }>('/api/portfolio/account', data)
  },
  async getSummary() {
    return ApiClient.get<PortfolioSummary>('/api/portfolio/summary')
  },
  async getPositions() {
    return ApiClient.get<{ items: PortfolioPositionItem[] }>('/api/portfolio/positions')
  },
  async addPosition(data: AddPositionPayload) {
    return ApiClient.post<{ message: string; code: string; market: string }>(
      '/api/portfolio/positions',
      data,
      { showLoading: true }
    )
  },
  async updatePosition(code: string, data: UpdatePositionPayload) {
    return ApiClient.put<{ message: string; code: string }>(
      `/api/portfolio/positions/${encodeURIComponent(code)}`,
      data
    )
  },
  async deletePosition(code: string) {
    return ApiClient.delete<{ message: string; code: string }>(
      `/api/portfolio/positions/${encodeURIComponent(code)}`
    )
  },
  async placeOrder(data: PlaceOrderPayload) {
    return ApiClient.post<{ order: PaperOrderItem }>('/api/portfolio/order', data, {
      showLoading: true
    })
  },
  async getOrders(limit = 50) {
    return ApiClient.get<{ items: PaperOrderItem[] }>('/api/portfolio/orders', { limit })
  },
  async resetAccount() {
    return ApiClient.post<{ message: string }>('/api/portfolio/reset?confirm=true')
  },
  async generateAdvice() {
    return ApiClient.post<{ advice_id: string; status: string }>(
      '/api/portfolio/advice',
      {},
      { showLoading: true }
    )
  },
  async getLatestAdvice() {
    return ApiClient.get<PortfolioAdvice>('/api/portfolio/advice/latest')
  },
  async getAdvice(adviceId: string) {
    return ApiClient.get<PortfolioAdvice>(`/api/portfolio/advice/${adviceId}`)
  },
  async getAdviceHistory(page = 1, pageSize = 10) {
    return ApiClient.get<{ items: PortfolioAdvice[]; total: number }>('/api/portfolio/advice', {
      page,
      page_size: pageSize
    })
  },
  // 两阶段分析
  async startL1Plan(goal: string = '') {
    return ApiClient.post<{ task_id: string; status: string }>(
      '/api/portfolio/analysis/plan',
      { goal },
      { showLoading: true }
    )
  },
  async executeAnalysis(taskId: string, selectedIndustries: string[]) {
    return ApiClient.post<{ task_id: string; status: string }>(
      '/api/portfolio/analysis/execute',
      { task_id: taskId, selected_industries: selectedIndustries },
      { showLoading: true }
    )
  },
  async getAnalysisStatus(taskId: string) {
    return ApiClient.get<{ status: string; progress: number; result?: any; current_step?: string }>(
      `/api/portfolio/analysis/${taskId}/status`
    )
  },
  async getPortfolioOverview() {
    return ApiClient.get<{
      matrix: IndustryOverviewRow[]
      total_industries: number
      covered_count: number
      stale_count: number
      never_count: number
      planned_count: number
      latest_advice_at: string
      data_score: number
    }>('/api/portfolio/overview')
  }
}

export interface IndustryOverviewRow {
  industry: string
  market: string
  lifecycle: string
  depth: string
  go_nogo: string
  vitality_level?: string // v3: 景气强度（强烈看好/看好/中性/看空）
  gap?: number // v3: 配额缺口
  source?: string // v3: 入池来源（holding/watchlist/vitality）
  confidence: string
  coverage_status?: 'covered' | 'stale' | 'never' | 'planned'
  analyzed_at: string
  holdings_weight: number
  target_weight: number
  delta: number
  position_count: number
  position_codes: string[]
  position_names: string[]
  positions_detail?: AdviceItem[]  // v3: 该行业下个股处方列表
  reasoning: string
  advice_id: string
  prescriptions: AdviceItem[]
}

// 向后兼容
export const paperApi = portfolioApi
