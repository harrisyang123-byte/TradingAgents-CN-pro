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
  debate_history?: string
  elapsed_seconds?: number
  created_at: string
  completed_at?: string
  error?: string
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
      '/api/portfolio/positions', data, { showLoading: true }
    )
  },
  async updatePosition(code: string, data: UpdatePositionPayload) {
    return ApiClient.put<{ message: string; code: string }>(
      `/api/portfolio/positions/${encodeURIComponent(code)}`, data
    )
  },
  async deletePosition(code: string) {
    return ApiClient.delete<{ message: string; code: string }>(
      `/api/portfolio/positions/${encodeURIComponent(code)}`
    )
  },
  async placeOrder(data: PlaceOrderPayload) {
    return ApiClient.post<{ order: PaperOrderItem }>(
      '/api/portfolio/order', data, { showLoading: true }
    )
  },
  async getOrders(limit = 50) {
    return ApiClient.get<{ items: PaperOrderItem[] }>('/api/portfolio/orders', { limit })
  },
  async resetAccount() {
    return ApiClient.post<{ message: string }>('/api/portfolio/reset?confirm=true')
  },
  async generateAdvice() {
    return ApiClient.post<{ advice_id: string; status: string }>(
      '/api/portfolio/advice', {}, { showLoading: true }
    )
  },
  async getLatestAdvice() {
    return ApiClient.get<PortfolioAdvice>('/api/portfolio/advice/latest')
  },
  async getAdvice(adviceId: string) {
    return ApiClient.get<PortfolioAdvice>(`/api/portfolio/advice/${adviceId}`)
  },
  async getAdviceHistory(page = 1, pageSize = 10) {
    return ApiClient.get<{ items: PortfolioAdvice[]; total: number }>(
      '/api/portfolio/advice', { page, page_size: pageSize }
    )
  }
}

// 向后兼容
export const paperApi = portfolioApi
