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
      <!-- 大类配比委员会 v10: 3大行动 + 3大风险 -->
      <div v-if="(review as any).portfolio_key_actions?.length" class="dt-pf-actions">
        <div class="dt-pf-actions-title">📋 大类配比委员会 关键行动 <span v-if="(review as any).portfolio_confidence" class="dt-pf-conf">conf {{ (review as any).portfolio_confidence }}</span></div>
        <ul class="dt-pf-actions-list">
          <li v-for="(a, i) in (review as any).portfolio_key_actions" :key="'a'+i" class="dt-pf-action">{{ a }}</li>
        </ul>
        <div class="dt-pf-actions-title risk">⚠️ 关键风险 + 对冲</div>
        <ul class="dt-pf-actions-list">
          <li v-for="(r, i) in (review as any).portfolio_key_risks" :key="'r'+i" class="dt-pf-risk">{{ r }}</li>
        </ul>
      </div>

      <!-- 11 canonical 行业配比总览(权益 equity_quota 下11大行业目标分配) -->
      <div v-if="(review as any).industry_allocations?.length" class="dt-ind-alloc">
        <div class="dt-ind-alloc-title">
          🎯 权益 11 大行业目标配比（equity_quota {{ (review as any).equity_quota_v4 }}%）
        </div>
        <div class="dt-ind-alloc-grid">
          <div v-for="a in (review as any).industry_allocations" :key="a.industry" class="dt-ind-alloc-card" :class="a.direction">
            <div class="dt-ind-alloc-head">
              <span class="dt-ind-alloc-name">{{ a.industry }}</span>
              <span class="dt-ind-alloc-w">{{ a.target_weight }}%</span>
            </div>
            <div class="dt-ind-alloc-stance">{{ a.stance || a.direction }}</div>
            <div v-if="a.value_creation_roic" class="dt-ind-alloc-roic">{{ a.value_creation_roic }}</div>
          </div>
        </div>
      </div>

      <!-- 大类决策树(资金动向已由各大类首行 gap_value + 个股 stance 直接展示, 不再单独列资金流向区块) -->
      <div class="dt-tree-title">📊 大类 → 行业 → 持仓（点击大类展开行业, 右侧"分析→"进各层详情）</div>
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
            <!-- 大类配比 reasoning(macro/flow/policy/risk 四视角) -->
            <div v-if="node.reasoning && Object.keys(node.reasoning).length" class="dt-class-reasoning">
              <div class="dt-cr-row" v-if="node.reasoning.macro"><span class="dt-cr-tag macro">📊 宏观</span>{{ node.reasoning.macro }}</div>
              <div class="dt-cr-row" v-if="node.reasoning.flow"><span class="dt-cr-tag flow">💧 资金</span>{{ node.reasoning.flow }}</div>
              <div class="dt-cr-row" v-if="node.reasoning.policy"><span class="dt-cr-tag policy">📜 政策</span>{{ node.reasoning.policy }}</div>
              <div class="dt-cr-row" v-if="node.reasoning.risk"><span class="dt-cr-tag risk">⚠️ 风险</span>{{ node.reasoning.risk }}</div>
            </div>
            <!-- 行业（权益） -->
            <div v-for="ind in node.industries" :key="ind.name" class="dt-ind">
              <!-- 行业首行: 名+目标配比+持仓金额+基金金额+推荐数量 -->
              <div class="dt-ind-row">
                <span class="dt-ind-name">🏭 {{ ind.name }}</span>
                <span v-if="industryAllocMap[ind.name]?.target_weight != null" class="dt-ind-target">
                  目标 {{ industryAllocMap[ind.name].target_weight }}%
                  <span class="dt-ind-direction" :class="industryAllocMap[ind.name].direction">{{ industryAllocMap[ind.name].direction }}</span>
                </span>
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
import { ref, reactive, computed } from 'vue'
import { portfolioV4Api, type HoldingsReview } from '@/api/portfolioV4'

defineEmits<{
  (e: 'open-stock', code: string): void
  (e: 'open-asset', key: string): void
  (e: 'open-industry', name: string): void
}>()

const review = ref<HoldingsReview | null>(null)
const open = reactive<Record<string, boolean>>({})

// 11 canonical 行业配比映射(供行业行显示 target_weight + direction)
const industryAllocMap = computed(() => {
  const m: Record<string, any> = {}
  const list = (review.value as any)?.industry_allocations || []
  for (const a of list) m[a.industry] = a
  return m
})

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
/* 11 canonical 行业配比总览 */
.dt-ind-alloc { background: #fafbff; border: 1px solid #d6e4ff; border-radius: 8px; padding: 12px; margin: 14px 0; }
.dt-ind-alloc-title { font-size: 13px; font-weight: 700; color: #1d3a8e; margin-bottom: 10px; }
.dt-ind-alloc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; }
.dt-ind-alloc-card { padding: 8px 10px; background: #fff; border-left: 3px solid #ccc; border-radius: 4px; }
.dt-ind-alloc-card.go { border-left-color: #389e0d; }
.dt-ind-alloc-card.bullish, .dt-ind-alloc-card.bullish_value_pick, .dt-ind-alloc-card.bullish_high_conviction { border-left-color: #389e0d; }
.dt-ind-alloc-card.cautious_bullish, .dt-ind-alloc-card.go_with_cautions, .dt-ind-alloc-card.cautious_bullish_cycle, .dt-ind-alloc-card.bullish_industry_cautious_stock { border-left-color: #faad14; }
.dt-ind-alloc-card.defensive_value_creator { border-left-color: #1d39c4; }
.dt-ind-alloc-head { display: flex; justify-content: space-between; align-items: center; }
.dt-ind-alloc-name { font-size: 12.5px; font-weight: 600; color: #303133; }
.dt-ind-alloc-w { font-size: 14px; font-weight: 700; color: #fa8c16; }
.dt-ind-alloc-stance { font-size: 11px; color: #595959; margin: 3px 0 2px; }
.dt-ind-alloc-roic { font-size: 11px; color: #909399; line-height: 1.4; }
/* 行业行 target_weight 标签 */
.dt-ind-target { font-size: 12px; color: #fa8c16; font-weight: 600; }
.dt-ind-direction { font-size: 10.5px; padding: 1px 5px; border-radius: 3px; margin-left: 4px; background: #f5f5f5; color: #606266; }
.dt-ind-direction.go, .dt-ind-direction.bullish, .dt-ind-direction.bullish_value_pick, .dt-ind-direction.bullish_high_conviction { background: #f6ffed; color: #389e0d; }
.dt-ind-direction.cautious_bullish, .dt-ind-direction.go_with_cautions, .dt-ind-direction.cautious_bullish_cycle, .dt-ind-direction.bullish_industry_cautious_stock { background: #fff7e6; color: #d46b08; }
.dt-ind-direction.defensive_value_creator { background: #f0f5ff; color: #1d39c4; }
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
/* 大类配比 reasoning */
.dt-class-reasoning { background: #fafbfc; border-left: 3px solid #409eff; padding: 8px 12px; margin: 6px 0 10px; border-radius: 4px; }
.dt-cr-row { font-size: 12px; color: #4e5969; line-height: 1.7; padding: 3px 0; }
.dt-cr-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10.5px; font-weight: 700; margin-right: 6px; }
.dt-cr-tag.macro { background: #ecf5ff; color: #1d3a8e; }
.dt-cr-tag.flow { background: #e6fffb; color: #006d75; }
.dt-cr-tag.policy { background: #fff7e6; color: #d46b08; }
.dt-cr-tag.risk { background: #fff1f0; color: #cf1322; }
/* 大类配比委员会 keyactions/risks */
.dt-pf-actions { background: #fff7e6; border: 1px solid #ffd591; border-radius: 8px; padding: 10px 14px; margin: 14px 0; }
.dt-pf-actions-title { font-size: 13px; font-weight: 700; color: #d46b08; margin: 6px 0 6px; }
.dt-pf-actions-title.risk { color: #cf1322; margin-top: 12px; }
.dt-pf-conf { font-size: 11px; color: #1d3a8e; font-weight: 600; background: #ecf5ff; padding: 1px 6px; border-radius: 3px; margin-left: 8px; }
.dt-pf-actions-list { list-style: none; padding: 0; margin: 0; }
.dt-pf-action, .dt-pf-risk { font-size: 12.5px; color: #434343; line-height: 1.7; padding: 3px 0; }
.dt-pf-risk { color: #595959; }
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
