<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { fundApi, type FundBasicInfo, type FundHolding, type FundSector, type FundNavPoint } from '@/api/fund'

const router = useRouter()
const route = useRoute()

const code = computed(() => route.params.code as string)

// ---- 各区域独立状态 ----
type ZoneState = 'loading' | 'ideal' | 'empty' | 'error'

const basicInfoState = ref<ZoneState>('loading')
const holdingsState = ref<ZoneState>('loading')
const sectorState = ref<ZoneState>('loading')
const navState = ref<ZoneState>('loading')

const basicInfo = ref<FundBasicInfo | null>(null)
const holdings = ref<FundHolding[]>([])
const sectors = ref<FundSector[]>([])
const navHistory = ref<FundNavPoint[]>([])

const basicInfoError = ref('')
const holdingsError = ref('')
const sectorError = ref('')
const navError = ref('')

const navPeriod = ref('1年')
const navPeriodOptions = ['1月', '3月', '6月', '1年', '3年', '成立来']

// ECharts
const navChartRef = ref<HTMLElement | null>(null)
let navChart: echarts.ECharts | null = null

function renderNavChart() {
  if (!navChartRef.value || !navHistory.value.length) return
  // 每次重新 init 确保 DOM 已挂载
  if (navChart) { navChart.dispose(); navChart = null }
  navChart = echarts.init(navChartRef.value)
  const dates = navHistory.value.map(p => p.date)
  const navs = navHistory.value.map(p => p.nav)
  navChart.setOption({
    tooltip: { trigger: 'axis', formatter: (params: any) => {
      const p = params[0]
      return `${p.axisValue}<br/>单位净值: <b>${p.value?.toFixed(4) ?? '--'}</b>`
    }},
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11, color: '#909399' }, axisLine: { lineStyle: { color: '#ebeef5' } } },
    yAxis: { type: 'value', scale: true, axisLabel: { fontSize: 11, color: '#909399', formatter: (v: number) => v.toFixed(2) }, splitLine: { lineStyle: { color: '#f5f7fa' } } },
    series: [{ type: 'line', data: navs, smooth: true, symbol: 'none', lineStyle: { color: '#409eff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.2)' }, { offset: 1, color: 'rgba(64,158,255,0)' }]) } }],
  })
}

// ---- 整体页面状态(用于初始加载/空/错误时全屏覆盖) ----
// 初始: loading → 任一区域有数据就切换 ideal
// 全空: 三个区域都 empty → page empty
// 全错: 三个区域都 error → page error
type PageState = 'loading' | 'ideal' | 'empty' | 'error'
const pageState = ref<PageState>('loading')
const fatalError = ref('')

// ---- 加载数据 ----
async function loadBasicInfo() {
  basicInfoState.value = 'loading'
  basicInfoError.value = ''
  try {
    const res = await fundApi.getBasicInfo(code.value)
    if (res.success && res.data) {
      basicInfo.value = res.data
      basicInfoState.value = 'ideal'
    } else {
      basicInfoState.value = 'empty'
    }
  } catch (e: any) {
    basicInfoError.value = e?.message || '获取基础信息失败'
    basicInfoState.value = 'error'
  }
}

async function loadHoldings() {
  holdingsState.value = 'loading'
  holdingsError.value = ''
  try {
    const res = await fundApi.getTopHoldings(code.value)
    if (res.success) {
      holdings.value = res.data || []
      holdingsState.value = res.data?.length ? 'ideal' : 'empty'
    } else {
      holdingsState.value = 'empty'
    }
  } catch (e: any) {
    holdingsError.value = e?.message || '获取持仓数据失败'
    holdingsState.value = 'error'
  }
}

async function loadSectors() {
  sectorState.value = 'loading'
  sectorError.value = ''
  try {
    const res = await fundApi.getSectorDistribution(code.value)
    if (res.success) {
      sectors.value = res.data || []
      sectorState.value = res.data?.length ? 'ideal' : 'empty'
    } else {
      sectorState.value = 'empty'
    }
  } catch (e: any) {
    sectorError.value = e?.message || '获取行业分布失败'
    sectorState.value = 'error'
  }
}

async function loadNavHistory() {
  navState.value = 'loading'
  navError.value = ''
  try {
    const res = await fundApi.getNavHistory(code.value, navPeriod.value)
    if (res.success) {
      navHistory.value = res.data || []
      navState.value = res.data?.length ? 'ideal' : 'empty'
      if (navState.value === 'ideal') {
        await nextTick()
        renderNavChart()
      }
    } else {
      navState.value = 'empty'
    }
  } catch (e: any) {
    navError.value = e?.message || '获取净值数据失败'
    navState.value = 'error'
  }
}

async function loadAll() {
  pageState.value = 'loading'
  fatalError.value = ''
  await Promise.allSettled([
    loadBasicInfo(),
    loadHoldings(),
    loadSectors(),
    loadNavHistory(),
  ])
  const states = [basicInfoState.value, holdingsState.value, sectorState.value, navState.value]
  if (states.every(s => s === 'empty')) {
    pageState.value = 'empty'
  } else if (states.every(s => s === 'error')) {
    fatalError.value = '所有基金数据加载失败，请检查网络连接后重试。'
    pageState.value = 'error'
  } else {
    pageState.value = 'ideal'
  }
}

onUnmounted(() => {
  navChart?.dispose()
  navChart = null
})

function retryAll() { loadAll() }

function goBack() { router.push({ name: 'PortfolioHome' }) }

function startAnalysis() {
  // 跳转到分析页面，预填基金代码和类型
  router.push({
    name: 'SingleAnalysis',
    query: {
      symbol: code.value,
      instrument_type: 'fund',
      fund_type: basicInfo.value?.type || '',
    }
  })
}

// ---- 更新时间戳 ----
const updateTime = computed(() => {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`
})

// ---- 饼图 ----
const sectorColors = [
  '#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#7c3aed',
  '#ff85c0', '#36cfc9', '#b37feb', '#ffa940',
]

function calcConicGradient(list: FundSector[]) {
  if (!list.length) return ''
  const total = list.reduce((s, i) => s + i.ratio, 0) || 1
  let start = 0
  const stops = list.map((item, i) => {
    const pct = (item.ratio / total) * 360
    const end = start + pct
    const color = sectorColors[i % sectorColors.length]
    const seg = `${color} ${start}deg ${end}deg`
    start = end
    return seg
  })
  return `conic-gradient(${stops.join(', ')})`
}

const conicStyle = computed(() => calcConicGradient(sectors.value))
const totalSectors = computed(() => sectors.value.length)

// ---- 前十大集中度 ----
const topConcentration = computed(() => {
  if (!holdings.value.length) return 0
  return holdings.value.reduce((s, h) => s + h.ratio, 0)
})

// ---- 工具 ----
function maxHoldingRatio() {
  if (!holdings.value.length) return 100
  return Math.max(...holdings.value.map(h => h.ratio), 1)
}

// ---- 初始化 ----
onMounted(() => {
  if (!code.value) {
    pageState.value = 'empty'
    return
  }
  loadAll()
})
</script>

<template>
  <div class="fund-detail">
    <!-- ============ 整体加载态(骨架屏) ============ -->
    <template v-if="pageState === 'loading'">
      <!-- 返回导航（骨架） -->
      <div class="skeleton" style="width:100px;height:16px;margin-bottom:24px;"></div>
      <!-- 标题行（骨架） -->
      <div class="flex items-center gap-2 mb-5">
        <div class="skeleton" style="width:20px;height:20px;"></div>
        <div class="skeleton" style="width:80px;height:18px;"></div>
      </div>
      <!-- 卡片 1 骨架 -->
      <div class="card mb-4">
        <div class="card-header"><div class="skeleton" style="width:100px;height:16px;"></div></div>
        <div class="card-body">
          <div class="flex items-start gap-4">
            <div class="skeleton" style="width:56px;height:56px;border-radius:12px;"></div>
            <div class="flex-1">
              <div class="skeleton" style="width:240px;height:20px;margin-bottom:16px;"></div>
              <div class="info-grid">
                <div v-for="i in 6" :key="i">
                  <div class="skeleton" style="width:60%;height:12px;margin-bottom:6px;"></div>
                  <div class="skeleton" style="width:80%;height:16px;"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- 卡片 2 骨架 -->
      <div class="card mb-4">
        <div class="card-header"><div class="skeleton" style="width:140px;height:16px;"></div></div>
        <div class="card-body" style="padding:20px;">
          <div v-for="i in 5" :key="i" class="flex gap-4 items-center" style="margin-bottom:12px;">
            <div class="skeleton" style="width:28px;height:20px;border-radius:4px;"></div>
            <div class="skeleton" style="width:80px;height:14px;"></div>
            <div class="skeleton" style="width:90px;height:14px;"></div>
            <div class="skeleton" style="width:60px;height:14px;"></div>
            <div class="skeleton" style="flex:1;height:14px;"></div>
          </div>
        </div>
      </div>
      <!-- 卡片 3 骨架 -->
      <div class="card mb-4">
        <div class="card-header"><div class="skeleton" style="width:100px;height:16px;"></div></div>
        <div class="card-body flex items-start gap-8">
          <div class="skeleton" style="width:180px;height:180px;border-radius:50%;flex-shrink:0;"></div>
          <div class="flex-1 flex flex-col gap-3">
            <div v-for="i in 6" :key="i" class="skeleton" :style="{ width: (100 - i * 10) + '%', height: '16px' }"></div>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ 整体空态 ============ -->
    <template v-else-if="pageState === 'empty'">
      <div class="detail-header">
        <a class="back-link" @click="goBack">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-sm"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          <span>返回持仓</span>
        </a>
      </div>
      <div class="page-title-row">
        <div class="title-left">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-md primary"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
          <span class="title-text">基金详情</span>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="empty-state-wrap">
            <svg viewBox="0 0 24 24" fill="#c0c4cc" class="empty-icon"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
            <div class="empty-title">无可用的基金数据</div>
            <div class="empty-desc">该基金代码可能未正确传递，或对应基金的信息尚不可用。请确认基金代码有效，或稍后重试。</div>
            <button class="btn btn-primary btn-sm" @click="retryAll">刷新数据</button>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ 整体错误态 ============ -->
    <template v-else-if="pageState === 'error'">
      <div class="detail-header">
        <a class="back-link" @click="goBack">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-sm"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          <span>返回持仓</span>
        </a>
      </div>
      <div class="page-title-row">
        <div class="title-left">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-md primary"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
          <span class="title-text">基金详情</span>
        </div>
        <button class="btn btn-plain btn-sm" @click="retryAll">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-xs"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
          重试
        </button>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="error-state-wrap">
            <svg viewBox="0 0 24 24" fill="#f56c6c" class="error-icon"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
            <div class="error-title">基金数据加载失败</div>
            <div class="error-desc">{{ fatalError }}</div>
            <div class="error-box">
              <span class="error-box-text">错误详情：API 请求失败 — <code>/api/fund/*?code={{ code }}</code></span>
            </div>
            <button class="btn btn-primary" @click="retryAll">
              <svg viewBox="0 0 24 24" fill="currentColor" class="icon-xs"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
              重新加载
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- ============ 理想态 ============ -->
    <template v-else>
      <!-- 返回导航 -->
      <div class="detail-header">
        <a class="back-link" @click="goBack">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-sm"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
          <span>返回持仓</span>
        </a>
      </div>

      <!-- 页面标题 -->
      <div class="page-title-row">
        <div class="title-left">
          <svg viewBox="0 0 24 24" fill="currentColor" class="icon-md primary"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
          <span class="title-text">基金详情</span>
          <span class="update-time">
            <svg viewBox="0 0 24 24" fill="currentColor" class="icon-update"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
            更新于 {{ updateTime }}
          </span>
        </div>
        <div class="title-right">
          <button class="btn btn-primary btn-sm" @click="startAnalysis" style="margin-right:8px;">
            <svg viewBox="0 0 24 24" fill="currentColor" class="icon-xs"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>
            AI 分析
          </button>
          <button class="btn btn-plain btn-sm" @click="retryAll">
            <svg viewBox="0 0 24 24" fill="currentColor" class="icon-xs"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
            刷新
          </button>
        </div>
      </div>

      <!-- ============ 卡片 1: 基金基础信息 ============ -->
      <div class="card mb-4">
        <div class="card-header">
          <span>基金基础信息</span>
          <span v-if="basicInfo?.type" class="tag tag-blue">{{ basicInfo.type }}</span>
        </div>
        <div class="card-body">
          <!-- 加载态 -->
          <div v-if="basicInfoState === 'loading'" class="flex items-start gap-4">
            <div class="skeleton" style="width:56px;height:56px;border-radius:12px;"></div>
            <div class="flex-1">
              <div class="skeleton" style="width:240px;height:20px;margin-bottom:16px;"></div>
              <div class="info-grid">
                <div v-for="i in 6" :key="i">
                  <div class="skeleton" style="width:60%;height:12px;margin-bottom:6px;"></div>
                  <div class="skeleton" style="width:80%;height:16px;"></div>
                </div>
              </div>
            </div>
          </div>
          <!-- 错误态 -->
          <div v-else-if="basicInfoState === 'error'" class="zone-error">
            <div class="zone-error-msg">{{ basicInfoError }}</div>
            <button class="btn btn-primary btn-sm" @click="loadBasicInfo">重试</button>
          </div>
          <!-- 空态 -->
          <div v-else-if="basicInfoState === 'empty'" class="zone-empty">暂无基金数据</div>
          <!-- 理想态 -->
          <div v-else-if="basicInfo" class="flex items-start gap-4">
            <div class="fund-icon">
              <svg viewBox="0 0 24 24" fill="#fff"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-3 flex-wrap">
                <h2 class="fund-name">{{ basicInfo.name || basicInfo.code }}</h2>
                <span class="tag tag-gray">{{ basicInfo.code }}</span>
                <span v-if="basicInfo.manager" class="tag tag-purple">{{ basicInfo.manager }}</span>
              </div>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">基金代码</span>
                  <span class="info-value">{{ basicInfo.code }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">基金类型</span>
                  <span class="info-value">{{ basicInfo.type || '--' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">最新规模</span>
                  <span class="info-value highlight">{{ basicInfo.scale != null ? basicInfo.scale.toFixed(2) + ' 亿元' : '--' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">基金经理</span>
                  <span class="info-value">{{ basicInfo.manager || '--' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">成立日期</span>
                  <span class="info-value">{{ basicInfo.establishment_date || '--' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ============ 卡片 2: 净值历史走势 ============ -->
      <div class="card mb-4">
        <div class="card-header">
          <span>净值历史走势</span>
          <div class="period-tabs">
            <button
              v-for="p in navPeriodOptions" :key="p"
              class="period-btn" :class="{ active: navPeriod === p }"
              @click="navPeriod = p; loadNavHistory()"
            >{{ p }}</button>
          </div>
        </div>
        <div class="card-body" style="padding: 16px 20px;">
          <div v-if="navState === 'loading'" class="skeleton" style="width:100%;height:260px;border-radius:4px;"></div>
          <div v-else-if="navState === 'error'" class="zone-error">
            <div class="zone-error-msg">{{ navError }}</div>
            <button class="btn btn-primary btn-sm" @click="loadNavHistory">重试</button>
          </div>
          <div v-else-if="navState === 'empty'" class="zone-empty">暂无净值数据</div>
          <!-- 始终保留 DOM，避免切换 period 时 ECharts 实例失效 -->
          <div v-show="navState === 'ideal'" ref="navChartRef" style="width:100%;height:260px;"></div>
        </div>
      </div>

      <!-- ============ 卡片 3: 前十大重仓股 ============ -->
      <div class="card mb-4">
        <div class="card-header">
          <div class="flex items-center gap-2">
            <span>前十大重仓股</span>
            <span class="text-secondary" style="font-size:12px;">(穿透数据)</span>
          </div>
          <div style="font-size:12px;color:#909399;">
            <span class="tag tag-gray" style="font-size:11px;padding:1px 6px;margin-right:8px;">数据来源: 最近报告期</span>
            <span v-if="holdingsState === 'ideal'">前十大集中度: {{ topConcentration.toFixed(2) }}%</span>
          </div>
        </div>
        <div class="card-body" style="padding:0;">
          <!-- 加载态 -->
          <div v-if="holdingsState === 'loading'" style="padding:20px;">
            <div v-for="i in 5" :key="i" class="flex gap-4 items-center" style="margin-bottom:12px;">
              <div class="skeleton" style="width:28px;height:20px;border-radius:4px;"></div>
              <div class="skeleton" style="width:80px;height:14px;"></div>
              <div class="skeleton" style="width:90px;height:14px;"></div>
              <div class="skeleton" style="width:60px;height:14px;"></div>
              <div class="skeleton" style="flex:1;height:14px;"></div>
            </div>
          </div>
          <!-- 错误态 -->
          <div v-else-if="holdingsState === 'error'" class="zone-error" style="padding:20px;">
            <div class="zone-error-msg">{{ holdingsError }}</div>
            <button class="btn btn-primary btn-sm" @click="loadHoldings">重试</button>
          </div>
          <!-- 空态 -->
          <div v-else-if="holdingsState === 'empty'" class="zone-empty" style="padding:40px 20px;">
            <span v-if="basicInfo?.type && (basicInfo.type.includes('QDII') || basicInfo.type.includes('ETF') || basicInfo.type.includes('货币'))">
              {{ basicInfo.type }} 基金暂不支持重仓股穿透展示
            </span>
            <span v-else>该基金暂无持仓数据</span>
          </div>
          <!-- 理想态 -->
          <div v-else>
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width:48px;text-align:center;">排名</th>
                  <th>股票名称</th>
                  <th>股票代码</th>
                  <th style="text-align:right;">占净值比例</th>
                  <th>持仓占比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(h, i) in holdings" :key="h.stock_code">
                  <td style="text-align:center;">
                    <span class="rank-tag" :class="{ top3: i < 3 }">{{ i + 1 }}</span>
                  </td>
                  <td><span class="stock-link">{{ h.stock_name }}</span></td>
                  <td><span class="code-text">{{ h.stock_code }}</span></td>
                  <td style="text-align:right;font-weight:600;">{{ h.ratio.toFixed(2) }}%</td>
                  <td style="padding-right:32px;">
                    <div class="progress-bar" style="width:160px;">
                      <div class="progress-fill" :style="{ width: (h.ratio / maxHoldingRatio() * 100) + '%', background: 'linear-gradient(90deg, #409eff, #66b1ff)' }"></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <!-- 数据脚注 -->
            <div class="data-source-note label-top">
              <span class="label">数据来源：</span>最近一期基金报告。前十大重仓股占基金净值比例合计
              <span style="color:#409eff;font-weight:600;">{{ topConcentration.toFixed(2) }}%</span>。
            </div>
          </div>
        </div>
      </div>

      <!-- ============ 卡片 4: 行业分布 ============ -->
      <div class="card mb-4">
        <div class="card-header">
          <div class="flex items-center gap-2">
            <span>行业分布</span>
            <span class="text-secondary" style="font-size:12px;">(前{{ totalSectors }}大行业)</span>
          </div>
          <span class="tag tag-gray" style="font-size:11px;">数据来源: 最近报告期</span>
        </div>
        <div class="card-body">
          <!-- 加载态 -->
          <div v-if="sectorState === 'loading'" class="flex items-start gap-8">
            <div class="skeleton" style="width:180px;height:180px;border-radius:50%;flex-shrink:0;"></div>
            <div class="flex-1 flex flex-col gap-3">
              <div v-for="i in 6" :key="i" class="skeleton" :style="{ width: (100 - i * 10) + '%', height: '16px' }"></div>
            </div>
          </div>
          <!-- 错误态 -->
          <div v-else-if="sectorState === 'error'" class="zone-error">
            <div class="zone-error-msg">{{ sectorError }}</div>
            <button class="btn btn-primary btn-sm" @click="loadSectors">重试</button>
          </div>
          <!-- 空态 -->
          <div v-else-if="sectorState === 'empty'" class="zone-empty">暂无行业数据</div>
          <!-- 理想态 -->
          <div v-else class="flex items-start gap-6 flex-wrap">
            <!-- 饼图 -->
            <div class="donut-wrap">
              <div class="donut-chart" :style="{ background: conicStyle }"></div>
              <div class="donut-center">
                <span class="donut-label">持股行业</span>
                <span class="donut-value">{{ totalSectors }}</span>
              </div>
            </div>
            <!-- 图例 -->
            <div class="donut-legend">
              <div v-for="(s, i) in sectors" :key="s.sector_name" class="legend-item">
                <div class="legend-dot" :style="{ background: sectorColors[i % sectorColors.length] }"></div>
                <span class="legend-label">{{ s.sector_name }}</span>
                <span class="legend-pct">{{ s.ratio.toFixed(1) }}%</span>
              </div>
            </div>
            <!-- 条形图 -->
            <div class="sector-bars">
              <div style="font-size:12px;color:#909399;margin-bottom:8px;">行业权重排序</div>
              <div v-for="(s, i) in sectors" :key="s.sector_name" class="industry-bar">
                <span class="rank-num">{{ i + 1 }}</span>
                <span class="industry-name">{{ s.sector_name }}</span>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: s.ratio + '%', background: sectorColors[i % sectorColors.length] }"></div>
                </div>
                <span class="pct-value">{{ s.ratio.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <!-- 数据脚注 -->
          <div v-if="sectorState === 'ideal'" class="data-source-note">
            <span class="label">说明：</span>行业分类依据基金报告披露数据。占比为该行业持仓市值占基金净值的比例。
          </div>
        </div>
      </div>

      <!-- ============ 卡片 5: 基金经理 ============ -->
      <div class="card mb-4">
        <div class="card-header">
          <span>基金经理</span>
        </div>
        <div class="card-body">
          <div class="flex items-start gap-4">
            <div class="manager-avatar">
              <svg viewBox="0 0 24 24" fill="#409eff"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
            </div>
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2 flex-wrap">
                <span class="manager-name">{{ basicInfo?.manager || '暂无数据' }}</span>
              </div>
              <div class="manager-bio">
                以上为当前基金的基本面数据。基金经理管理的具体风格、历史业绩等详细信息可通过
                <span class="stock-link" @click="goBack">持仓分析</span> 功能进一步了解。
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 数据来源脚注（全局） -->
      <div class="footer-note">
        数据来源：AKShare 接口。基金持仓数据按季度更新，非实时数据。
      </div>
    </template>
  </div>
</template>

<style scoped>
.fund-detail {
  max-width: 1200px;
  margin: 0 auto;
}

/* ---- 净值周期切换 ---- */
.period-tabs {
  display: flex;
  gap: 4px;
}

.period-btn {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  transition: all 0.2s;
}

.period-btn:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }

.period-btn.active { color: #409eff; border-color: #409eff; background: #ecf5ff; font-weight: 600; }

/* ---- 返回链接 ---- */
.detail-header {
  margin-bottom: 12px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #409eff;
  cursor: pointer;
  text-decoration: none;
}

.back-link:hover { color: #66b1ff; }

/* ---- 页面标题 ---- */
.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.update-time {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: #a8abb2;
}

.icon-update {
  width: 13px;
  height: 13px;
}

/* ---- 卡片 ---- */
.card {
  background: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  transition: box-shadow 0.3s;
}

.card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  padding: 14px 20px;
  border-bottom: 1px solid #ebeef5;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-body { padding: 20px; }

.mb-4 { margin-bottom: 16px; }

/* ---- 基金图标 ---- */
.fund-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fund-icon svg { width: 28px; height: 28px; fill: #fff; }

/* ---- 基金名称 ---- */
.fund-name {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  margin: 0;
}

/* ---- 信息网格 ---- */
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 32px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #909399;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.info-value.highlight {
  color: #409eff;
  font-size: 18px;
  font-weight: 700;
}

/* ---- 标签 ---- */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
}

.tag-gray { background: #f4f4f5; color: #909399; border: 1px solid #e9e9eb; }

.tag-purple { background: #f5f0ff; color: #7c3aed; border: 1px solid #ede5ff; }

.tag-blue { background: #ecf5ff; color: #409eff; border: 1px solid #d9ecff; }

/* ---- 表格 ---- */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  background: #fafafa;
  color: #909399;
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  font-size: 12px;
  white-space: nowrap;
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #ebeef5;
  color: #303133;
}

.data-table tbody tr:hover { background: #f5f7fa; }

.data-table tbody tr:last-child td { border-bottom: none; }

/* ---- 排名标签 ---- */
.rank-tag {
  display: inline-block;
  min-width: 22px;
  padding: 2px 6px;
  text-align: center;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  background: #f5f7fa;
  color: #606266;
  border: 1px solid #e4e7ed;
}

.rank-tag.top3 {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid #fde2e2;
}

/* ---- 股票链接 ---- */
.stock-link {
  color: #409eff;
  cursor: pointer;
  text-decoration: none;
  font-weight: 500;
}

.stock-link:hover { color: #66b1ff; }

.code-text { color: #606266; }

/* ---- 进度条 ---- */
.progress-bar {
  height: 8px;
  background: #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

/* ---- 饼图 ---- */
.donut-wrap {
  position: relative;
  width: 180px;
  height: 180px;
  flex-shrink: 0;
}

.donut-chart {
  width: 180px;
  height: 180px;
  border-radius: 50%;
}

.donut-center {
  position: absolute;
  top: 40px;
  left: 40px;
  width: 100px;
  height: 100px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.donut-label { font-size: 11px; color: #909399; }

.donut-value { font-size: 15px; font-weight: 700; color: #303133; }

/* ---- 图例 ---- */
.donut-legend { flex-shrink: 0; }

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-label {
  font-size: 13px;
  color: #606266;
  min-width: 80px;
}

.legend-pct { font-size: 13px; font-weight: 600; color: #303133; }

/* ---- 行业分布条形图 ---- */
.sector-bars {
  flex: 1;
  min-width: 250px;
}

.industry-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f7fa;
}

.industry-bar:last-child { border-bottom: none; }

.rank-num {
  width: 20px;
  font-size: 12px;
  color: #909399;
  text-align: center;
  flex-shrink: 0;
}

.industry-name {
  width: 80px;
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  flex: 1;
  height: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}

.pct-value {
  width: 60px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  text-align: right;
  flex-shrink: 0;
}

/* ---- 数据脚注 ---- */
.data-source-note {
  font-size: 12px;
  color: #a8abb2;
  line-height: 1.6;
  border-top: 1px solid #ebeef5;
  margin-top: 16px;
  padding: 16px 0 0;
}

.data-source-note.label-top {
  margin: 0 20px 8px;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}

.data-source-note .label {
  font-weight: 500;
  color: #909399;
}

/* ---- 全局脚注 ---- */
.footer-note {
  font-size: 12px;
  color: #a8abb2;
  text-align: center;
  padding: 16px 0 32px;
}

/* ---- 基金经理 ---- */
.manager-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ecf5ff, #d9ecff);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.manager-avatar svg { width: 24px; height: 24px; }

.manager-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.manager-bio {
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}

/* ---- 区域状态 ---- */
.zone-error {
  text-align: center;
  padding: 24px;
}

.zone-error-msg {
  font-size: 14px;
  color: #909399;
  margin-bottom: 12px;
}

.zone-empty {
  text-align: center;
  padding: 24px;
  font-size: 14px;
  color: #909399;
}

/* ---- 整体空态 ---- */
.empty-state-wrap {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  width: 100px;
  height: 100px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 20px;
}

/* ---- 整体错误态 ---- */
.error-state-wrap {
  text-align: center;
  padding: 40px 20px;
}

.error-icon {
  width: 56px;
  height: 56px;
  margin-bottom: 16px;
}

.error-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.error-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 20px;
}

.error-box {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 12px 16px;
  display: inline-block;
  margin-bottom: 20px;
}

.error-box-text {
  font-size: 13px;
  color: #f56c6c;
}

.error-box-text code {
  background: rgba(245, 108, 108, 0.1);
  padding: 0 4px;
  border-radius: 2px;
}

/* ---- 按钮 ---- */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid;
  transition: all 0.2s;
  font-weight: 400;
  line-height: 1;
  white-space: nowrap;
}

.btn-primary {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

.btn-primary:hover {
  background: #66b1ff;
  border-color: #66b1ff;
}

.btn-plain {
  background: #fff;
  border-color: #dcdfe6;
  color: #606266;
}

.btn-plain:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background: #ecf5ff;
}

.btn-sm { padding: 5px 12px; font-size: 12px; }

/* ---- 骨架屏 ---- */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.skeleton {
  background: #e4e7ed;
  border-radius: 4px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

/* ---- 图标 ---- */
.icon-sm { width: 16px; height: 16px; }

.icon-xs { width: 14px; height: 14px; }

.icon-md { width: 20px; height: 20px; }

.icon-md.primary { color: #409eff; }

/* ---- 辅助 ---- */
.flex { display: flex; }

.flex-col { flex-direction: column; }

.items-center { align-items: center; }

.items-start { align-items: flex-start; }

.justify-between { justify-content: space-between; }

.gap-2 { gap: 8px; }

.gap-3 { gap: 12px; }

.gap-4 { gap: 16px; }

.gap-6 { gap: 24px; }

.gap-8 { gap: 32px; }

.flex-1 { flex: 1; }

.flex-shrink-0 { flex-shrink: 0; }

.min-w-0 { min-width: 0; }

.mb-3 { margin-bottom: 12px; }

.flex-wrap { flex-wrap: wrap; }

.text-secondary { color: #909399; }
</style>
