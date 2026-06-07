<template>
  <div
    class="asset-card"
    :class="{ 'ac-zeroed': card.actively_zeroed, 'ac-clickable': clickable }"
    :style="{ borderTopColor: classColor(card.asset_class) }"
    @click="clickable && $emit('open', card.asset_class)"
  >
    <div class="ac-head">
      <span class="ac-dot" :style="{ background: classColor(card.asset_class) }"></span>
      <span class="ac-label">{{ card.label }}</span>
      <UnitStatusBadge
        :status="card.status"
        :stale-reason="card.stale_reason"
        :cli-hint="card.cli_hint"
        :meta="card"
      />
    </div>

    <!-- 当前 → 目标 配比 -->
    <div class="ac-alloc">
      <div class="ac-alloc-item">
        <div class="ac-alloc-val">{{ fmtPct(card.current_weight) }}</div>
        <div class="ac-alloc-cap">现状</div>
      </div>
      <div class="ac-arrow">→</div>
      <div class="ac-alloc-item">
        <div class="ac-alloc-val ac-target">
          <span v-if="card.target_weight != null">{{ fmtPct(card.target_weight) }}</span>
          <span v-else class="ac-muted">--</span>
        </div>
        <div class="ac-alloc-cap">目标</div>
      </div>
      <div class="ac-action">
        <el-tag v-if="card.actively_zeroed" type="info" size="small" effect="plain">主动归零</el-tag>
        <el-tag v-else-if="actionType" :type="actionType.type" size="small" effect="plain">
          {{ actionType.label }}
        </el-tag>
      </div>
    </div>

    <!-- 研判摘要 -->
    <div class="ac-summary">
      <el-tag v-if="card.stance" :type="stanceType" size="small" class="ac-stance">
        {{ stanceLabel }}
      </el-tag>
      <span v-if="card.summary" class="ac-summary-text">{{ card.summary }}</span>
      <span v-else class="ac-muted">{{ card.exists ? '无研判摘要' : '尚未分析 — ' + drillHint }}</span>
    </div>

    <div v-if="card.max_drill_depth === 'industry_stock'" class="ac-foot">点击下钻：行业 → 个股</div>
    <div v-else-if="clickable" class="ac-foot">点击查看：投资方案</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import UnitStatusBadge from './UnitStatusBadge.vue'
import { classColor } from './assetClasses'
import type { AssetCardData } from '@/api/portfolioV4'

const props = withDefaults(
  defineProps<{ card: AssetCardData; clickable?: boolean }>(),
  { clickable: true },
)

defineEmits<{ (e: 'open', assetClass: string): void }>()

const actionType = computed(() => {
  const a = props.card.action
  if (a === 'add') return { type: 'success' as const, label: '加配' }
  if (a === 'reduce') return { type: 'danger' as const, label: '减配' }
  if (a === 'clear') return { type: 'info' as const, label: '清仓' }
  if (a === 'hold') return { type: 'warning' as const, label: '维持' }
  return null
})

const stanceLabel = computed(() => {
  return { bullish: '看多', bearish: '看空', neutral: '中性' }[props.card.stance || ''] || props.card.stance
})
const stanceType = computed(() => {
  return (
    { bullish: 'success', bearish: 'danger', neutral: 'info' }[props.card.stance || ''] || 'info'
  ) as 'success' | 'danger' | 'info'
})

const drillHint = computed(() => props.card.cli_hint)

function fmtPct(v: number | null | undefined): string {
  if (v == null) return '--'
  return `${Number(v).toFixed(1)}%`
}
</script>

<style scoped>
.asset-card {
  border: 1px solid #ebeef5;
  border-top: 3px solid #c0c4cc;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
  transition: box-shadow 0.2s, transform 0.2s;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ac-clickable {
  cursor: pointer;
}
.ac-clickable:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
.ac-zeroed {
  opacity: 0.72;
}
.ac-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ac-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.ac-label {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
  flex: 1;
}
.ac-alloc {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ac-alloc-item {
  text-align: center;
}
.ac-alloc-val {
  font-size: 18px;
  font-weight: 700;
  color: #606266;
}
.ac-target {
  color: #409eff;
}
.ac-alloc-cap {
  font-size: 11px;
  color: #909399;
}
.ac-arrow {
  color: #c0c4cc;
  font-size: 16px;
}
.ac-action {
  margin-left: auto;
}
.ac-summary {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
  display: flex;
  gap: 6px;
  align-items: flex-start;
}
.ac-stance {
  flex-shrink: 0;
}
.ac-summary-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ac-muted {
  color: #c0c4cc;
}
.ac-foot {
  font-size: 11px;
  color: #909399;
  border-top: 1px dashed #ebeef5;
  padding-top: 8px;
}
</style>
