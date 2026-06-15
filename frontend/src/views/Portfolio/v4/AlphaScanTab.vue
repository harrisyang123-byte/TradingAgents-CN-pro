<template>
  <div class="alpha-scan">
    <div class="scan-intro">
      <div class="scan-intro-title">🌿 选股池 &amp; 产业链瓶颈</div>
      <div class="scan-intro-sub">
        自下而上进攻链产出：全市场横向扫描 + 产业链瓶颈纵向深挖（Serenity 五因子）+ 被错杀龙头。
        <span class="scan-warn">数据均为 verified_AKShare + 演绎推理，标的代码可点击下钻个股详情。</span>
      </div>
      <div v-if="index" class="scan-gen">扫描生成日期：{{ index.generated }} · 共 {{ index.scan_files.length }} 份成果</div>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />
    <el-empty v-else-if="!index" description="暂无扫描成果（请先跑 build_snapshot_v4.py）" />

    <template v-else>
      <!-- 真 alpha 清单高亮（来自 deep_chain_final 的终极清单） -->
      <el-card v-if="alphaList" class="alpha-highlight" shadow="never">
        <template #header>
          <span class="hl-title">⭐ 终极真 alpha 清单（全程深挖 + verified 后）</span>
        </template>
        <div v-for="(val, key) in alphaList" :key="key" class="alpha-row">
          <div class="alpha-cat">{{ key }}</div>
          <div class="alpha-val" v-html="renderWithCodes(String(val))" @click="onCodeClick"></div>
        </div>
      </el-card>

      <!-- 各扫描成果折叠面板 -->
      <el-collapse v-model="activeNames" class="scan-collapse">
        <el-collapse-item v-for="f in index.scan_files" :key="f.file" :name="f.file">
          <template #title>
            <span class="scan-file-title">{{ friendlyName(f.file) }}</span>
            <el-tag v-if="f.method" size="small" type="info" class="scan-method">{{ truncate(f.method, 50) }}</el-tag>
          </template>
          <div class="scan-detail">
            <div v-if="f.key" class="scan-key" v-html="renderWithCodes(String(f.key))" @click="onCodeClick"></div>
            <div v-if="detailCache[f.file]" class="scan-codes">
              <span class="codes-label">提及标的（点击下钻）：</span>
              <el-tag
                v-for="c in extractCodes(detailCache[f.file])"
                :key="c"
                size="small"
                class="code-chip"
                effect="plain"
                @click="$emit('open-stock', c)"
              >{{ c }}</el-tag>
              <span v-if="extractCodes(detailCache[f.file]).length === 0" class="no-code">（无 A 股代码）</span>
            </div>
            <pre v-if="detailCache[f.file]" class="scan-json">{{ pretty(detailCache[f.file]) }}</pre>
            <el-button v-else size="small" text type="primary" @click="loadDetail(f.file)">展开完整内容 →</el-button>
          </div>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioV4Api, type ScanIndex } from '@/api/portfolioV4'

const emit = defineEmits<{ (e: 'open-stock', code: string): void }>()

const loading = ref(true)
const index = ref<ScanIndex | null>(null)
const alphaList = ref<Record<string, unknown> | null>(null)
const activeNames = ref<string[]>([])
const detailCache = ref<Record<string, Record<string, unknown>>>({})

const NAME_MAP: Record<string, string> = {
  'deep_chain_final_2026-06-15.json': '🏁 八大主线深挖收敛（真 alpha 清单）',
  'ai_deep_chokepoint_2026-06-15.json': 'AI 产业链最底层物理瓶颈',
  'industry_chokepoint_2026-06-15.json': '行业供应链瓶颈（消费电子/化工/有色）',
  'robot_pharma_deep_2026-06-15.json': '人形机器人 + 创新药 CXO 最底层',
  'bottleneck_chain_batch_2026-06-15.json': '瓶颈选股链（紫苏叶五因子）',
  'errokilled_leaders_2026-06-15.json': '被错杀的卡位龙头（预期差）',
  'zisu_bottleneck_alpha.json': '紫苏叶瓶颈 alpha（三主线）',
  'chokepoint_alpha.json': '产业链瓶颈 alpha',
  'alpha_picks.json': '全市场扫描 alpha（横向）',
  'candidates.json': '全市场扫描候选池',
}
function friendlyName(f: string): string { return NAME_MAP[f] ?? f.replace(/\.json$/, '') }
function truncate(s: string, n: number): string { return s.length > n ? s.slice(0, n) + '…' : s }
function pretty(o: unknown): string { return JSON.stringify(o, null, 2) }

// A股6位(0/3/6开头)+港股5位代码识别
const CODE_RE = /\b([036]\d{5}|0\d{4})\b/g
function extractCodes(obj: unknown): string[] {
  const s = JSON.stringify(obj)
  const set = new Set<string>()
  let m: RegExpExecArray | null
  const re = new RegExp(CODE_RE)
  while ((m = re.exec(s)) !== null) set.add(m[1])
  return Array.from(set)
}
function renderWithCodes(text: string): string {
  const esc = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc.replace(/\b([036]\d{5}|0\d{4})\b/g, '<a class="code-link" data-code="$1">$1</a>')
}
function onCodeClick(e: MouseEvent) {
  const t = e.target as HTMLElement
  if (t.classList.contains('code-link')) {
    const code = t.getAttribute('data-code')
    if (code) emit('open-stock', code)
  }
}

async function loadDetail(file: string) {
  try {
    const resp = await portfolioV4Api.getScanFile(file)
    if (resp.success) detailCache.value[file] = resp.data
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const resp = await portfolioV4Api.getScanIndex()
    if (resp.success) {
      index.value = resp.data
      // 加载 deep_chain_final 提取真 alpha 清单
      const finalFile = resp.data.scan_files.find((f) => f.file.startsWith('deep_chain_final'))
      if (finalFile) {
        const fr = await portfolioV4Api.getScanFile(finalFile.file)
        if (fr.success) {
          detailCache.value[finalFile.file] = fr.data
          const d = fr.data as Record<string, unknown>
          const alphaKey = Object.keys(d).find((k) => k.includes('真alpha') || k.includes('alpha清单'))
          if (alphaKey && typeof d[alphaKey] === 'object') {
            alphaList.value = d[alphaKey] as Record<string, unknown>
          }
        }
      }
    }
  } catch { /* ignore */ } finally { loading.value = false }
})
</script>

<style scoped>
.alpha-scan { padding: 4px 2px; }
.scan-intro { margin-bottom: 16px; }
.scan-intro-title { font-size: 18px; font-weight: 700; color: #303133; }
.scan-intro-sub { font-size: 13px; color: #606266; margin-top: 4px; line-height: 1.6; }
.scan-warn { color: #e6a23c; }
.scan-gen { font-size: 12px; color: #909399; margin-top: 6px; }
.alpha-highlight { margin-bottom: 16px; border: 1px solid #b3e19d; background: #f0f9eb; }
.hl-title { font-weight: 700; color: #67c23a; }
.alpha-row { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px dashed #e4e7ed; }
.alpha-row:last-child { border-bottom: none; }
.alpha-cat { flex: 0 0 110px; font-weight: 600; color: #529b2e; font-size: 13px; }
.alpha-val { flex: 1; font-size: 13px; color: #303133; line-height: 1.7; }
.scan-collapse { margin-top: 8px; }
.scan-file-title { font-weight: 600; margin-right: 10px; }
.scan-method { max-width: 420px; }
.scan-detail { padding: 4px 0; }
.scan-key { font-size: 13px; color: #303133; background: #fdf6ec; padding: 8px 12px; border-radius: 4px; margin-bottom: 10px; line-height: 1.7; }
.scan-codes { margin-bottom: 10px; }
.codes-label { font-size: 12px; color: #909399; margin-right: 6px; }
.code-chip { cursor: pointer; margin: 2px 4px 2px 0; }
.code-chip:hover { color: #409eff; }
.no-code { font-size: 12px; color: #c0c4cc; }
.scan-json { font-size: 12px; background: #f5f7fa; padding: 12px; border-radius: 4px; max-height: 480px; overflow: auto; white-space: pre-wrap; word-break: break-word; color: #5c6b77; }
:deep(.code-link) { color: #409eff; cursor: pointer; text-decoration: underline; }
</style>
