<template>
  <div class="stock-detail-tab">
    <div v-if="loading" class="sdt-loading"><el-skeleton :rows="6" animated /></div>
    <template v-else-if="detail">
      <!-- 头部: 评级 + 买卖决策 -->
      <div class="card sdt-head">
        <div class="sdt-head-row">
          <span class="sdt-title">{{ detail.name }} <span class="sdt-code">{{ detail.code }}</span></span>
          <el-tag :type="ratingType" effect="plain">{{ detail.rating }}</el-tag>
        </div>
        <div class="sdt-decision">
          <div class="sdt-kv"><span>目标价</span><b>{{ detail.target_price ?? '区间法' }}</b></div>
          <div class="sdt-kv"><span>买点区间</span><b>{{ fmtRange(detail.entry_price_range) }}</b></div>
          <div class="sdt-kv"><span>判断时价</span><b>{{ detail.price_at_judgment ?? '-' }}</b></div>
          <div class="sdt-kv"><span>预期差</span><b>{{ shortGap }}</b></div>
        </div>
      </div>

      <!-- D0-1 估值推导链 (解决"买点怎么来") -->
      <div v-if="detail.valuation_basis" class="card sdt-section sdt-valuation">
        <div class="sdt-section-title">💰 估值推导（买点/目标价怎么来的）</div>
        <p>{{ detail.valuation_basis }}</p>
      </div>

      <!-- 四维质量闸门 -->
      <div class="card sdt-section">
        <div class="sdt-section-title">⚖️ 四维质量闸门（芒格/段永平/达里奥）</div>
        <div class="sdt-grid">
          <p v-if="detail.business_quality"><b>🏢 生意质量(10年)：</b>{{ detail.business_quality }}</p>
          <p v-if="detail.position_nature"><b>📌 投资 or 交易：</b>{{ detail.position_nature }}</p>
          <p v-if="detail.worst_case"><b>🧠 逆向最坏：</b>{{ detail.worst_case }}</p>
          <p v-if="detail.downside"><b>🌊 赔率+周期：</b>{{ detail.downside }}</p>
        </div>
        <p v-if="detail.thesis" class="sdt-thesis"><b>核心判断：</b>{{ detail.thesis }}</p>
      </div>

      <!-- 硬止损纪律 -->
      <div v-if="detail.sell_discipline?.length" class="card sdt-section sdt-sell">
        <div class="sdt-section-title">🛑 卖出/止损纪律（看到就执行）</div>
        <ol><li v-for="(s, i) in detail.sell_discipline" :key="i">{{ s }}</li></ol>
      </div>

      <!-- C 阶段 历史判断准确率 -->
      <div v-if="detail.historical_alpha" class="card sdt-section sdt-alpha">
        <div class="sdt-section-title">📊 历史判断准确率（结果闭环）</div>
        <div class="sdt-alpha-row">
          <el-tag :type="hitType" size="small">{{ hitLabel }}</el-tag>
          <span class="sdt-alpha-note">{{ detail.historical_alpha.alpha_note }}</span>
        </div>
        <p class="sdt-alpha-meta">数据状态: {{ detail.historical_alpha.data_status }} | 评估日: {{ detail.historical_alpha.evaluated_at }}</p>
      </div>

      <!-- 前瞻视野 -->
      <div v-if="detail.forward_view" class="card sdt-section">
        <el-collapse>
          <el-collapse-item name="fv">
            <template #title><span class="sdt-section-title">🔭 前瞻视野（事件日历+三情景+触发监控）</span></template>
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
            <p v-if="fv.mid_term_path"><b>📈 中长期：</b>{{ fv.mid_term_path }}</p>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- D 阶段 五力深做 (5+1 架构 2026-06-13) -->
      <div v-if="detail.five_forces" class="card sdt-section">
        <el-collapse>
          <el-collapse-item name="ff">
            <template #title>
              <span class="sdt-section-title">
                🏰 五力深做(护城河多强多稳)
                <el-tag v-if="ff.moat_rating" :type="moatType(ff.moat_rating)" size="small" class="sdt-moat">{{ ff.moat_rating }}</el-tag>
                <el-tag v-if="ff.moat_durability" type="info" size="small" class="sdt-moat">⏳ {{ durabilityShort(ff.moat_durability) }}</el-tag>
              </span>
            </template>
            <p v-if="ff.moat_synthesis" class="sdt-moat-synthesis"><b>护城河综合：</b>{{ ff.moat_synthesis }}</p>
            <div v-if="ff.five_forces_summary" class="sdt-fv-scn">
              <b>📊 五力评估：</b>
              <ul class="sdt-ff-list">
                <li v-if="ff.five_forces_summary.entry"><b>🚧 进入威胁：</b>{{ ff.five_forces_summary.entry }}</li>
                <li v-if="ff.five_forces_summary.substitute"><b>🔄 替代威胁：</b>{{ ff.five_forces_summary.substitute }}</li>
                <li v-if="ff.five_forces_summary.buyer"><b>🛒 买方议价：</b>{{ ff.five_forces_summary.buyer }}</li>
                <li v-if="ff.five_forces_summary.supplier"><b>📦 供方议价：</b>{{ ff.five_forces_summary.supplier }}</li>
                <li v-if="ff.five_forces_summary.rivalry"><b>⚔️ 同业竞争：</b>{{ ff.five_forces_summary.rivalry }}</li>
              </ul>
            </div>
            <div v-if="cfd?.mutual_reinforcement?.length" class="sdt-fv-scn">
              <b>🔗 力间互相强化（飞轮）：</b>
              <ol><li v-for="(m, i) in cfd.mutual_reinforcement" :key="'r'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
            </div>
            <div v-if="cfd?.mutual_offset?.length" class="sdt-fv-scn">
              <b>⚖️ 力间互相抵消：</b>
              <ol><li v-for="(m, i) in cfd.mutual_offset" :key="'o'+i">{{ m.force_a }} × {{ m.force_b }}：{{ m.mechanism }}</li></ol>
            </div>
            <p v-if="cfd?.weakest_link" class="sdt-weakest"><b>⚠️ 最弱一环：</b>{{ cfd.weakest_link }}</p>
            <p v-if="ff.key_risk"><b>🎯 最大单一风险：</b>{{ ff.key_risk }}</p>
            <div v-if="ff.monitoring_signals?.length">
              <b>👀 护城河层面监控信号：</b>
              <ul><li v-for="(s, i) in ff.monitoring_signals" :key="i">{{ s }}</li></ul>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 风险 + 证据 -->
      <div v-if="detail.risks?.length" class="card sdt-section">
        <div class="sdt-section-title">⚠️ 主要风险</div>
        <el-tag v-for="(r, i) in detail.risks" :key="i" type="danger" size="small" effect="plain" class="sdt-risk">{{ r }}</el-tag>
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
const shortGap = computed(() => (detail.value?.expectation_gap || '').slice(0, 20))
const ratingType = computed(() => {
  const r = detail.value?.rating || ''
  if (/买入|增持/.test(r)) return 'success'
  if (/减持|卖出/.test(r)) return 'danger'
  return 'info'
})
const hitLabel = computed(() => ({ hit: '✅ 命中', miss: '❌ 未命中', flat: '➖ 持平', tracking: '🔍 追踪中' } as Record<string, string>)[detail.value?.historical_alpha?.hit || ''] || detail.value?.historical_alpha?.hit || '-')
const hitType = computed(() => ({ hit: 'success', miss: 'danger', flat: 'info' } as Record<string, any>)[detail.value?.historical_alpha?.hit || ''] || 'info')

function fmtRange(r?: number[]) { return r && r.length === 2 ? `${r[0]} - ${r[1]}` : '-' }
function scnLabel(n?: string) { return ({ base: '基准', bull: '乐观', bear: '悲观' } as Record<string, string>)[n || ''] || n }
function moatType(r?: string): any { return ({ '宽': 'success', '中上': 'success', '中': 'info', '中下': 'warning', '窄': 'danger' } as Record<string, any>)[r || ''] || 'info' }
function durabilityShort(d?: string): string { if (!d) return ''; if (d.includes('长期')) return '长期 10 年+'; if (d.includes('中期')) return '中期 3-5 年'; if (d.includes('短期')) return '短期 1-3 年'; return d.slice(0, 10) }

watch(() => props.code, (c) => { if (c) load(c) }, { immediate: true })
</script>

<style scoped>
.sdt-loading { padding: 20px; }
.card { border: 1px solid #ebeef5; border-radius: 8px; background: #fff; padding: 16px; margin-bottom: 14px; }
.sdt-head-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sdt-title { font-size: 18px; font-weight: 700; color: #303133; }
.sdt-code { font-size: 13px; color: #909399; font-weight: 400; }
.sdt-decision { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.sdt-kv { display: flex; flex-direction: column; font-size: 13px; }
.sdt-kv span { color: #909399; font-size: 12px; }
.sdt-kv b { color: #303133; font-size: 15px; }
.sdt-section-title { font-weight: 600; color: #303133; margin-bottom: 8px; font-size: 14px; }
.sdt-valuation { background: #f0f9eb; border-left: 3px solid #67c23a; }
.sdt-valuation p { font-size: 13px; line-height: 1.7; color: #5a6a4f; }
.sdt-grid p { font-size: 13px; line-height: 1.7; margin: 4px 0; }
.sdt-thesis { margin-top: 10px; padding: 8px; background: #f5f7fa; border-radius: 4px; font-size: 13px; }
.sdt-sell { background: #fef0f0; border-left: 3px solid #f56c6c; }
.sdt-sell ol { padding-left: 22px; line-height: 1.9; font-size: 13px; }
.sdt-alpha { background: #ecf5ff; border-left: 3px solid #409eff; }
.sdt-alpha-row { display: flex; align-items: center; gap: 8px; }
.sdt-alpha-note { font-size: 13px; color: #5a6a8f; }
.sdt-alpha-meta { font-size: 11px; color: #909399; margin-top: 6px; }
.sdt-fv-trigger ol, .sdt-fv-scn { font-size: 13px; line-height: 1.8; }
.sdt-fv-trigger { background: #fef3e6; padding: 8px; border-radius: 4px; margin-bottom: 8px; }
.sdt-scn { margin: 3px 0; font-size: 12px; }
.sdt-risk { margin: 3px; }
.sdt-moat { margin-left: 6px; }
.sdt-moat-synthesis { background: #f5f7fa; padding: 8px; border-left: 3px solid #67c23a; border-radius: 4px; font-size: 13px; line-height: 1.7; margin-bottom: 10px; }
.sdt-ff-list { padding-left: 18px; font-size: 13px; line-height: 1.8; }
.sdt-weakest { background: #fef0f0; padding: 6px 8px; border-radius: 4px; font-size: 13px; color: #6a3030; margin-top: 8px; }
</style>
