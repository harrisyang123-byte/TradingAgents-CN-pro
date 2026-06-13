<template>
  <div class="hr-wrap">
    <div v-if="!review" class="hr-hint">
      暂无持仓体检数据。请先跑 <code>build_snapshot_v4.py</code> 生成 holdings_review.json。
    </div>

    <template v-else>
      <!-- 组合体检摘要 -->
      <div class="hr-summary">
        <div class="hr-sum-item">
          <div class="hr-sum-label">组合总值</div>
          <div class="hr-sum-val">¥{{ fmt(review.summary.total_value) }}</div>
        </div>
        <div class="hr-sum-item">
          <div class="hr-sum-label">股票 / 基金 / 现金</div>
          <div class="hr-sum-val sm">
            {{ review.summary.stock_pct }}% / {{ review.summary.fund_pct }}% / {{ review.summary.cash_pct }}%
          </div>
        </div>
        <div class="hr-sum-item">
          <div class="hr-sum-label">已深度分析</div>
          <div class="hr-sum-val sm">{{ review.summary.analyzed_count }} / {{ review.summary.total_stocks }} 只股票</div>
        </div>
        <div class="hr-sum-item alert">
          <div class="hr-sum-label">待处理动作</div>
          <div class="hr-sum-val">{{ review.summary.pending_actions }} 项</div>
        </div>
      </div>

      <!-- 直接持股 -->
      <div class="hr-section-title">📈 直接持股（{{ review.stocks.length }} 只） — 点「查看分析」进入个股深度报告</div>
      <table class="hr-table">
        <thead>
          <tr>
            <th>代码</th><th>名称</th><th>市值</th><th>占比</th>
            <th>分析状态</th><th>结论</th><th>处理动作</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in review.stocks" :key="s.code">
            <td class="mono">{{ s.code }}</td>
            <td>{{ shortName(s.name) }}</td>
            <td>¥{{ fmt(s.market_value) }}</td>
            <td>{{ s.weight }}%</td>
            <td>
              <span v-if="s.analyzed" class="tag green">已分析 ✓</span>
              <span v-else class="tag gray">待分析</span>
            </td>
            <td>
              <span v-if="s.analyzed" class="stance" :class="stanceCls(s.stance)">{{ s.stance }}</span>
              <span v-else class="muted">—</span>
            </td>
            <td class="action-cell">
              <span v-if="s.action">{{ s.action }}</span>
              <span v-else class="muted">尚未生成处理建议（待 8 step 深度分析）</span>
            </td>
            <td>
              <a v-if="s.analyzed" class="link" @click="$emit('open-stock', s.code)">查看分析 →</a>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 基金穿透处理（同主题合并） -->
      <div class="hr-section-title">
        🪙 基金穿透处理（{{ review.summary.total_funds }} 只基金 ¥{{ fmt(review.summary.fund_value) }}）
        — 同主题重复 = 拖累费率，下方给合并动作
      </div>
      <div class="hr-fund-groups">
        <div v-for="(g, i) in review.fund_groups" :key="i" class="hr-fund-group">
          <div class="hr-fg-head">
            <b>{{ g.theme }}</b>
            <span class="hr-fg-meta">{{ g.fund_count }} 只 · ¥{{ fmt(g.total_mv) }}</span>
            <span v-if="g.release_mv > 0" class="hr-fg-release">可释放 ¥{{ fmt(g.release_mv) }}</span>
          </div>
          <div class="hr-fg-action">💡 {{ g.action }}</div>
          <div class="hr-fg-funds">
            <span v-for="f in g.keep" :key="f.code" class="fund-pill keep">保留 {{ shortName(f.name) }}</span>
            <span v-for="f in g.sell" :key="f.code" class="fund-pill sell">卖 {{ shortName(f.name) }} ¥{{ fmt(f.mv) }}</span>
          </div>
        </div>
      </div>

      <!-- 未重叠基金 -->
      <div v-if="review.ungrouped_funds.length" class="hr-ungrouped">
        <span class="hr-ug-label">无重复（保持）：</span>
        <span v-for="f in review.ungrouped_funds" :key="f.code" class="fund-pill plain">
          {{ shortName(f.name) }} ¥{{ fmt(f.market_value) }}
        </span>
      </div>

      <!-- 间接持仓提示 -->
      <div v-if="review.indirect_holdings.length" class="hr-section-title">
        📊 间接持仓提示 — 你已通过基金间接持有这些股票，直接加仓前先算总暴露
      </div>
      <table v-if="review.indirect_holdings.length" class="hr-table compact">
        <tbody>
          <tr v-for="ih in review.indirect_holdings" :key="ih.code">
            <td class="mono">{{ ih.code }}</td>
            <td>{{ ih.name }}</td>
            <td>间接 ¥{{ fmt(ih.indirect_value) }}</td>
            <td>经 {{ ih.fund_count }} 只基金</td>
            <td class="action-cell">{{ ih.note }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 风格暴露 -->
      <div class="hr-section-title">📐 组合风格暴露</div>
      <div class="hr-style">
        <div><b>地区：</b>{{ dist(review.summary.style_region) }}</div>
        <div><b>基金类型：</b>{{ dist(review.summary.style_fund_type) }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { portfolioV4Api, type HoldingsReview } from '@/api/portfolioV4'

defineEmits<{ (e: 'open-stock', code: string): void }>()

const review = ref<HoldingsReview | null>(null)

async function load() {
  try {
    const resp = await portfolioV4Api.getHoldingsReview()
    review.value = (resp as any)?.data ?? (resp as any) ?? null
  } catch {
    review.value = null
  }
}
load()

function fmt(v?: number): string {
  if (v == null) return '0'
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}
function shortName(n?: string): string {
  if (!n) return ''
  return n.length > 16 ? n.slice(0, 16) + '…' : n
}
function stanceCls(stance?: string | null): string {
  if (!stance) return ''
  if (stance.includes('减') || stance.includes('卖')) return 'reduce'
  if (stance.includes('加') || stance.includes('买')) return 'add'
  return 'hold'
}
function dist(d?: Record<string, number>): string {
  if (!d) return '-'
  const total = Object.values(d).reduce((a, b) => a + b, 0)
  if (total <= 0) return '-'
  return Object.entries(d)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${k} ${(v / total * 100).toFixed(0)}%`)
    .join(' / ')
}
</script>

<style scoped>
.hr-wrap { padding: 4px; }
.hr-hint { text-align: center; padding: 40px; color: #909399; }
.hr-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.hr-sum-item {
  background: #f7f9fc;
  border-radius: 8px;
  padding: 12px 16px;
  border-left: 3px solid #409eff;
}
.hr-sum-item.alert { border-left-color: #faad14; background: #fffbe6; }
.hr-sum-label { font-size: 12px; color: #909399; }
.hr-sum-val { font-size: 20px; font-weight: 700; color: #303133; margin-top: 4px; }
.hr-sum-val.sm { font-size: 15px; }
.hr-section-title {
  font-size: 14px; font-weight: 600; color: #303133;
  margin: 22px 0 10px; padding-left: 8px; border-left: 3px solid #409eff;
}
.hr-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.hr-table th {
  text-align: left; padding: 8px 10px; color: #909399;
  font-weight: 500; border-bottom: 2px solid #ebeef5; font-size: 12px;
}
.hr-table td { padding: 9px 10px; border-bottom: 1px solid #f0f2f5; color: #4e5969; vertical-align: top; }
.hr-table.compact td { padding: 6px 10px; }
.mono { font-family: monospace; color: #303133; }
.action-cell { font-size: 12px; line-height: 1.5; max-width: 360px; }
.muted { color: #c0c4cc; font-size: 12px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.tag.green { background: #f0f9eb; color: #67c23a; }
.tag.gray { background: #f4f4f5; color: #909399; }
.stance { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.stance.reduce { background: #fef0f0; color: #f56c6c; }
.stance.add { background: #f0f9eb; color: #67c23a; }
.stance.hold { background: #fdf6ec; color: #e6a23c; }
.link { color: #409eff; cursor: pointer; font-size: 12px; white-space: nowrap; }
.link:hover { text-decoration: underline; }
.hr-fund-groups { display: flex; flex-direction: column; gap: 10px; }
.hr-fund-group { background: #fafafa; border-radius: 8px; padding: 12px 14px; border-left: 3px solid #faad14; }
.hr-fg-head { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #303133; }
.hr-fg-meta { font-size: 12px; color: #909399; }
.hr-fg-release { font-size: 12px; color: #d46b08; background: #fff7e6; padding: 1px 8px; border-radius: 10px; font-weight: 600; }
.hr-fg-action { font-size: 12.5px; color: #c45656; margin: 6px 0 8px; line-height: 1.5; }
.hr-fg-funds { display: flex; flex-wrap: wrap; gap: 6px; }
.fund-pill { font-size: 11.5px; padding: 2px 8px; border-radius: 4px; }
.fund-pill.keep { background: #f0f9eb; color: #67c23a; }
.fund-pill.sell { background: #fef0f0; color: #f56c6c; }
.fund-pill.plain { background: #f4f4f5; color: #606266; }
.hr-ungrouped { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.hr-ug-label { font-size: 12px; color: #909399; }
.hr-style { font-size: 13px; color: #4e5969; line-height: 1.9; }
.hr-style b { color: #303133; }
</style>
