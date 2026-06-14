<template>
  <div class="dt-wrap">
    <div v-if="!review" class="dt-hint">暂无数据，请先跑 build_snapshot_v4.py</div>

    <template v-else>
      <!-- 顶部摘要 -->
      <div class="dt-summary">
        <div class="dt-sum"><span>组合总值</span><b>¥{{ fmt(review.summary.total_value) }}</b></div>
        <div class="dt-sum"><span>已深度分析</span><b>{{ review.summary.analyzed_count }}/{{ review.summary.total_stocks }} 股</b></div>
        <div class="dt-sum alert"><span>待处理动作</span><b>{{ review.summary.pending_actions }} 项</b></div>
      </div>

      <!-- 资金流向：同一笔钱怎么动 -->
      <div class="dt-flow">
        <div class="dt-flow-title">💰 这笔钱怎么动（配比是全局的，超配/减仓腾出 → 补到低配处）</div>
        <div class="dt-flow-cols">
          <div class="dt-flow-col">
            <div class="dt-flow-h src">资金来源（卖出/超配/合并释放）</div>
            <div v-for="(s, i) in review.capital_flow.sources" :key="i" class="dt-flow-item">
              <span class="dt-flow-desc">{{ s.desc }}</span>
              <span v-if="s.amount" class="dt-flow-amt src">¥{{ fmt(s.amount) }}</span>
              <span v-else-if="s.note" class="dt-flow-note">{{ s.note }}</span>
            </div>
          </div>
          <div class="dt-flow-col">
            <div class="dt-flow-h use">资金去向（加仓/低配补齐）</div>
            <div v-for="(u, i) in review.capital_flow.uses" :key="i" class="dt-flow-item">
              <span class="dt-flow-desc">{{ u.desc }}</span>
              <span v-if="u.amount" class="dt-flow-amt use">¥{{ fmt(u.amount) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 大类决策树 -->
      <div class="dt-tree-title">📊 大类 → 行业 → 持仓（点行名展开；右侧可看各层分析）</div>
      <div class="dt-tree">
        <div v-for="node in review.asset_tree" :key="node.key" class="dt-class">
          <!-- 大类行 -->
          <div class="dt-class-row" @click="toggle(node.key)">
            <span class="dt-caret">{{ open[node.key] ? '▼' : '▶' }}</span>
            <span class="dt-class-label">{{ node.label }}</span>
            <span class="dt-pct">当前 <b>{{ node.current_pct }}%</b></span>
            <span class="dt-pct" v-if="node.target_pct != null">目标 {{ node.target_pct }}%</span>
            <span v-if="node.action" class="dt-action-tag" :class="actCls(node.action)">{{ actLabel(node.action) }}</span>
            <span v-if="node.gap_value != null && Math.abs(node.gap_value) > 1000"
                  class="dt-gap" :class="node.gap_value > 0 ? 'add' : 'reduce'">
              {{ node.gap_value > 0 ? '需加 ¥' + fmt(node.gap_value) : '超配 ¥' + fmt(-node.gap_value) }}
            </span>
            <a v-if="node.has_class_analysis" class="dt-link" @click.stop="$emit('open-asset', node.key)">大类分析→</a>
          </div>

          <!-- 展开内容 -->
          <div v-show="open[node.key]" class="dt-class-body">
            <!-- 行业（权益） -->
            <div v-for="ind in node.industries" :key="ind.name" class="dt-ind">
              <!-- 行业首行: 名+持仓金额+基金金额+推荐数量 -->
              <div class="dt-ind-row">
                <span class="dt-ind-name">🏭 {{ ind.name }}</span>
                <span class="dt-ind-stats">
                  <template v-if="ind.direct_value > 0">持股 ¥{{ fmt(ind.direct_value) }}</template>
                  <template v-if="(ind.fund_value || 0) > 0"><span v-if="ind.direct_value > 0"> · </span>持基金 ¥{{ fmt(ind.fund_value) }}</template>
                  <template v-if="(ind.rec_count || 0) > 0"><span v-if="ind.direct_value > 0 || (ind.fund_value || 0) > 0"> · </span>推荐 {{ ind.rec_count }}只</template>
                  <span v-if="!ind.direct_value && !(ind.fund_value || 0) && !(ind.rec_count || 0)" class="dt-rec-only">未持仓</span>
                </span>
                <a v-if="ind.has_industry_analysis" class="dt-link" @click="$emit('open-industry', ind.name)">行业分析→</a>
              </div>
              <!-- 表格: 类型/代码/名称/持仓/比例/stance/目标/动作 -->
              <table v-if="ind.holdings.length || (ind.fund_holdings && ind.fund_holdings.length) || (ind.recommendations && ind.recommendations.length)" class="dt-table">
                <thead>
                  <tr>
                    <th>类型</th><th>代码</th><th>名称</th><th>市值/比例</th><th>判断/目标</th><th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <!-- 持仓股 -->
                  <tr v-for="hh in ind.holdings" :key="'h'+hh.code" class="dt-tr-own">
                    <td><span class="dt-pill-own">持股</span></td>
                    <td class="dt-mono">{{ hh.code }}</td>
                    <td>{{ shortName(hh.name) }}</td>
                    <td>¥{{ fmt(hh.market_value) }} · {{ hh.weight }}%</td>
                    <td>
                      <span v-if="hh.analyzed && hh.stance" class="dt-stance" :class="stanceCls(hh.stance)">{{ hh.stance }}</span>
                      <span v-else class="dt-pending">待分析</span>
                    </td>
                    <td>
                      <a v-if="hh.analyzed" class="dt-link sm" @click="$emit('open-stock', hh.code)">分析→</a>
                    </td>
                  </tr>
                  <!-- 持仓基金(行业相关主题基金) -->
                  <tr v-for="fh in (ind.fund_holdings || [])" :key="'fh'+fh.code" class="dt-tr-fund">
                    <td><span class="dt-pill-fund">持基金</span></td>
                    <td class="dt-mono">{{ fh.code }}</td>
                    <td>{{ shortName(fh.name) }}</td>
                    <td>¥{{ fmt(fh.market_value) }} · {{ fh.weight }}%</td>
                    <td><span class="dt-stance hold">主题暴露</span></td>
                    <td>—</td>
                  </tr>
                  <!-- 推荐股(未持仓) -->
                  <tr v-for="rc in (ind.recommendations || [])" :key="'rc'+rc.code" class="dt-tr-rec">
                    <td><span class="dt-pill-rec">推荐</span></td>
                    <td class="dt-mono">{{ rc.code }}</td>
                    <td>{{ shortName(rc.name) }}</td>
                    <td><span class="dt-rec-meta">PE {{ rc.pe || '?' }}x · ROIC {{ rc.roic || '?' }}%</span></td>
                    <td>
                      <span v-if="rc.stance" class="dt-stance" :class="stanceCls(rc.stance)">{{ rc.stance }}</span>
                      <div v-if="rc.target_price" class="dt-rec-target">🎯 {{ rc.target_price }}</div>
                    </td>
                    <td><a class="dt-link sm" @click="$emit('open-stock', rc.code)">分析→</a></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 非权益直接持仓 -->
            <div v-for="dh in node.direct_holdings" :key="dh.code || dh.name" class="dt-hold plain">
              <span class="dt-h-name">{{ shortName(dh.name) }}</span>
              <span class="dt-h-wt">¥{{ fmt(dh.market_value) }}</span>
              <span class="dt-h-wt">{{ dh.weight }}%</span>
            </div>
          </div>
        </div>
      </div>

      <p class="dt-note">{{ review.summary.config_note }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { portfolioV4Api, type HoldingsReview } from '@/api/portfolioV4'

defineEmits<{
  (e: 'open-stock', code: string): void
  (e: 'open-asset', key: string): void
  (e: 'open-industry', name: string): void
}>()

const review = ref<HoldingsReview | null>(null)
const open = reactive<Record<string, boolean>>({})

async function load() {
  try {
    const resp = await portfolioV4Api.getHoldingsReview()
    review.value = (resp as any)?.data ?? (resp as any) ?? null
    // 默认展开权益
    if (review.value) for (const n of review.value.asset_tree) open[n.key] = n.key === 'equity'
  } catch { review.value = null }
}
load()

function toggle(k: string) { open[k] = !open[k] }
function fmt(v?: number): string {
  if (v == null) return '0'
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(0)
}
function shortName(n?: string): string {
  if (!n) return ''
  return n.length > 14 ? n.slice(0, 14) + '…' : n
}
function stanceCls(s?: string | null): string {
  if (!s) return ''
  if (s.includes('减') || s.includes('卖')) return 'reduce'
  if (s.includes('加') || s.includes('买')) return 'add'
  return 'hold'
}
function actCls(a?: string | null): string {
  if (a === 'reduce' || a === 'clear') return 'reduce'
  if (a === 'add') return 'add'
  return 'hold'
}
function actLabel(a?: string | null): string {
  return { add: '加配', reduce: '减配', hold: '维持', clear: '清空' }[a || ''] || a || ''
}
</script>

<style scoped>
.dt-wrap { padding: 4px; }
.dt-hint { text-align: center; padding: 40px; color: #909399; }
.dt-summary { display: flex; gap: 24px; margin-bottom: 16px; }
.dt-sum { background: #f7f9fc; border-radius: 8px; padding: 10px 18px; border-left: 3px solid #409eff; }
.dt-sum.alert { border-left-color: #faad14; background: #fffbe6; }
.dt-sum span { font-size: 12px; color: #909399; display: block; }
.dt-sum b { font-size: 18px; color: #303133; }

.dt-flow { background: #f9fbff; border: 1px solid #e4ecfb; border-radius: 8px; padding: 14px; margin-bottom: 18px; }
.dt-flow-title { font-size: 13.5px; font-weight: 600; color: #303133; margin-bottom: 10px; }
.dt-flow-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.dt-flow-h { font-size: 12.5px; font-weight: 600; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px dashed #dcdfe6; }
.dt-flow-h.src { color: #f56c6c; }
.dt-flow-h.use { color: #67c23a; }
.dt-flow-item { display: flex; justify-content: space-between; gap: 8px; font-size: 12.5px; color: #4e5969; padding: 3px 0; }
.dt-flow-amt { font-weight: 700; white-space: nowrap; }
.dt-flow-amt.src { color: #f56c6c; }
.dt-flow-amt.use { color: #67c23a; }
.dt-flow-note { font-size: 11px; color: #909399; max-width: 50%; text-align: right; }

.dt-tree-title { font-size: 14px; font-weight: 600; color: #303133; margin: 8px 0 10px; }
.dt-tree { border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; }
.dt-class { border-bottom: 1px solid #f0f2f5; }
.dt-class-row { display: flex; align-items: center; gap: 12px; padding: 11px 14px; cursor: pointer; background: #fafbfc; }
.dt-class-row:hover { background: #f5f7fa; }
.dt-caret { color: #909399; font-size: 11px; width: 12px; }
.dt-class-label { font-weight: 700; color: #303133; font-size: 14px; min-width: 80px; }
.dt-pct { font-size: 12.5px; color: #606266; }
.dt-pct b { color: #303133; }
.dt-action-tag { font-size: 11px; padding: 1px 8px; border-radius: 10px; font-weight: 600; }
.dt-action-tag.add { background: #f0f9eb; color: #67c23a; }
.dt-action-tag.reduce { background: #fef0f0; color: #f56c6c; }
.dt-action-tag.hold { background: #fdf6ec; color: #e6a23c; }
.dt-gap { font-size: 11.5px; font-weight: 600; }
.dt-gap.add { color: #67c23a; }
.dt-gap.reduce { color: #f56c6c; }
.dt-link { color: #409eff; cursor: pointer; font-size: 12px; margin-left: auto; white-space: nowrap; }
.dt-link.sm { margin-left: 0; font-size: 11px; }
.dt-link:hover { text-decoration: underline; }

.dt-class-body { padding: 4px 14px 12px 30px; background: #fff; }
.dt-ind { margin: 12px 0; }
.dt-ind-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; margin-bottom: 4px; }
.dt-ind-name { font-weight: 700; color: #303133; font-size: 13.5px; }
.dt-ind-stats { font-size: 12px; color: #606266; }
.dt-rec-only { color: #fa8c16 !important; font-weight: 600; }

/* 表格化展示 */
.dt-table { width: 100%; border-collapse: collapse; font-size: 12.5px; margin-bottom: 8px; }
.dt-table thead th { background: #fafbfc; padding: 6px 8px; text-align: left; font-weight: 600; color: #909399; font-size: 11.5px; border-bottom: 1px solid #ebeef5; }
.dt-table tbody td { padding: 7px 8px; border-bottom: 1px solid #f5f7fa; vertical-align: middle; color: #4e5969; }
.dt-table tbody tr:hover { background: #fafbfc; }
.dt-tr-own { background: #fff; }
.dt-tr-fund { background: #fafdff; }
.dt-tr-rec { background: #fffdf7; }
.dt-mono { font-family: monospace; color: #303133; }
.dt-pill-own, .dt-pill-fund, .dt-pill-rec { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10.5px; font-weight: 700; }
.dt-pill-own { background: #ecf5ff; color: #409eff; }
.dt-pill-fund { background: #f0f9ff; color: #0958d9; }
.dt-pill-rec { background: #fff7e6; color: #fa8c16; }
.dt-rec-meta { font-size: 11.5px; color: #909399; font-family: monospace; }
.dt-rec-target { font-size: 11.5px; color: #389e0d; font-weight: 600; margin-top: 2px; }
.dt-stance { font-size: 11.5px; font-weight: 700; padding: 1px 7px; border-radius: 4px; }
.dt-stance.reduce { background: #fef0f0; color: #f56c6c; }
.dt-stance.add { background: #f0f9eb; color: #67c23a; }
.dt-stance.hold { background: #fdf6ec; color: #e6a23c; }
.dt-pending { font-size: 11px; color: #c0c4cc; }
.dt-hold.plain { display: flex; gap: 10px; padding: 5px 0; font-size: 12.5px; color: #4e5969; }
.dt-h-name { color: #303133; min-width: 110px; }
.dt-h-wt { color: #909399; font-size: 12px; }
.dt-note { font-size: 11px; color: #c0c4cc; margin-top: 12px; }
</style>
