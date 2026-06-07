<template>
  <div class="stock-table-wrap">
    <EmptyUnitState
      v-if="!rows.length"
      title="尚无个股分析"
      description="行业方向与权重确定后，由独立「行业内研究部门」对每只个股独立分析。"
      :cli-hint="`./scripts/run_v4.sh analyze stock:<代码>`"
    />

    <el-table v-else :data="rows" border size="default">
      <el-table-column label="个股" min-width="160">
        <template #default="{ row }">
          <div class="st-name">
            <b>{{ row.name || row.code }}</b>
            <span v-if="row.code" class="st-code">{{ row.code }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <UnitStatusBadge
            :status="row.status || 'gray'"
            :stale-reason="row.stale_reason"
            :cli-hint="row.cli_hint"
            :meta="row.meta"
          />
        </template>
      </el-table-column>
      <el-table-column label="评级" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.rating" :type="ratingType(row.rating)" size="small">{{ row.rating }}</el-tag>
          <span v-else class="st-muted">--</span>
        </template>
      </el-table-column>
      <el-table-column label="目标价" width="110" align="center">
        <template #default="{ row }">
          <span v-if="row.target_price != null">{{ row.target_price }}</span>
          <span v-else class="st-muted">--</span>
        </template>
      </el-table-column>
      <el-table-column label="目标权重" width="110" align="center">
        <template #default="{ row }">
          <b v-if="row.target_weight != null" class="st-weight">{{ fmtPct(row.target_weight) }}</b>
          <span v-else class="st-muted">--</span>
        </template>
      </el-table-column>
      <el-table-column label="买入区间" min-width="140" align="center">
        <template #default="{ row }">
          <span v-if="row.entry_price_range">{{ fmtRange(row.entry_price_range) }}</span>
          <span v-else class="st-muted">--</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import EmptyUnitState from './EmptyUnitState.vue'
import type { StockUnit, StockWeightRow } from '@/api/portfolioV4'

const props = defineProps<{
  stocks: StockUnit[]
  stockWeights: StockWeightRow[]
}>()

// 合并个股分析单元与行业内配比权重（按 code 关联）
const rows = computed(() => {
  const weightByCode: Record<string, StockWeightRow> = {}
  for (const w of props.stockWeights || []) {
    if (w.code) weightByCode[w.code] = w
  }
  const seen = new Set<string>()
  const out: any[] = []
  for (const s of props.stocks || []) {
    const code = s.code || ''
    seen.add(code)
    const w = weightByCode[code]
    out.push({
      code,
      name: s.name,
      status: s.status,
      stale_reason: s.stale_reason,
      cli_hint: s.cli_hint,
      meta: s,
      rating: s.rating,
      target_price: s.target_price,
      target_weight: w?.target_weight ?? null,
      entry_price_range: w?.entry_price_range ?? null,
    })
  }
  // 有配比但无个股单元的（行业内配比先于个股缓存到位的边界）
  for (const w of props.stockWeights || []) {
    if (w.code && !seen.has(w.code)) {
      out.push({
        code: w.code,
        name: w.code,
        status: 'gray',
        rating: null,
        target_price: null,
        target_weight: w.target_weight,
        entry_price_range: w.entry_price_range ?? null,
      })
    }
  }
  return out
})

function ratingType(r: string): 'success' | 'warning' | 'danger' | 'info' {
  const s = String(r).toLowerCase()
  if (s.includes('买') || s.includes('增持') || s.includes('buy') || s.includes('overweight')) return 'success'
  if (s.includes('减') || s.includes('卖') || s.includes('sell') || s.includes('underweight')) return 'danger'
  if (s.includes('中性') || s.includes('hold') || s.includes('neutral')) return 'warning'
  return 'info'
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return '--'
  return `${Number(v).toFixed(1)}%`
}

function fmtRange(r: string | number[] | undefined): string {
  if (!r) return '--'
  if (Array.isArray(r)) return r.join(' ~ ')
  return String(r)
}
</script>

<style scoped>
.st-name { display: flex; flex-direction: column; }
.st-code { font-size: 11px; color: #909399; }
.st-muted { color: #c0c4cc; }
.st-weight { color: #409eff; }
</style>
