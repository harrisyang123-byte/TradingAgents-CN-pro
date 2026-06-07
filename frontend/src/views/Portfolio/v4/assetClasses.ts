// assetClasses.ts — 七大类资产前端常量（须与后端 app/services/v4/asset_classes.py 一致）
//
// 状态颜色语言（NFR3.1）与下钻深度语义（AC1.3）的唯一前端真源。
// 概览接口也会下发 asset_classes（同源），此处常量用于离线/快照与颜色映射。

import type { UnitStatus } from '@/api/portfolioV4'

export interface AssetClassDef {
  key: string
  label: string
  color: string
  maxDrillDepth: 'industry_stock' | 'instrument' | 'holding_structure'
}

export const ASSET_CLASSES: AssetClassDef[] = [
  { key: 'equity', label: '权益', color: '#f56c6c', maxDrillDepth: 'industry_stock' },
  { key: 'fixed_income', label: '固定收益', color: '#409eff', maxDrillDepth: 'instrument' },
  { key: 'cash', label: '现金及等价物', color: '#909399', maxDrillDepth: 'holding_structure' },
  { key: 'commodity', label: '大宗商品', color: '#e6a23c', maxDrillDepth: 'instrument' },
  { key: 'precious_metal', label: '贵金属', color: '#d4af37', maxDrillDepth: 'instrument' },
  { key: 'real_estate', label: '房地产', color: '#67c23a', maxDrillDepth: 'instrument' },
  { key: 'alternative', label: '另类投资', color: '#9b59b6', maxDrillDepth: 'instrument' },
]

const _byKey: Record<string, AssetClassDef> = Object.fromEntries(
  ASSET_CLASSES.map((c) => [c.key, c]),
)

export function classLabel(key: string): string {
  if (key === 'unclassified') return '待人工归类'
  return _byKey[key]?.label ?? key
}

export function classColor(key: string): string {
  return _byKey[key]?.color ?? '#c0c4cc'
}

export function isEquity(key: string): boolean {
  return key === 'equity'
}

// ── 五色状态语言（FR-004 状态机） ─────────────────────────────────────
export interface StatusStyle {
  color: string
  bg: string
  label: string
  icon: string // Element Plus icon name 或 emoji
  type: '' | 'success' | 'warning' | 'danger' | 'info'
}

export const STATUS_STYLES: Record<UnitStatus, StatusStyle> = {
  gray: { color: '#909399', bg: '#f4f4f5', label: '未分析', icon: '○', type: 'info' },
  blue: { color: '#409eff', bg: '#ecf5ff', label: '分析中', icon: '◐', type: '' },
  green: { color: '#67c23a', bg: '#f0f9eb', label: '新鲜', icon: '●', type: 'success' },
  yellow: { color: '#e6a23c', bg: '#fdf6ec', label: '建议刷新', icon: '◑', type: 'warning' },
  red: { color: '#f56c6c', bg: '#fef0f0', label: '失败', icon: '✕', type: 'danger' },
}

export function statusStyle(status: string): StatusStyle {
  return STATUS_STYLES[(status as UnitStatus)] ?? STATUS_STYLES.gray
}
