<template>
  <div class="portfolio-overview page-content">
    <!-- 顶部统计 -->
    <div v-if="overview" style="display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap;">
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#409eff;">{{ overview.total_industries || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">总行业数</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#67c23a;">{{ overview.covered_count || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">已覆盖</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700; color:#e6a23c;">{{ overview.stale_count || 0 }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">待更新</div>
        </div>
      </div>
      <div class="card" style="flex:1; min-width:140px;">
        <div class="card-body" style="text-align:center; padding:14px;">
          <div style="font-size:22px; font-weight:700;">{{ overview.data_score ? (overview.data_score * 100).toFixed(0) + '%' : '--' }}</div>
          <div style="font-size:12px; color:#909399; margin-top:4px;">数据质量</div>
        </div>
      </div>
    </div>

    <!-- 资产配比总揽（战略层·大类）-->
    <div v-if="assetAssets.length" class="card">
      <div class="card-header">
        <span>资产配比总揽 <span class="sub">· 战略层（大类）</span></span>
      </div>
      <div class="alloc-wrap">
        <div class="alloc-bar-label">现状</div>
        <div class="stacked">
          <div v-for="seg in assetSegments('current_weight')" :key="'c'+seg.cls" class="seg"
            :style="{ flex: seg.w, background: seg.color }" :title="seg.cls + ' ' + seg.w + '%'">
            <span>{{ seg.cls }} {{ seg.w.toFixed(1) }}%</span>
          </div>
        </div>
        <template v-if="assetHasTargets">
          <div class="alloc-bar-label">目标（大类裁判产出）</div>
          <div class="stacked">
            <div v-for="seg in assetSegments('target_weight')" :key="'t'+seg.cls" class="seg"
              :style="{ flex: seg.w, background: seg.color }" :title="seg.cls + ' ' + seg.w + '%'">
              <span>{{ seg.cls }} {{ seg.w.toFixed(1) }}%</span>
            </div>
          </div>
        </template>
        <div v-else class="alloc-note">⚠️ 本次未生成大类目标配比（大类配置 agent 未产出），仅展示当前持仓现状，不编造目标值。</div>

        <table class="alloc-table">
          <thead>
            <tr><th>大类</th><th>现状%</th><th>目标%</th><th>变动</th><th>操作</th><th>调仓金额</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="a in assetAssets" :key="a.asset_class" class="alloc-row" @click="onAssetRowClick(a)">
              <td><span class="alloc-dot" :style="{ background: assetColor(a.asset_class) }"></span><span class="alloc-name">{{ a.asset_class }}</span></td>
              <td>{{ a.current_weight.toFixed(1) }}%</td>
              <td><span v-if="a.target_weight != null" class="target">{{ a.target_weight.toFixed(1) }}%</span><span v-else class="text-muted">--</span></td>
              <td>
                <span v-if="a.delta == null" class="text-muted">--</span>
                <span v-else-if="a.delta > 0" style="color:#67c23a;">+{{ a.delta.toFixed(1) }}%</span>
                <span v-else-if="a.delta < 0" style="color:#f56c6c;">{{ a.delta.toFixed(1) }}%</span>
                <span v-else>0%</span>
              </td>
              <td>
                <span v-if="a.target_weight == null" class="text-muted">--</span>
                <span v-else-if="a.action === 'add'" class="go-badge go-badge-go">加配</span>
                <span v-else-if="a.action === 'reduce'" class="go-badge go-badge-nogo">减配</span>
                <span v-else class="go-badge go-badge-hold">维持</span>
              </td>
              <td><span v-if="a.target_amount != null && a.delta">{{ formatMoney(Math.abs(a.target_amount - a.current_amount)) }}</span><span v-else class="text-muted">--</span></td>
              <td>
                <span v-if="a.asset_class === '股票'" class="drill-hint">↓ 见下方矩阵</span>
                <span v-else-if="['黄金','债券','海外'].includes(a.asset_class)" class="drill-hint">下钻 →</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 行业矩阵 -->
    <div class="card" ref="matrixCard" :class="{ 'matrix-flash': matrixFlash }">
      <div class="card-header">
        <span>行业配置矩阵 <span v-if="assetAssets.length" class="sub">· 股票大类明细</span></span>
        <button style="font-size:12px; padding:4px 12px; border:1px solid #dcdfe6; border-radius:4px; cursor:pointer; background:#fff;" @click="loadOverview(true)" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
      <div v-if="assetHasTargets && assetAllocation && assetAllocation.stock_weight != null" class="matrix-hint">
        ⤷ 以下为<b>股票大类</b>内部细分，目标% 合计 = 股票目标 <b>{{ assetAllocation.stock_weight }}%</b>（已剔除现金/债券/黄金/海外，避免与大类层重复）
      </div>
      <div class="card-body" style="padding:0;">
        <div v-if="loading" style="text-align:center; padding:40px; color:#909399;">加载中...</div>
        <div v-else-if="!overview || !filteredMatrix.length" class="empty-state">
          <div class="empty-title">暂无行业数据</div>
          <div class="empty-desc">请先运行组合顾问分析</div>
        </div>
        <table v-else class="industry-table">
          <thead>
            <tr>
              <th>行业</th>
              <th>市场</th>
              <th>景气</th>
              <th>现持仓%</th>
              <th>目标%</th>
              <th>操作</th>
              <th>调仓金额</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in filteredMatrix" :key="row.industry">
            <tr
              class="industry-row"
              :class="[row.go_nogo === 'GO' ? 'row-go' : (row.go_nogo === 'NOGO' ? 'row-nogo' : ''), expandedRow === row.industry ? 'row-expanded' : '']"
              @click="toggleRowExpand(row)"
            >
              <td>
                <span class="ind-name">{{ row.industry }}</span>
                <span v-if="['holding','watchlist','vitality'].includes(row.source || '')" class="ind-source-tag" :class="'src-' + row.source">{{ sourceLabel(row.source || '') }}</span>
              </td>
              <td style="color:#606266; font-size:12px;">{{ row.market || '--' }}</td>
              <td>
                <span v-if="row.vitality_level" class="v-tag" :class="'v-' + row.vitality_level">{{ row.vitality_level }}</span>
                <span v-else class="text-muted">--</span>
              </td>
              <td>
                <div class="weight-transition">
                  <span>{{ (row.holdings_weight || 0).toFixed(1) }}%</span>
                  <span class="arrow">→</span>
                  <span class="target">{{ (row.target_weight || 0).toFixed(1) }}%</span>
                </div>
              </td>
              <td style="color:#909399; font-size:12px;">
                <span v-if="row.delta > 0" style="color:#67c23a;">+{{ row.delta.toFixed(1) }}%</span>
                <span v-else-if="row.delta < 0" style="color:#f56c6c;">{{ row.delta.toFixed(1) }}%</span>
                <span v-else>0%</span>
              </td>
              <td>
                <span v-if="row.industry === '现金'" class="go-badge go-badge-hold">现金</span>
                <span v-else-if="row.target_weight === 0 && row.holdings_weight > 0" class="go-badge go-badge-nogo">清仓</span>
                <span v-else-if="row.delta > 0" class="go-badge go-badge-go">{{ row.go_nogo === 'GO' ? 'GO ' : '' }}加仓</span>
                <span v-else-if="row.delta < 0" class="go-badge go-badge-nogo">{{ row.go_nogo === 'NOGO' ? 'NOGO ' : '' }}减仓</span>
                <span v-else class="go-badge go-badge-hold">持有</span>
              </td>
              <td style="font-size:13px;">
                <span v-if="row.delta !== 0">{{ formatMoney(actionAmount(row)) }}</span>
                <span v-else class="text-muted">--</span>
              </td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 分析师辩论历程 -->
    <div v-if="latestAdvice" class="card mt-4 debate-card">
      <div class="card-header debate-header" @click="debateCollapsed = !debateCollapsed" style="cursor:pointer;">
        <span>分析师辩论历程</span>
        <span class="collapse-arrow" :class="debateCollapsed ? '' : 'open'">▸</span>
      </div>
      <div v-if="!debateCollapsed">
        <div class="debate-tabs">
          <button v-for="tab in debateTabs" :key="tab.key" class="debate-tab" :class="activeDebateTab === tab.key ? 'active' : ''" @click="activeDebateTab = tab.key">{{ tab.label }}</button>
        </div>
        <div class="debate-content">
          <DebateTimeline v-if="activeDebateHistory" :history-data="activeDebateHistory" />
          <div v-else class="debate-empty">{{ activeDebateEmptyText }}</div>
        </div>
      </div>
    </div>

    <!-- 历史建议 -->
    <div class="card mt-4">
      <div class="card-header">历史分析记录</div>
      <div v-if="!adviceHistory.length" class="empty-state">
        <div class="empty-title">暂无历史记录</div>
        <div class="empty-desc">分析完成后将在此显示</div>
      </div>
      <div v-else>
        <div
          v-for="adv in adviceHistory"
          :key="adv.advice_id"
          class="history-card"
          :class="latestAdvice && latestAdvice.advice_id === adv.advice_id ? 'history-card-selected' : ''"
          @click="selectAdvice(adv)"
        >
          <div class="history-header">
            <span class="history-date">{{ formatDateTime(adv.created_at) }}</span>
            <span style="font-size:11px; padding:2px 8px; border-radius:3px; background:#f0f9eb; color:#67c23a;">{{ adv.status }}</span>
          </div>
          <div class="history-summary">
            {{ (adv.prescription || []).length }} 条处方
            · {{ (adv as any).selected_industries?.length || (adv as any).market_intel?.industries?.length || (adv as any).industry_matrix?.length || 0 }} 个行业
            <span v-if="(adv as any).total_assets_snapshot"> · {{ formatMoney((adv as any).total_assets_snapshot) }} 元</span>
            · 耗时 {{ adv.elapsed_seconds ? (adv.elapsed_seconds / 60).toFixed(0) + ' 分钟' : '--' }}
          </div>
        </div>
      </div>
    </div>

    <!-- 下钻抽屉（大类 / 行业共用，宽 60%）-->
    <div v-if="showIndustryDrawer" class="drawer-mask" @click="showIndustryDrawer = false"></div>
    <div v-if="showIndustryDrawer" class="drawer-panel">
      <div class="drawer-head">
        <span class="drawer-title">
          <template v-if="drawerType === 'asset'">【大类】{{ drawerAsset?.asset_class }}</template>
          <template v-else>【行业】{{ selectedIndustry?.industry }}</template>
        </span>
        <button class="drawer-close" @click="showIndustryDrawer = false">×</button>
      </div>

      <!-- 快照 -->
      <div class="snapshot">
        <template v-if="drawerType === 'asset' && drawerAsset">
          <div class="snap-item"><div class="k">现状 → 目标</div><div class="v">{{ drawerAsset.current_weight.toFixed(1) }}% <span class="arrow">→</span> <span v-if="drawerAsset.target_weight!=null" class="target">{{ drawerAsset.target_weight.toFixed(1) }}%</span><span v-else class="text-muted">未生成</span></div></div>
          <div class="snap-item"><div class="k">操作</div><div class="v">
            <span v-if="drawerAsset.target_weight==null" class="text-muted">--</span>
            <span v-else-if="drawerAsset.action==='add'" class="go-badge go-badge-go">加配</span>
            <span v-else-if="drawerAsset.action==='reduce'" class="go-badge go-badge-nogo">减配</span>
            <span v-else class="go-badge go-badge-hold">维持</span>
          </div></div>
          <div class="snap-item"><div class="k">调仓金额</div><div class="v">{{ drawerAsset.target_amount!=null && drawerAsset.delta ? formatMoney(Math.abs(drawerAsset.target_amount - drawerAsset.current_amount)) : '--' }}</div></div>
        </template>
        <template v-else-if="selectedIndustry">
          <div class="snap-item"><div class="k">景气</div><div class="v"><span v-if="selectedIndustry.vitality_level" class="v-tag" :class="'v-' + selectedIndustry.vitality_level">{{ selectedIndustry.vitality_level }}</span><span v-else class="text-muted">--</span></div></div>
          <div class="snap-item"><div class="k">现状 → 目标</div><div class="v">{{ (selectedIndustry.holdings_weight||0).toFixed(1) }}% <span class="arrow">→</span> <span class="target">{{ (selectedIndustry.target_weight||0).toFixed(1) }}%</span></div></div>
          <div class="snap-item"><div class="k">调仓金额</div><div class="v">{{ formatMoney(actionAmount(selectedIndustry)) }}</div></div>
        </template>
      </div>

      <!-- 配置理由 -->
      <div v-if="(drawerType==='asset' ? drawerAsset?.reasoning : selectedIndustry?.reasoning)" class="reasoning-box">
        <div class="reasoning-head">配置理由</div>
        <div class="reasoning-body">{{ drawerType==='asset' ? drawerAsset?.reasoning : selectedIndustry?.reasoning }}</div>
      </div>

      <!-- 标的处方表（行可展开看 Tier1 选股依据）-->
      <div class="rx-title">标的处方<span class="rx-sub">（点标的看 Tier1 选股依据：核心逻辑 / 风险 / 评级 / 目标价）</span></div>
      <table v-if="drawerPositions.length" class="rx-table">
        <thead>
          <tr>
            <th>标的</th><th>操作</th><th>现仓→目标</th><th>买入区间</th><th>策略</th>
            <th v-if="drawerShowPe">PE分位</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="pos in drawerPositions" :key="pos.code">
            <tr class="rx-main" :class="{ open: expandedRx === pos.code }" @click="toggleRx(pos.code)">
              <td><span class="caret">▸</span><span class="rx-name">{{ pos.name || pos.code }}</span><span class="rx-code">{{ pos.code }}</span></td>
              <td><span :class="'action action-' + (['buy','add','new_position'].includes(pos.action) ? 'buy' : ['sell','reduce'].includes(pos.action) ? 'sell' : 'hold')">{{ actionLabel(pos.action) }}</span></td>
              <td class="pos-change">{{ (pos.current_weight||0).toFixed(1) }}% → {{ (pos.target_weight||0).toFixed(1) }}%</td>
              <td><span v-if="pos.suggested_price" style="color:#409eff;">{{ pos.suggested_price }}</span><span v-else class="text-muted">--</span></td>
              <td><span v-if="pos.build_strategy || pos.timing" class="strat-tag" :class="'strat-' + (pos.build_strategy || pos.timing)">{{ buildStrategyLabel(pos.build_strategy || pos.timing || '') }}</span><span v-else class="text-muted">--</span></td>
              <td v-if="drawerShowPe"><span v-if="pos.pe_data && pos.pe_data.pe_percentile_5y !== undefined" class="pe-badge" :class="pos.pe_data.pe_percentile_5y > 80 ? 'pe-high' : pos.pe_data.pe_percentile_5y < 30 ? 'pe-low' : 'pe-mid'">{{ pos.pe_data.pe_percentile_5y.toFixed(0) }}%ile</span><span v-else class="text-muted">--</span></td>
            </tr>
            <tr v-if="expandedRx === pos.code" class="rx-detail-row">
              <td :colspan="drawerShowPe ? 6 : 5">
                <div class="tier1">
                  <div class="tier1-head">
                    <span class="tier1-tag">Tier1 研究库</span>
                    <span class="rating">{{ pos.tier1_rating || '--' }}</span>
                    <span class="t1-target">目标价 <b>{{ pos.target_price || '未给目标价' }}</b></span>
                  </div>
                  <div class="tier1-grid">
                    <div class="t1-block t1-bull"><div class="lbl">核心逻辑（多头）</div>{{ pos.reasoning || '未分析' }}</div>
                    <div class="t1-block t1-bear"><div class="lbl">主要风险（空头）</div>{{ pos.risk_note || '未分析' }}</div>
                  </div>
                  <div v-if="(pos.batch_plan || []).length" class="t1-block" style="margin-bottom:8px;">
                    <div class="lbl">分批计划</div>
                    <div v-for="(b, bi) in pos.batch_plan" :key="bi" class="batch-line">• {{ b.price }} ｜ {{ b.weight_pct }}% ｜ {{ b.condition }}</div>
                  </div>
                  <div class="t1-meta">
                    <span><b>建仓策略</b> {{ buildStrategyLabel(pos.build_strategy || pos.timing || '') || '--' }}</span>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div v-else class="rx-empty">暂无标的处方明细</div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { portfolioApi, type PortfolioAdvice, type IndustryOverviewRow, type AdviceItem } from '@/api/paper'
import { usePageCache } from '@/composables/usePageCache'
import DebateTimeline from '@/components/Analysis/DebateTimeline.vue'

// --- state ---
const loading = ref(false)
const overview = ref<any>(null)
const { loadWithCache, forceRefresh } = usePageCache()
const adviceHistory = ref<PortfolioAdvice[]>([])

const showIndustryDrawer = ref(false)
const selectedIndustry = ref<IndustryOverviewRow | null>(null)
const expandedRow = ref<string | null>(null)

// 通用下钻 Drawer（大类 / 行业共用）
type DrawerType = 'asset' | 'industry'
const drawerType = ref<DrawerType>('industry')
const drawerAsset = ref<any>(null)
const expandedRx = ref<string | null>(null) // 个股行展开的 code（看 Tier1 依据）
const matrixCard = ref<HTMLElement | null>(null)
const matrixFlash = ref(false)

const latestAdvice = ref<any>(null)
const debateCollapsed = ref(true)
const activeDebateTab = ref('market')
// 四路辩论 tab 全部常驻：缺数据时显示「暂无…记录」空状态，不再隐藏整个 tab
// （隐藏会掩盖「本次未跑大类层」与「前端故障」的区别，违背数据缺失需明示的原则）
const debateTabs = computed(() => {
  return [
    { key: 'asset', label: '大类配置辩论' },
    { key: 'market', label: '市场研判（L1）' },
    { key: 'stock', label: '个股辩论（L3）' },
    { key: 'final', label: '综合裁决' },
  ]
})

// 当前 tab 的辩论文本（喂给 DebateTimeline 气泡组件）
const activeDebateHistory = computed(() => {
  const adv: any = latestAdvice.value
  if (!adv) return ''
  if (activeDebateTab.value === 'asset') return adv.asset_debate_history || ''
  if (activeDebateTab.value === 'market') return adv.market_debate_history || ''
  if (activeDebateTab.value === 'stock') return adv.stock_debate_history || ''
  return adv.debate_history || ''
})
const activeDebateEmptyText = computed(() => {
  const m: Record<string, string> = {
    asset: '暂无大类配置辩论记录',
    market: '暂无市场研判记录',
    stock: '暂无个股辩论记录',
    final: '暂无综合裁决记录',
  }
  return m[activeDebateTab.value] || '暂无记录'
})

// --- 大类资产配置（资产配比总揽卡）---
const ASSET_META: Record<string, { color: string }> = {
  股票: { color: '#f0883e' },
  现金: { color: '#b0b4bd' },
  债券: { color: '#5b8def' },
  黄金: { color: '#e6c200' },
  海外: { color: '#36b39a' },
  其他: { color: '#c98ce0' },
}
function assetColor(cls: string): string {
  return ASSET_META[cls]?.color || '#c98ce0'
}
// 前端大类穿透（与后端 ingest _asset_class_of 口径一致），用于把处方按大类归类下钻
function assetClassOf(code: string, name: string, bucket: string): string {
  const s = `${name || ''} ${bucket || ''}`
  const c = (code || '').toUpperCase()
  if (c === 'CASH' || s.includes('现金') || s.includes('逆回购')) return '现金'
  if (s.includes('黄金') || bucket === '黄金') return '黄金'
  if (['QDII', '海外', '纳指', '纳斯达克', '标普', '恒生', '港股', '美股', '境外', '全球'].some(k => s.includes(k))) return '海外'
  if (['债', '国债', '货币', '货基', '固收', '纯债'].some(k => s.includes(k))) return '债券'
  return '股票'
}

const assetAllocation = computed<any>(() => {
  return overview.value?.asset_allocation || (latestAdvice.value as any)?.asset_allocation || null
})
const assetAssets = computed<any[]>(() => assetAllocation.value?.assets || [])
const assetHasTargets = computed<boolean>(() => !!assetAllocation.value?.has_targets)

// 堆叠条分段：field = 'current_weight' | 'target_weight'
function assetSegments(field: 'current_weight' | 'target_weight') {
  return assetAssets.value
    .filter(a => (a[field] || 0) > 0)
    .map(a => ({ cls: a.asset_class, w: a[field] || 0, color: assetColor(a.asset_class) }))
}

// --- filtered matrix：行业矩阵只保留「股票大类内部」的真行业，
//     剔除现金/债券/黄金/海外(QDII)/全球配置/债券固收（这些已在大类层展示，避免重复）---
const NON_STOCK_BUCKETS = ['现金', '债券', '债券/固收', '黄金', '海外', '海外(QDII)', 'QDII/海外', '全球配置']
const filteredMatrix = computed(() => {
  if (!overview.value?.matrix) return []
  return overview.value.matrix.filter((r: IndustryOverviewRow) => !NON_STOCK_BUCKETS.includes(r.industry))
})

// --- drawer 标的处方列表 ---
const drawerPositions = computed<AdviceItem[]>(() => {
  if (drawerType.value === 'industry') {
    return selectedIndustry.value?.positions_detail || []
  }
  // 大类下钻（黄金/债券/海外）：从最新处方按大类归类筛选
  const cls = drawerAsset.value?.asset_class
  if (!cls) return []
  const rx = (latestAdvice.value as any)?.prescription || []
  return rx.filter((p: any) => assetClassOf(p.code, p.name, p.industry_bucket) === cls)
})
// 海外大类 PE 有意义，其余大类（债券/黄金）无 PE
const drawerShowPe = computed(() => drawerType.value === 'industry' || drawerAsset.value?.asset_class === '海外')

// --- helpers ---
function actionAmount(row: IndustryOverviewRow): number {
  const total = overview.value?.total_assets || 0
  const diff = (row.target_weight || 0) - (row.holdings_weight || 0)
  return Math.abs(roundMoney(diff / 100 * total))
}
function formatMoney(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toFixed(0)
}
function roundMoney(n: number): number {
  return Math.round(n / 100) * 100
}
function formatDateTime(utcStr?: string): string {
  if (!utcStr) return '--'
  return new Date(utcStr).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}
function sourceLabel(s: string): string {
  const m: Record<string, string> = { holding: '持仓', watchlist: '关注', vitality: '景气' }
  return m[s] || s
}

function actionLabel(a: string): string {
  const m: Record<string, string> = { buy: '买入', add: '加仓', reduce: '减仓', sell: '卖出', hold: '持有', new_position: '建仓' }
  return m[a?.toLowerCase()] || a || '--'
}
function buildStrategyLabel(s: string): string {
  const m: Record<string, string> = { immediate: '立即', batch: '分批', conditional: '条件' }
  return m[s] || s
}

function openIndustryDrawer(row: IndustryOverviewRow) {
  drawerType.value = 'industry'
  selectedIndustry.value = row
  expandedRx.value = null
  showIndustryDrawer.value = true
}

// 大类行点击：股票→滚动高亮下方矩阵；黄金/债券/海外→开抽屉；现金/其他→不下钻
function onAssetRowClick(item: any) {
  if (item.asset_class === '股票') {
    scrollToMatrix()
    return
  }
  if (['现金', '其他'].includes(item.asset_class)) return
  drawerType.value = 'asset'
  drawerAsset.value = item
  expandedRx.value = null
  showIndustryDrawer.value = true
}

function scrollToMatrix() {
  const el = matrixCard.value
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  matrixFlash.value = false
  // 重新触发动画
  requestAnimationFrame(() => { matrixFlash.value = true })
  setTimeout(() => { matrixFlash.value = false }, 1300)
}

function toggleRx(code: string) {
  expandedRx.value = expandedRx.value === code ? null : code
}

function toggleRowExpand(row: IndustryOverviewRow) {
  // 行业行点击 = 打开下钻抽屉（与大类下钻统一，消除「行内展开 vs 抽屉」两套）
  openIndustryDrawer(row)
}

function selectAdvice(adv: PortfolioAdvice) {
  latestAdvice.value = adv
  debateCollapsed.value = false
  openAdviceDetail(adv)
}

function openAdviceDetail(adv: PortfolioAdvice) {
  // Load overview with this advice's data
  loadOverview(false, adv)
}

// --- data loading ---
async function loadOverview(force = false, adv?: PortfolioAdvice) {
  loading.value = true
  try {
    const fn = force ? forceRefresh : loadWithCache
    overview.value = await fn('overview', async () => {
      const res = await portfolioApi.getPortfolioOverview()
      if (res.success) return res.data
      throw new Error('API failed')
    })
    // If we have a specific advice, load its prescription into the matrix
    if (adv) {
      // merge prescription into matrix as positions_detail
      const rx = adv.prescription || []
      const byIndustry: Record<string, AdviceItem[]> = {}
      for (const item of rx) {
        const ib = (item as any).industry_bucket || '其他'
        byIndustry[ib] = byIndustry[ib] || []
        byIndustry[ib].push(item)
      }
      if (overview.value?.matrix) {
        for (const row of overview.value.matrix) {
          row.positions_detail = byIndustry[row.industry] || []
        }
      }
    }
  } catch { /* ignore */ }
  loading.value = false
}

async function loadHistory() {
  try {
    adviceHistory.value = await loadWithCache('advice-history', async () => {
      const res = await portfolioApi.getAdviceHistory(1, 20)
      if (res.success) return (res.data.items || []).filter((a: PortfolioAdvice) => a.status === 'COMPLETED')
      throw new Error('API failed')
    })
    if (adviceHistory.value.length > 0) {
      latestAdvice.value = adviceHistory.value[0]
    }
  } catch { /* ignore */ }
}

onMounted(() => {
  loadOverview()
  loadHistory()
})
</script>

<style scoped>
.portfolio-overview { max-width: 1400px; margin: 0 auto; }
.page-content { padding: 20px; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 6px; }
.card-header { padding: 14px 20px; font-weight: 600; border-bottom: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 20px; }
.industry-table { width: 100%; border-collapse: collapse; }
.industry-table th { text-align: left; padding: 10px 14px; font-size: 12px; color: #909399; border-bottom: 1px solid #eee; white-space: nowrap; }
.industry-table td { padding: 12px 14px; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.industry-row { cursor: pointer; transition: background 0.15s; }
.industry-row:hover { background: #f5f7fa; }
.row-go { border-left: 3px solid #67c23a; }
.row-nogo { border-left: 3px solid #f56c6c; }

.ind-name { font-weight: 600; margin-right: 6px; }
.ind-source-tag { font-size: 10px; padding: 1px 5px; border-radius: 3px; }
.src-holding { background: #ecf5ff; color: #409eff; }
.src-watchlist { background: #f0f9eb; color: #67c23a; }
.src-vitality { background: #fdf6ec; color: #e6a23c; }

.weight-transition .arrow { margin: 0 6px; color: #c0c4cc; font-size: 11px; }
.weight-transition .target { color: #409eff; font-weight: 600; }

.v-tag { font-size: 11px; padding: 2px 8px; border-radius: 3px; font-weight: 600; }
.v-强烈看好, .v-看好 { background: #f0f9eb; color: #67c23a; }
.v-中性 { background: #f5f7fa; color: #909399; }
.v-看空 { background: #fef0f0; color: #f56c6c; }

.lifecycle-tag { font-size: 11px; color: #e6a23c; background: #fdf6ec; padding: 2px 6px; border-radius: 3px; }

.action { font-size: 12px; font-weight: 600; white-space: nowrap; }
.action-buy { color: #e6a23c; }
.action-sell { color: #409eff; }
.action-hold { color: #909399; }

.industry-snapshot { padding: 16px 0; border-bottom: 1px solid #eee; margin-bottom: 12px; }
.snap-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.snap-label { font-size: 15px; font-weight: 600; }
.snap-money { margin-left: auto; }

.reasoning-text { padding: 8px 0; font-size: 13px; color: #606266; line-height: 1.7; white-space: pre-wrap; }

.rx-section { margin-top: 16px; }
.rx-title { font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.rx-name { font-weight: 600; font-size: 13px; }
.rx-code { font-size: 11px; color: #909399; }

.strat-tag { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.strat-immediate { background: #fef0f0; color: #f56c6c; }
.strat-batch { background: #fdf6ec; color: #e6a23c; }
.strat-conditional { background: #f0f5ff; color: #409eff; }

.expand-content { font-size: 12px; padding: 8px; }
.expand-block { margin-bottom: 10px; }
.expand-block strong { display: block; margin-bottom: 4px; color: #303133; }
.batch-line { color: #606266; margin: 2px 0; padding-left: 12px; }

.history-card { padding: 12px 16px; border-bottom: 1px solid #f5f5f5; cursor: pointer; }
.history-card:hover { background: #f5f7fa; }
.history-card-selected { border-left: 3px solid #409eff; background: #ecf5ff; }
.history-card-selected:hover { background: #dbeeff; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.history-date { font-size: 13px; color: #606266; }
.history-summary { font-size: 12px; color: #909399; }

.empty-state { text-align: center; padding: 40px; }
.empty-title { font-size: 16px; color: #606266; margin-bottom: 8px; }
.empty-desc { font-size: 13px; color: #909399; }

.text-muted { color: #c0c4cc; }
.mt-4 { margin-top: 16px; }

.go-badge { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
.go-badge-go { background: #67c23a; color: #fff; }
.go-badge-nogo { background: #f56c6c; color: #fff; }
.go-badge-hold { background: #e9e9eb; color: #909399; }

.row-expanded { background: #f0f9eb; }
.reasoning-row { background: #f9fbf9; }
.reasoning-cell { padding: 10px 14px 10px 28px; font-size: 12px; color: #606266; line-height: 1.7; border-bottom: 1px solid #eee; }

.detail-row { background: #fafcff; }
.detail-cell { padding: 14px 18px 16px 28px; border-bottom: 1px solid #eee; }
.detail-reasoning { font-size: 12px; color: #606266; line-height: 1.7; margin-bottom: 12px; white-space: pre-wrap; }
.stock-detail-table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
.stock-detail-table th { text-align: left; padding: 8px 12px; font-size: 11px; color: #909399; background: #f5f7fa; border-bottom: 1px solid #ebeef5; white-space: nowrap; }
.stock-detail-table td { padding: 9px 12px; font-size: 12px; border-bottom: 1px solid #f5f5f5; white-space: nowrap; }
.stock-detail-table tr:last-child td { border-bottom: none; }
.detail-empty { font-size: 12px; color: #c0c4cc; padding: 8px 0; }
.detail-actions { margin-top: 10px; text-align: right; }
.detail-link { background: none; border: none; color: #409eff; font-size: 12px; cursor: pointer; padding: 0; }
.detail-link:hover { text-decoration: underline; }

.rx-card { border: 1px solid #eee; border-radius: 6px; padding: 12px; margin-bottom: 10px; }
.rx-row1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.rx-row2 { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; font-size: 12px; }
.pos-change { color: #606266; }
.capital-amount { color: #303133; font-weight: 600; }
.timing-badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
.timing-immediate { background: #fef0f0; color: #f56c6c; }
.timing-batch { background: #fdf6ec; color: #e6a23c; }
.timing-conditional, .timing-wait { background: #f0f5ff; color: #409eff; }
.pe-badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.pe-high { background: #fef0f0; color: #f56c6c; }
.pe-low { background: #f0f9eb; color: #67c23a; }
.pe-mid { background: #f5f7fa; color: #909399; }

.debate-card {}
.debate-header { user-select: none; }
.collapse-arrow { font-size: 14px; transition: transform 0.2s; display: inline-block; }
.collapse-arrow.open { transform: rotate(90deg); }
.debate-tabs { display: flex; gap: 0; border-bottom: 1px solid #eee; padding: 0 20px; }
.debate-tab { background: none; border: none; border-bottom: 2px solid transparent; padding: 8px 16px; cursor: pointer; font-size: 13px; color: #606266; }
.debate-tab.active { color: #409eff; border-bottom-color: #409eff; font-weight: 600; }
.debate-content { padding: 12px 20px 16px; }
.debate-empty { padding: 32px; text-align: center; color: #c0c4cc; font-size: 13px; }
.debate-content pre { font-size: 13px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; max-height: 400px; overflow-y: auto; margin: 0; color: #303133; background: #f8f9fa; border-radius: 4px; padding: 12px; }

/* ===== 资产配比总揽（大类）===== */
.card-header .sub { font-size: 12px; color: #909399; font-weight: 400; }
.alloc-wrap { padding: 18px 20px; }
.alloc-bar-label { font-size: 12px; color: #909399; margin: 10px 0 5px; }
.stacked { display: flex; height: 30px; border-radius: 5px; overflow: hidden; }
.stacked .seg { display: flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; font-weight: 600; min-width: 0; cursor: default; }
.stacked .seg span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px; }
.alloc-note { font-size: 12px; color: #e6a23c; background: #fdf6ec; padding: 8px 12px; border-radius: 4px; margin: 10px 0; }
.alloc-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.alloc-table th { text-align: left; padding: 9px 14px; font-size: 12px; color: #909399; border-bottom: 1px solid #eee; }
.alloc-table td { padding: 11px 14px; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.alloc-row { cursor: pointer; transition: background .15s; }
.alloc-row:hover { background: #f5f7fa; }
.alloc-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px; vertical-align: 0; }
.alloc-name { font-weight: 600; }
.alloc-table .target { color: #409eff; font-weight: 600; }
.drill-hint { color: #409eff; font-size: 12px; }

/* 矩阵收口提示 + 滚动高亮 */
.matrix-hint { font-size: 12px; color: #e6a23c; background: #fdf6ec; padding: 8px 20px; border-bottom: 1px solid #faecd8; }
.matrix-flash { animation: matrixFlash 1.2s; }
@keyframes matrixFlash { 0% { box-shadow: 0 0 0 3px #409eff; } 100% { box-shadow: 0 1px 3px rgba(0,0,0,0.08); } }

/* ===== 通用下钻抽屉（60%）===== */
.drawer-mask { position: fixed; inset: 0; background: rgba(0,0,0,.3); z-index: 999; }
.drawer-panel { position: fixed; top: 0; right: 0; width: 60%; max-width: 880px; height: 100vh; background: #fff; box-shadow: -4px 0 12px rgba(0,0,0,.12); z-index: 1000; overflow-y: auto; padding: 24px 28px; }
.drawer-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.drawer-title { font-size: 18px; font-weight: 700; }
.drawer-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #909399; }
.snapshot { display: flex; gap: 24px; flex-wrap: wrap; background: #f8f9fb; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
.snap-item .k { color: #909399; font-size: 12px; }
.snap-item .v { font-size: 16px; font-weight: 700; margin-top: 2px; }
.snap-item .v .arrow { margin: 0 6px; color: #c0c4cc; font-size: 12px; }
.snap-item .v .target { color: #409eff; }
.reasoning-box { border: 1px solid #ebeef5; border-radius: 6px; margin-bottom: 16px; }
.reasoning-head { padding: 10px 14px; font-weight: 600; font-size: 13px; background: #fafafa; }
.reasoning-body { padding: 12px 14px; font-size: 13px; line-height: 1.8; color: #606266; white-space: pre-wrap; }
.rx-sub { font-size: 12px; color: #909399; font-weight: 400; margin-left: 6px; }

/* 处方表 + Tier1 展开 */
.rx-table { width: 100%; border-collapse: collapse; border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; }
.rx-table th { text-align: left; padding: 9px 12px; font-size: 11px; color: #909399; background: #f5f7fa; border-bottom: 1px solid #ebeef5; white-space: nowrap; }
.rx-table td { padding: 10px 12px; font-size: 12px; border-bottom: 1px solid #f5f5f5; white-space: nowrap; }
.rx-main { cursor: pointer; }
.rx-main:hover { background: #f5f7fa; }
.caret { display: inline-block; width: 14px; color: #c0c4cc; transition: transform .2s; }
.rx-main.open .caret { transform: rotate(90deg); color: #409eff; }
.rx-detail-row > td { background: #fbfcfe; padding: 0 !important; }
.tier1 { padding: 14px 16px; }
.tier1-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.tier1-tag { font-size: 11px; background: #ecf5ff; color: #409eff; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.rating { font-size: 12px; font-weight: 700; padding: 2px 10px; border-radius: 4px; background: #f0f9eb; color: #529b2e; }
.t1-target { font-size: 12px; color: #909399; }
.t1-target b { color: #409eff; }
.tier1-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 18px; margin-bottom: 10px; }
.t1-block { font-size: 12px; line-height: 1.75; color: #4a4a4a; }
.t1-block .lbl { color: #909399; font-weight: 600; margin-bottom: 3px; }
.t1-bull { border-left: 3px solid #67c23a; padding-left: 10px; }
.t1-bear { border-left: 3px solid #f56c6c; padding-left: 10px; }
.t1-meta { display: flex; gap: 20px; flex-wrap: wrap; font-size: 11px; color: #909399; border-top: 1px dashed #e4e7ed; padding-top: 9px; }
.t1-meta b { color: #606266; }
.rx-empty { color: #c0c4cc; padding: 24px; text-align: center; font-size: 13px; }
</style>