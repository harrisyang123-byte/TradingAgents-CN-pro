// useV4Units.ts — v4 单元数据 composable（FR-008 / FR-009 双来源同构）
//
// 统一封装三层 Tab 的数据加载，自动适配「API / 静态快照」两来源（由 portfolioV4Api 内部判定）。
// 只读语义：仅取缓存产物，绝不触发分析（触发走 CLI，见各单元 cli_hint）。

import { ref, shallowRef } from 'vue'
import {
  portfolioV4Api,
  type V4Overview,
  type AssetDetail,
  type IndustryDetail,
  type UnitMeta,
} from '@/api/portfolioV4'

export function useV4Overview() {
  const overview = shallowRef<V4Overview | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const resp = await portfolioV4Api.getOverview()
      if (resp.success) {
        overview.value = resp.data
      } else {
        error.value = resp.message || '加载失败'
      }
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }

  return { overview, loading, error, load }
}

export function useAssetDetail() {
  const detail = shallowRef<AssetDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(assetClass: string) {
    loading.value = true
    error.value = null
    detail.value = null
    try {
      const resp = await portfolioV4Api.getAssetDetail(assetClass)
      if (resp.success) {
        detail.value = resp.data
      } else {
        error.value = resp.message || '加载失败'
      }
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }

  return { detail, loading, error, load }
}

export function useIndustryDetail() {
  const detail = shallowRef<IndustryDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(name: string) {
    loading.value = true
    error.value = null
    detail.value = null
    try {
      const resp = await portfolioV4Api.getIndustryDetail(name)
      if (resp.success) {
        detail.value = resp.data
      } else {
        error.value = resp.message || '加载失败'
      }
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }

  return { detail, loading, error, load }
}

export function useUnitsStatus() {
  const units = ref<UnitMeta[]>([])
  const hasData = ref(false)
  const loading = ref(false)

  async function load() {
    loading.value = true
    try {
      const resp = await portfolioV4Api.getUnitsStatus()
      if (resp.success) {
        units.value = resp.data.units || []
        hasData.value = resp.data.has_data
      }
    } catch {
      units.value = []
    } finally {
      loading.value = false
    }
  }

  return { units, hasData, loading, load }
}
