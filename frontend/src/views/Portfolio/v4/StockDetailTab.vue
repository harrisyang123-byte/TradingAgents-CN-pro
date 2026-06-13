<template>
  <div class="stock-detail-tab">
    <div v-if="loading" class="sdt-loading"><el-skeleton :rows="6" animated /></div>
    <template v-else-if="detail">

      <!-- 1. 头部: 股票名+代码+行业+评级 (服务"可信") -->
      <div class="card sdt-head">
        <div class="sdt-head-row">
          <span class="sdt-title">
            {{ detail.name }} <span class="sdt-code">{{ detail.code }}</span>
            <span v-if="detail.industry" class="sdt-industry">· {{ detail.industry }}</span>
          </span>
          <el-tag :type="ratingType" effect="dark" size="large">{{ detail.rating }}</el-tag>
        </div>
      </div>

      <!-- 2. 🎯 操作建议大卡 (服务"可执行" - 一进页面就知道现在该做什么) -->
      <div class="card sdt-action">
        <div class="sdt-section-title">🎯 操作建议</div>
        <div class="sdt-action-grid">
          <div class="sdt-action-cell">
            <span class="sdt-action-label">目标价</span>
            <b class="sdt-action-val">¥{{ detail.target_price ?? '区间法' }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">买点区间</span>
            <b class="sdt-action-val">{{ fmtRange(detail.entry_price_range) }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">判断时价</span>
            <b class="sdt-action-val">¥{{ detail.price_at_judgment ?? '-' }}</b>
          </div>
          <div class="sdt-action-cell">
            <span class="sdt-action-label">预期差</span>
            <b class="sdt-action-val sdt-action-gap">{{ shortGap }}</b>
          </div>
        </div>
        <!-- 止损前置 3 条(执行优先于详情) -->
        <div v-if="topSells.length" class="sdt-action-sells">
          <span class="sdt-action-sells-label">⚡ 关键止损线（看到立即执行）</span>
          <ol><li v-for="(s, i) in topSells" :key="i">{{ s }}</li></ol>
        </div>
      </div>

      <!-- 3. 📌 一句话总结 (服务"可信" - 核心判断不绕弯) -->
      <div v-if="detail.verdict_oneliner" class="card sdt-oneliner">
        <span class="sdt-oneliner-icon">📌</span>
        <span class="sdt-oneliner-text">{{ detail.verdict_oneliner }}</span>
      </div>

      <!-- 4. 🎯 产业链卡位 (服务"全面" - 连接行业层投资地图) -->
      <div v-if="detail.chain_positioning?.industry_top?.length" class="card sdt-chain">
        <div class="sdt-section-title">🎯 产业链卡位 — 为什么是它，不是别人</div>
        <div v-if="detail.chain_positioning.chokepoint" class="sdt-chain-flow">
          <span class="sdt-chain-node">行业：{{ detail.chain_positioning.industry }}</span> →
          <span class="sdt-chain-node">瓶颈：{{ detail.chain_positioning.chokepoint }}</span> →
          <span class="sdt-chain-rank">#{{ detail.chain_positioning.my_rank ?? '?' }} 推荐</span>
        </div>
        <table class="sdt-chain-table">
          <thead>
            <tr><th>排序</th><th>标的</th><th>瓶颈环节</th><th>评级</th><th>目标价</th><th>为什么是它</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in detail.chain_positioning.industry_top" :key="i" :class="{ 'sdt-chain-self': r.is_self }">
              <td><span :class="r.is_self ? 'sdt-chain-rk-self' : 'sdt-chain-rk'">#{{ r.rank }}</span></td>
              <td><b>{{ r.recommended }}</b></td>
              <td>{{ r.chokepoint }}</td>
              <td><el-tag size="small" :type="ratingTypeFor(r.rating)" effect="plain">{{ r.rating }}</el-tag></td>
              <td>{{ r.target_price_live != null ? `¥${r.target_price_live}` : '-' }}</td>
              <td class="sdt-chain-why">{{ r.why }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="detail.chain_positioning.my_why" class="sdt-chain-mywhy">
          <b>📌 为什么是它（本股视角）：</b>{{ detail.chain_positioning.my_why }}
        </p>
      </div>

      <!-- 5. 📄 完整逻辑 + 估值推导 + 可信度 (服务"可信"+"会学习") -->
      <div class="card sdt-thesis-card">
        <div class="sdt-section-title">📄 为什么这样判断（完整逻辑）</div>
        <p v-if="detail.thesis" class="sdt-thesis-text">{{ detail.thesis }}</p>
        <!-- 四维质量闸门 紧凑展示在 thesis 内 -->
        <div class="sdt-thesis-grid">
          <p v-if="detail.business_quality"><b>🏢 生意质量：</b>{{ detail.business_quality }}</p>
          <p v-if="detail.position_nature"><b>📌 投资 or 交易：</b>{{ detail.position_nature }}</p>
          <p v-if="detail.worst_case"><b>🧠 逆向最坏：</b>{{ detail.worst_case }}</p>
          <p v-if="detail.downside"><b>🌊 赔率+周期：</b>{{ detail.downside }}</p>
        </div>
        <!-- 估值推导嵌入(因为它是 thesis 的可执行落地) -->
        <p v-if="detail.valuation_basis" class="sdt-thesis-valuation">
          <b>💰 估值推导：</b>{{ detail.valuation_basis }}
        </p>
        <!-- 可信度 critic 评审 -->
        <div v-if="detail.credibility" class="sdt-credibility">
          <span class="sdt-cred-icon">🎩</span>
          <span class="sdt-cred-text">
            可信度：经
            <b v-if="detail.credibility.reviewers?.length">{{ detail.credibility.reviewers.join('/') }}</b>
            <b v-else>四视角</b> 评审委员会，从
            <b v-if="detail.credibility.initial_score != null">{{ detail.credibility.initial_score }}</b>
            分迭代到
            <b v-if="detail.credibility.critic_score != null">{{ detail.credibility.critic_score }}</b>
            分 <b>{{ detail.credibility.final_verdict || 'ACCEPT' }}</b>
            <span v-if="detail.credibility.critic_iterations">（{{ detail.credibility.critic_iterations }} 轮迭代）</span>
            <span v-if="detail.credibility.challenges?.length" class="sdt-cred-chal">
              · 关键挑战：{{ detail.credibility.challenges.join('；') }}
            </span>
          </span>
        </div>
      </div>

      <!-- 6. 🟦 较上次/自检 (服务"会学习") -->
      <div v-if="detail.reflection" class="card sdt-reflection">
        <span class="sdt-reflection-tag">🔄 较上次 / 自检</span>
        <p v-if="detail.reflection.what_changed"><b>本次变化：</b>{{ detail.reflection.what_changed }}</p>
        <p v-if="detail.reflection.why_changed"><b>为何改：</b>{{ detail.reflection.why_changed }}</p>
        <p v-if="detail.reflection.self_check" class="sdt-reflection-check"><b>自检：</b>{{ detail.reflection.self_check }}</p>
      </div>

      <!-- 7. 🛑 止损纪律全集 (服务"可执行") -->
      <div v-if="detail.sell_discipline?.length" class="card sdt-sell">
        <div class="sdt-section-title">🛑 卖出/止损纪律（看到就执行）</div>
        <ol><li v-for="(s, i) in detail.sell_discipline" :key="i">{{ s }}</li></ol>
      </div>

      <!-- 8. 📊 历史判断准确率 (服务"会学习") -->
      <div v-if="detail.historical_alpha" class="card sdt-alpha">
        <div class="sdt-section-title">📊 历史判断准确率（结果闭环）</div>
        <div class="sdt-alpha-row">
          <el-tag :type="hitType" size="small">{{ hitLabel }}</el-tag>
          <span class="sdt-alpha-note">{{ detail.historical_alpha.alpha_note }}</span>
        </div>
        <p class="sdt-alpha-meta">数据状态: {{ detail.historical_alpha.data_status }} | 评估日: {{ detail.historical_alpha.evaluated_at }}</p>
      </div>

      <!-- 9. 🔬 支撑分析(折叠合并: 辩论/五力/前瞻/风险/证据) (服务"可信" - 详尽但不喧宾夺主) -->
      <div class="card sdt-support">
        <div class="sdt-section-title sdt-support-head">🔬 支撑分析（点击展开看完整论证）</div>
        <el-collapse>
          <!-- 多空 3 轮辩论 -->
          <el-collapse-item v-if="detail.debate_rounds?.length" name="debate">
            <template #title><span class="sdt-support-title">① 多空 {{ detail.debate_rounds.length }} 轮辩论（真实交锋）</span></template>
            <div v-for="rd in detail.debate_rounds" :key="rd.round + '-' + rd.side" class="sdt-debate-row">
              <span class="sdt-debate-round">第 {{ rd.round }} 轮</span>
              <el-tag size="small" :type="rd.side === 'bull' ? 'success' : 'danger'" effect="plain">{{ rd.side === 'bull' ? '多头' : '空头' }}</el-tag>
              <p class="sdt-debate-thesis">{{ rd.thesis }}</p>
            </div>
          </el-collapse-item>
          <!-- 五力深做 -->
          <el-collapse-item v-if="detail.five_forces" name="ff">
            <template #title>
              <span class="sdt-support-title">
                ② 波特五力 · 护城河可持续性
                <el-tag v-if="ff.moat_rating" :type="moatType(ff.moat_rating)" size="small" class="sdt-moat-inline">护城河 {{ ff.moat_rating }}</el-tag>
                <el-tag v-if="ff.moat_durability" type="info" size="small" class="sdt-moat-inline">⏳ {{ durabilityShort(ff.moat_durability) }}</el-tag>
              </span>
            </template>
            <p v-if="ff.moat_synthesis" class="sdt-moat-synthesis"><b>护城河综合：</b>{{ ff.moat_synthesis }}</p>
            <ul v-if="ff.five_forces_summary" class="sdt-ff-list">
              <li v-if="ff.five_forces_summary.entry"><b>🚧 进入威胁：</b>{{ ff.five_forces_summary.entry }}</li>
              <li v-if="ff.five_forces_summary.substitute"><b>🔄 替代威胁：</b>{{ ff.five_forces_summary.substitute }}</li>
              <li v-if="ff.five_forces_summary.buyer"><b>🛒 买方议价：</b>{{ ff.five_forces_summary.buyer }}</li>
              <li v-if="ff.five_forces_summary.supplier"><b>📦 供方议价：</b>{{ ff.five_forces_summary.supplier }}</li>
              <li v-if="ff.five_forces_summary.rivalry"><b>⚔️ 同业竞争：</b>{{ ff.five_forces_summary.rivalry }}</li>
            </ul>
            <div v-if="cfd?.mutual_reinforcement?.length">
              <b>🔗 力间互相强化（飞轮）：</b>
              <ol><li v-for="(m, i) in cfd.mutual_reinforcement" :key="'r'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
            </div>
            <div v-if="cfd?.mutual_offset?.length">
              <b>⚖️ 力间互相抵消：</b>
              <ol><li v-for="(m, i) in cfd.mutual_offset" :key="'o'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
            </div>
            <p v-if="cfd?.weakest_link" class="sdt-weakest"><b>⚠️ 最弱一环：</b>{{ cfd.weakest_link }}</p>
            <p v-if="ff.key_risk"><b>🎯 最大单一风险：</b>{{ ff.key_risk }}</p>
            <div v-if="ff.monitoring_signals?.length">
              <b>👀 护城河监控信号：</b>
              <ul><li v-for="(s, i) in ff.monitoring_signals" :key="i">{{ s }}</li></ul>
            </div>
          </el-collapse-item>
          <!-- 前瞻视野 -->
          <el-collapse-item v-if="detail.forward_view" name="fv">
            <template #title><span class="sdt-support-title">③ 前瞻视野（事件日历+三情景+触发监控）</span></template>
            <div v-if="fv.trigger_monitor?.length" class="sdt-fv-trigger">
              <b>⚡ 触发监控：</b>
              <ol><li v-for="(t, i) in fv.trigger_monitor" :key="i">{{ t }}</li></ol>
            </div>
            <div v-if="fv.path_scenarios?.length" class="sdt-fv-scn">
              <b>🎯 三情景：</b>
              <div v-for="(s, i) in fv.path_scenarios" :key="i" class="sdt-scn">
                {{ scnLabel(s.name) }} ({{ Math.round((s.prob||0)*100) }}%): {{ s.trigger }} →
                目标 {{ s.implied_target_price ?? '-' }}{{ s.implied_pe ? ` (PE ${s.implied_pe})` : '' }}
              </div>
            </div>
            <p v-if="fv.mid_term_path"><b>📈 中长期路径：</b>{{ fv.mid_term_path }}</p>
            <p v-if="fv.expectation_vs_consensus"><b>📊 vs 一致预期：</b>{{ fv.expectation_vs_consensus }}</p>
          </el-collapse-item>
          <!-- 风险清单 -->
          <el-collapse-item v-if="detail.risks?.length" name="risks">
            <template #title><span class="sdt-support-title">④ 主要风险</span></template>
            <el-tag v-for="(r, i) in detail.risks" :key="i" type="danger" size="small" effect="plain" class="sdt-risk">{{ r }}</el-tag>
          </el-collapse-item>
          <!-- 证据源 -->
          <el-collapse-item v-if="detail.evidence?.length" name="evidence">
            <template #title><span class="sdt-support-title">⑤ 证据源（{{ detail.evidence.length }} 条 verified/estimated）</span></template>
            <ul class="sdt-evidence-list">
              <li v-for="(e, i) in detail.evidence" :key="i">
                <el-tag :type="evidenceTagType(e.status)" size="small" effect="plain">{{ e.status }}</el-tag>
                {{ e.claim }}
                <span v-if="e.source" class="sdt-evidence-src">— {{ e.source }}</span>
              </li>
            </ul>
          </el-collapse-item>
        </el-collapse>
      </div>

    </template>
    <EmptyUnitState v-else title="未找到该个股分析" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import EmptyUnitState from './EmptyUnitState.vue'
import { portfolioV4Api, type StockDetail } from '@/api/portfolioV4'

const props = defineProps<{ code: string }>()
const detail = ref<StockDetail | null>(null)
const loading = ref(false)

async function load(code: string) {
  if (!code) return
  loading.value = true
  try {
    const res = await portfolioV4Api.getStockDetail(code)
    detail.value = (res as any).data ?? null
  } catch { detail.value = null } finally { loading.value = false }
}

const fv = computed(() => detail.value?.forward_view || {})
const ff = computed(() => detail.value?.five_forces || {})
const cfd = computed(() => (detail.value?.five_forces || {}).cross_force_dynamics || {})
const shortGap = computed(() => (detail.value?.expectation_gap || '').slice(0, 30))
// 止损前置：取前 3 条最关键(看到立即执行)
const topSells = computed(() => (detail.value?.sell_discipline || []).slice(0, 3))
const ratingType = computed(() => ratingTypeFor(detail.value?.rating))
const hitLabel = computed(() => ({ hit: '✅ 命中', miss: '❌ 未命中', flat: '➖ 持平', tracking: '🔍 追踪中' } as Record<string, string>)[detail.value?.historical_alpha?.hit || ''] || detail.value?.historical_alpha?.hit || '-')
const hitType = computed(() => ({ hit: 'success', miss: 'danger', flat: 'info' } as Record<string, any>)[detail.value?.historical_alpha?.hit || ''] || 'info')

function fmtRange(r?: number[]) { return r && r.length === 2 ? `${r[0]} - ${r[1]}` : '-' }
function scnLabel(n?: string) { return ({ base: '基准', bull: '乐观', bear: '悲观' } as Record<string, string>)[n || ''] || n }
function moatType(r?: string): any { return ({ '宽': 'success', '中上': 'success', '中': 'info', '中下': 'warning', '窄': 'danger' } as Record<string, any>)[r || ''] || 'info' }
function durabilityShort(d?: string): string { if (!d) return ''; if (d.includes('长期')) return '长期 10 年+'; if (d.includes('中期')) return '中期 3-5 年'; if (d.includes('短期')) return '短期 1-3 年'; return d.slice(0, 10) }
function ratingTypeFor(r?: string): any {
  if (!r) return 'info'
  if (/买入|增持/.test(r)) return 'success'
  if (/减持|卖出/.test(r)) return 'danger'
  return 'info'
}
function evidenceTagType(s?: string): any {
  if (s === 'verified') return 'success'
  if (s === 'estimated') return 'warning'
  if (s === 'missing') return 'info'
  return 'info'
}

watch(() => props.code, (c) => { if (c) load(c) }, { immediate: true })
</script>

<style scoped>
.sdt-loading { padding: 20px; }
.card { border: 1px solid #ebeef5; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 14px; }

/* 1. 头部 */
.sdt-head-row { display: flex; align-items: center; justify-content: space-between; }
.sdt-title { font-size: 20px; font-weight: 700; color: #303133; }
.sdt-code { font-size: 14px; color: #909399; font-weight: 400; margin-left: 6px; }
.sdt-industry { font-size: 13px; color: #2f4f8f; font-weight: 500; }

/* 2. 操作建议大卡 — 强调 */
.sdt-action { background: #fff7e6; border-left: 4px solid #faad14; box-shadow: 0 2px 8px rgba(250, 173, 20, 0.12); }
.sdt-action-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 12px; }
.sdt-action-cell { display: flex; flex-direction: column; padding: 10px; background: rgba(255,255,255,0.6); border-radius: 6px; }
.sdt-action-label { color: #8c6e00; font-size: 12px; margin-bottom: 4px; }
.sdt-action-val { color: #303133; font-size: 16px; font-weight: 700; }
.sdt-action-gap { font-size: 13px; line-height: 1.4; }
.sdt-action-sells { background: #fef0f0; border-radius: 6px; padding: 10px 14px; }
.sdt-action-sells-label { color: #c45656; font-weight: 600; font-size: 13px; }
.sdt-action-sells ol { padding-left: 22px; margin-top: 6px; line-height: 1.8; font-size: 13px; color: #6a3030; }

/* 3. 一句话总结 */
.sdt-oneliner { background: #f0f9eb; border-left: 4px solid #67c23a; padding: 14px 16px; display: flex; gap: 10px; align-items: flex-start; }
.sdt-oneliner-icon { font-size: 18px; }
.sdt-oneliner-text { font-size: 16px; font-weight: 600; color: #1d2129; line-height: 1.6; }

/* 4. 产业链卡位 */
.sdt-chain { border-left: 4px solid #2f4f8f; box-shadow: 0 2px 6px rgba(47, 79, 143, 0.08); }
.sdt-section-title { font-weight: 600; color: #303133; margin-bottom: 10px; font-size: 14px; }
.sdt-chain-flow { font-size: 14px; color: #4e5969; padding: 6px 0 12px 0; line-height: 2; }
.sdt-chain-node { background: #eef2ff; padding: 4px 10px; border-radius: 14px; color: #2f4f8f; font-weight: 600; }
.sdt-chain-rank { background: #67c23a; color: #fff; padding: 4px 12px; border-radius: 14px; font-weight: 700; }
.sdt-chain-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 6px; }
.sdt-chain-table th { background: #fafafa; padding: 8px 10px; text-align: left; border-bottom: 1px solid #ebeef5; font-weight: 600; color: #909399; font-size: 12px; }
.sdt-chain-table td { padding: 10px; border-bottom: 1px solid #f5f7fa; vertical-align: top; }
.sdt-chain-self { background: #f0f9eb; }
.sdt-chain-rk { display: inline-block; background: #909399; color: #fff; border-radius: 14px; padding: 2px 9px; font-size: 12px; }
.sdt-chain-rk-self { display: inline-block; background: #67c23a; color: #fff; border-radius: 14px; padding: 2px 9px; font-size: 12px; font-weight: 700; }
.sdt-chain-why { color: #606266; font-size: 12.5px; line-height: 1.5; max-width: 280px; }
.sdt-chain-mywhy { margin-top: 14px; padding: 12px; background: #fff7e6; border-left: 3px solid #faad14; border-radius: 4px; font-size: 13.5px; line-height: 1.7; color: #4e5969; }

/* 5. 完整逻辑+可信度 */
.sdt-thesis-card { }
.sdt-thesis-text { font-size: 14px; color: #4e5969; line-height: 1.8; white-space: pre-wrap; padding: 8px 12px; background: #f5f7fa; border-radius: 6px; margin-bottom: 12px; }
.sdt-thesis-grid p { font-size: 13px; line-height: 1.7; margin: 4px 0; color: #606266; }
.sdt-thesis-valuation { background: #f0f9eb; border-left: 3px solid #67c23a; padding: 10px 12px; border-radius: 4px; font-size: 13px; line-height: 1.7; color: #5a6a4f; margin-top: 10px; }
.sdt-credibility { margin-top: 12px; background: #eef2ff; border-radius: 6px; padding: 10px 14px; display: flex; align-items: flex-start; gap: 10px; }
.sdt-cred-icon { font-size: 16px; }
.sdt-cred-text { color: #4f46e5; font-size: 13px; line-height: 1.6; }
.sdt-cred-text b { color: #312e81; font-weight: 700; }
.sdt-cred-chal { display: block; margin-top: 4px; color: #6366f1; }

/* 6. reflection */
.sdt-reflection { background: #ecf5ff; border-left: 3px solid #409eff; }
.sdt-reflection-tag { color: #2f54eb; font-weight: 700; font-size: 13px; margin-right: 8px; }
.sdt-reflection p { font-size: 13px; line-height: 1.7; margin: 4px 0; color: #5a6a8f; }
.sdt-reflection-check { background: rgba(255,255,255,0.5); padding: 8px; border-radius: 4px; margin-top: 8px !important; }

/* 7. 止损 */
.sdt-sell { background: #fef0f0; border-left: 3px solid #f56c6c; }
.sdt-sell ol { padding-left: 22px; line-height: 1.9; font-size: 13px; }

/* 8. alpha */
.sdt-alpha { background: #ecf5ff; border-left: 3px solid #409eff; }
.sdt-alpha-row { display: flex; align-items: center; gap: 8px; }
.sdt-alpha-note { font-size: 13px; color: #5a6a8f; }
.sdt-alpha-meta { font-size: 11px; color: #909399; margin-top: 6px; }

/* 9. 支撑分析(折叠) */
.sdt-support-head { color: #909399; font-size: 13px; }
.sdt-support-title { font-weight: 600; color: #303133; font-size: 13.5px; }
.sdt-debate-row { padding: 8px; margin: 4px 0; background: #fafafa; border-radius: 4px; font-size: 13px; }
.sdt-debate-round { font-weight: 700; color: #909399; margin-right: 8px; }
.sdt-debate-thesis { margin-top: 6px; line-height: 1.6; color: #4e5969; }
.sdt-moat-inline { margin-left: 6px; }
.sdt-moat-synthesis { background: #f5f7fa; padding: 8px; border-left: 3px solid #67c23a; border-radius: 4px; font-size: 13px; line-height: 1.7; margin-bottom: 10px; }
.sdt-ff-list { padding-left: 18px; font-size: 13px; line-height: 1.8; }
.sdt-weakest { background: #fef0f0; padding: 6px 8px; border-radius: 4px; font-size: 13px; color: #6a3030; margin-top: 8px; }
.sdt-fv-trigger { background: #fef3e6; padding: 8px; border-radius: 4px; margin-bottom: 8px; font-size: 13px; line-height: 1.8; }
.sdt-fv-scn { font-size: 13px; line-height: 1.8; margin-bottom: 8px; }
.sdt-scn { margin: 3px 0; font-size: 12.5px; }
.sdt-risk { margin: 3px; }
.sdt-evidence-list { padding-left: 0; list-style: none; font-size: 12.5px; line-height: 1.8; }
.sdt-evidence-list li { padding: 4px 0; border-bottom: 1px dashed #f5f7fa; }
.sdt-evidence-src { color: #909399; font-size: 11.5px; margin-left: 6px; }
</style>
