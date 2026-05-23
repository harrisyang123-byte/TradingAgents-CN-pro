<template>
  <div class="decision-card" :class="[`priority-${item.priority || 'optional'}`]">
    <!-- Header: action + code/name + priority -->
    <div class="card-header">
      <div class="header-left">
        <el-tag :type="actionTag" size="small" effect="dark">{{ actionLabel }}</el-tag>
        <span class="stock-name">{{ item.name || item.code }}</span>
        <span class="stock-code">{{ item.code }}</span>
      </div>
      <div class="header-right">
        <el-tag :type="priorityTag" size="small" effect="plain">{{ priorityLabel }}</el-tag>
        <span class="weight-change">
          <template v-if="item.action === 'new_position' || item.action === 'buy'">
            新建仓 → {{ item.target_weight?.toFixed(0) }}%
          </template>
          <template v-else>
            {{ item.current_weight?.toFixed(0) }}% → {{ item.target_weight?.toFixed(0) }}%
          </template>
        </span>
      </div>
    </div>

    <!-- Context: l1 + l2 (collapsible) -->
    <div v-if="hasContext" class="card-context" @click="expanded = !expanded">
      <div class="context-toggle">
        <svg :class="{ rotated: expanded }" width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
          <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/>
        </svg>
        <span>决策上下文</span>
      </div>
      <div v-if="expanded" class="context-body">
        <div v-if="item.l1_context" class="context-item l1">
          <span class="context-label">行业方向</span>
          <span>{{ item.l1_context }}</span>
        </div>
        <div v-if="item.l2_context" class="context-item l2">
          <span class="context-label">护城河</span>
          <span>{{ item.l2_context }}</span>
        </div>
      </div>
    </div>

    <!-- Price Anchor: suggested_price + PE bar -->
    <div v-if="item.suggested_price" class="card-price">
      <div class="price-text">{{ item.suggested_price }}</div>
      <div v-if="pePercentile !== null" class="pe-bar-container">
        <div class="pe-bar">
          <div class="pe-fill" :style="{ width: peFillWidth }" :class="peColorClass" />
        </div>
        <span class="pe-label">{{ pePercentile }}% 分位 · {{ peLabel }}</span>
      </div>
    </div>

    <!-- Risk Row -->
    <div class="card-risk">
      <div class="risk-item" v-if="item.max_loss_pct">
        <span class="risk-icon">⚠️</span>
        <span class="risk-text">{{ item.max_loss_pct }}</span>
      </div>
      <div class="risk-item" v-if="item.five_year_view">
        <span class="risk-icon">📅</span>
        <span class="risk-text">{{ item.five_year_view }}</span>
      </div>
      <div class="risk-item" v-if="item.bias_check">
        <span class="risk-icon">🧠</span>
        <span class="risk-text">{{ item.bias_check }}</span>
      </div>
      <div v-if="!item.max_loss_pct && !item.five_year_view && !item.bias_check" class="risk-item muted">
        —
      </div>
    </div>

    <!-- Reasoning (footer) -->
    <div v-if="item.reasoning" class="card-reasoning">
      {{ item.reasoning }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AdviceItem } from '@/api/paper'

const props = defineProps<{
  item: AdviceItem
}>()

const expanded = ref(false)

// --- action ---
const actionTag = computed(() => {
  const a = props.item.action
  if (a === 'buy' || a === 'add' || a === 'new_position') return 'success'
  if (a === 'sell' || a === 'reduce') return 'danger'
  return 'info'
})

const actionLabel = computed(() => {
  const map: Record<string, string> = {
    buy: '买入', add: '加仓', new_position: '建仓',
    sell: '清仓', reduce: '减仓', hold: '持有'
  }
  return map[props.item.action] || props.item.action
})

// --- priority ---
const priorityTag = computed(() => {
  if (props.item.priority === 'urgent') return 'danger'
  if (props.item.priority === 'important') return 'warning'
  return 'info'
})

const priorityLabel = computed(() => {
  if (props.item.priority === 'urgent') return '紧急'
  if (props.item.priority === 'important') return '建议'
  return '参考'
})

// --- context ---
const hasContext = computed(() => !!(props.item.l1_context || props.item.l2_context))

// --- PE percentile bar ---
const pePercentile = computed(() => {
  const txt = props.item.suggested_price || ''
  const m = txt.match(/(\d+\.?\d*)\s*%\s*分位/)
  return m ? parseFloat(m[1]) : null
})

const peFillWidth = computed(() => {
  if (pePercentile.value === null) return '0%'
  return `${pePercentile.value}%`
})

const peColorClass = computed(() => {
  if (pePercentile.value === null) return ''
  if (pePercentile.value <= 25) return 'pe-low'
  if (pePercentile.value <= 75) return 'pe-mid'
  return 'pe-high'
})

const peLabel = computed(() => {
  if (pePercentile.value === null) return ''
  if (pePercentile.value <= 25) return '低估'
  if (pePercentile.value <= 75) return '合理'
  return '高估'
})
</script>

<style scoped>
.decision-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  background: #fff;
  transition: box-shadow 0.2s;
}
.decision-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.decision-card.priority-urgent { border-left: 4px solid #f56c6c; }
.decision-card.priority-important { border-left: 4px solid #e6a23c; }
.decision-card.priority-optional { border-left: 4px solid #c0c4cc; }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.stock-name { font-weight: 600; font-size: 15px; }
.stock-code { font-size: 12px; color: #909399; }
.header-right { display: flex; align-items: center; gap: 8px; }
.weight-change { font-size: 13px; color: #606266; }

/* Context */
.card-context { margin: 8px 0; cursor: pointer; }
.context-toggle {
  display: flex; align-items: center; gap: 4px;
  font-size: 13px; color: #909399; user-select: none;
}
.context-toggle svg { transition: transform 0.2s; }
.context-toggle svg.rotated { transform: rotate(90deg); }
.context-body { margin-top: 8px; padding: 8px 12px; background: #f5f7fa; border-radius: 6px; }
.context-item { font-size: 13px; margin-bottom: 4px; display: flex; gap: 8px; }
.context-label { color: #909399; min-width: 56px; flex-shrink: 0; }

/* Price */
.card-price {
  margin: 12px 0;
  padding: 10px 12px;
  background: #f0f9ff;
  border-radius: 6px;
}
.price-text { font-size: 13px; color: #303133; margin-bottom: 6px; }
.pe-bar-container { display: flex; align-items: center; gap: 8px; }
.pe-bar {
  flex: 1; height: 8px; background: #e4e7ed; border-radius: 4px; overflow: hidden;
}
.pe-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.pe-fill.pe-low { background: #67c23a; }
.pe-fill.pe-mid { background: #e6a23c; }
.pe-fill.pe-high { background: #f56c6c; }
.pe-label { font-size: 12px; color: #909399; white-space: nowrap; }

/* Risk */
.card-risk {
  display: flex; flex-wrap: wrap; gap: 12px;
  margin-top: 8px; padding-top: 8px;
  border-top: 1px solid #ebeef5;
}
.risk-item { display: flex; align-items: flex-start; gap: 4px; font-size: 12px; color: #606266; flex: 1; min-width: 160px; }
.risk-item.muted { color: #c0c4cc; }
.risk-icon { flex-shrink: 0; font-size: 13px; }
.risk-text { line-height: 1.4; }

/* Reasoning */
.card-reasoning {
  margin-top: 8px; font-size: 13px; color: #606266;
  line-height: 1.5; font-style: italic;
}
</style>
