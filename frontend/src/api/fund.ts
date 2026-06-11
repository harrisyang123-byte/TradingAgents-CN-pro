import { ApiClient } from './request'

export interface FundBasicInfo {
  code: string
  name?: string
  type?: string
  scale?: number
  establishment_date?: string
  manager?: string
}

export interface FundHolding {
  stock_code: string
  stock_name: string
  ratio: number
  change: number | null
}

export interface FundSector {
  sector_name: string
  ratio: number
}

export const fundApi = {
  async getBasicInfo(code: string) {
    return ApiClient.get<FundBasicInfo>(
      '/api/fund/basic-info',
      { code },
      { skipErrorHandler: true }
    )
  },
  async getTopHoldings(code: string) {
    return ApiClient.get<FundHolding[]>(
      '/api/fund/top-holdings',
      { code },
      { skipErrorHandler: true }
    )
  },
  async getSectorDistribution(code: string) {
    return ApiClient.get<FundSector[]>(
      '/api/fund/sector-distribution',
      { code },
      { skipErrorHandler: true }
    )
  }
}
