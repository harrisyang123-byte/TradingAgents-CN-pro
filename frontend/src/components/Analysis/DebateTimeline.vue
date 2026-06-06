<template>
  <div class="debate-timeline">
    <div v-if="parsedBubbles.length === 0" class="fallback-view">
      <div class="report-content" v-html="formatMarkdown(rawHistory)"></div>
    </div>

    <div v-else class="chat-container">
      <div
        v-for="(bubble, index) in parsedBubbles"
        :key="index"
        class="chat-bubble-wrapper"
        :class="bubble.alignment"
      >
        <!-- 头像区 -->
        <div class="avatar-col" v-if="bubble.alignment === 'left'">
          <div class="avatar" :class="bubble.roleClass">
            <span class="avatar-icon">{{ bubble.icon }}</span>
          </div>
        </div>

        <!-- 气泡内容区 -->
        <div class="bubble-content-col">
          <div class="bubble-meta">
            <span class="bubble-name">{{ bubble.roleName }}</span>
          </div>
          <div class="bubble-body" :class="bubble.roleClass">
            <div class="report-content" v-html="formatMarkdown(bubble.content)"></div>
          </div>

          <!-- 数据凭据条：每条结论的取数状态 ✓ 已核实 / ~ 估算 / ✗ 缺失 -->
          <div v-if="bubble.evidence && bubble.evidence.length" class="evidence-bar">
            <span class="evidence-label">数据凭据</span>
            <span
              v-for="(ev, i) in bubble.evidence"
              :key="i"
              class="evidence-chip"
              :class="evidenceFeature(ev.s).cls"
              :title="(evidenceFeature(ev.s).label) + (ev.src ? ' · 来源：' + ev.src : '')"
            >
              <span class="ev-icon">{{ evidenceFeature(ev.s).icon }}</span>{{ ev.t }}
            </span>
          </div>
        </div>

        <!-- 右侧头像区 -->
        <div class="avatar-col right-avatar" v-if="bubble.alignment === 'right'">
          <div class="avatar" :class="bubble.roleClass">
            <span class="avatar-icon">{{ bubble.icon }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  historyData: {
    type: [String, Object],
    required: true
  }
})

// 安全获取字符串形式的history
const rawHistory = computed(() => {
  if (!props.historyData) return ''

  if (typeof props.historyData === 'string') {
    return props.historyData
  }

  if (typeof props.historyData === 'object') {
    // 优先取 history 字段，其次是 bull_history 或其他能拼接的内容
    const obj = props.historyData as any
    if (obj.history) return String(obj.history)
    if (obj.bull_history || obj.bear_history) {
      let combined = ''
      if (obj.bull_history) combined += obj.bull_history + '\n\n'
      if (obj.bear_history) combined += obj.bear_history + '\n\n'
      return combined
    }
    // Fallback
    return JSON.stringify(obj, null, 2)
  }

  return String(props.historyData)
})

// 解析气泡
// 角色词表：ingest 的 _assemble_debates 按「角色名：内容」前缀输出，这里据此切气泡。
// 长词在前，避免「裁判/反向者」等子串误匹配（行首锚定已基本规避，仍保守排序）。
const ROLE_TOKENS = [
  // 大类配置层（阶段2）
  '战略配置师', '防御配置师', '大类裁判',
  // 市场研判 L1
  '宏观裁判', '跨行业裁判', '行业研究员', '行业反向者',
  // 个股辩论 L3
  '组合反向者', '持仓诊断', 'Scout候选', '激进PM', '保守PM', 'PM裁判',
  // 综合裁决
  '悲观风险总监', '乐观风险分析师', '风控裁判', '组合合成器',
  // 兼容旧英文/中文角色名
  'Bull Analyst', 'Bear Analyst', 'Aggressive Analyst', 'Conservative Analyst',
  'Neutral Analyst', 'Research Manager', 'Manager Analyst', 'Fund Trader',
  '多头分析师', '空头分析师', '激进分析师', '保守分析师', '中性分析师',
  'Trader', 'Manager', '裁判', '分析师',
]

const parsedBubbles = computed(() => {
  const historyStr = rawHistory.value
  if (!historyStr) return []

  const tokens = ROLE_TOKENS.join('|')
  // (?:^|\n) 角色名 [:：] 内容（非贪婪，直到下一个角色名行首或结尾）
  const regex = new RegExp(
    `(?:^|\\n)(?:\\*\\*)?(${tokens})(?:\\*\\*)?\\s*[:：]\\s*([\\s\\S]*?)(?=(?:\\n(?:\\*\\*)?(?:${tokens})(?:\\*\\*)?\\s*[:：]|$))`,
    'gi'
  )

  const bubbles = []
  let match

  while ((match = regex.exec(historyStr)) !== null) {
    const rawRole = match[1].trim()
    let content = match[2].trim()
    const roleFeature = getRoleFeature(rawRole)

    // 提取数据凭据标记行 __EVIDENCE__:<json>（ingest 追加在气泡正文尾部），渲染为 chip 条
    const evidence = extractEvidence(content)
    if (evidence.length) {
      content = stripEvidence(content)
    }

    bubbles.push({
      roleName: roleFeature.name,
      roleClass: roleFeature.className,
      icon: roleFeature.icon,
      alignment: roleFeature.alignment,
      content: content,
      evidence: evidence
    })
  }

  return bubbles
})

// 凭据标记：__EVIDENCE__:[{"t":"...","s":"verified|estimated|missing","src":"..."}]
const EVIDENCE_RE = /__EVIDENCE__:(\[.*?\])\s*$/s

interface EvidenceChip { t: string; s: string; src: string }

function extractEvidence(content: string): EvidenceChip[] {
  const m = content.match(EVIDENCE_RE)
  if (!m) return []
  try {
    const arr = JSON.parse(m[1])
    if (!Array.isArray(arr)) return []
    return arr
      .filter((e: any) => e && typeof e.t === 'string' && e.t.trim())
      .map((e: any) => ({ t: String(e.t).trim(), s: String(e.s || 'estimated'), src: String(e.src || '') }))
  } catch (e) {
    return []
  }
}

function stripEvidence(content: string): string {
  return content.replace(EVIDENCE_RE, '').trim()
}

// 凭据状态 → 展示特征
function evidenceFeature(status: string) {
  if (status === 'verified') return { icon: '✓', cls: 'ev-verified', label: '已核实' }
  if (status === 'missing') return { icon: '✗', cls: 'ev-missing', label: '数据缺失' }
  return { icon: '~', cls: 'ev-estimated', label: '估算' }
}

// 根据角色名称获取特征（左=进攻/多头 绿，右=避险/空头 红，中=裁判 紫）
function getRoleFeature(rawRole: string) {
  const roleLower = rawRole.toLowerCase()

  // 激进 (左侧，橙红) — 先于多头判定
  if (roleLower.includes('aggressive') || rawRole.includes('激进')) {
    return { name: rawRole, className: 'role-aggressive', icon: '⚡', alignment: 'left' }
  }

  // 保守 (右侧，蓝) — 先于空头判定
  if (roleLower.includes('conservative') || rawRole.includes('保守')) {
    return { name: rawRole, className: 'role-conservative', icon: '🛡️', alignment: 'right' }
  }

  // 多头/进攻/研究员/战略/乐观/Scout (左侧，绿色)
  if (roleLower.includes('bull') || rawRole.includes('多头') || rawRole.includes('研究员')
      || rawRole.includes('战略配置') || rawRole.includes('乐观')
      || roleLower.includes('scout') || rawRole.includes('候选')) {
    return { name: rawRole, className: 'role-bull', icon: '🐂', alignment: 'left' }
  }

  // 空头/反向者/防御/悲观 (右侧，红色)
  if (roleLower.includes('bear') || rawRole.includes('空头') || rawRole.includes('反向者')
      || rawRole.includes('防御配置') || rawRole.includes('悲观')) {
    return { name: rawRole, className: 'role-bear', icon: '🐻', alignment: 'right' }
  }

  // 中性 (左侧，灰色)
  if (roleLower.includes('neutral') || rawRole.includes('中性')) {
    return { name: rawRole, className: 'role-neutral', icon: '⚖️', alignment: 'left' }
  }

  // 管理者/裁判/宏观/合成器/诊断/大类 (居中，紫色)
  if (roleLower.includes('manager') || roleLower.includes('trader') || roleLower.includes('synthesizer')
      || rawRole.includes('裁判') || rawRole.includes('宏观') || rawRole.includes('合成器')
      || rawRole.includes('诊断') || rawRole.includes('大类')) {
    return { name: rawRole, className: 'role-manager', icon: '👨‍⚖️', alignment: 'center' }
  }

  // 默认 (左侧，蓝色)
  return { name: rawRole, className: 'role-default', icon: '👤', alignment: 'left' }
}

// 格式化 Markdown
function formatMarkdown(text: string) {
  try {
    return marked.parse(text)
  } catch (e) {
    return `<pre style="white-space: pre-wrap; font-family: inherit;">${text}</pre>`
  }
}
</script>

<style lang="scss" scoped>
.debate-timeline {
  padding: 10px 0;
}

.chat-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-bubble-wrapper {
  display: flex;
  gap: 16px;
  max-width: 90%;

  &.left {
    align-self: flex-start;
  }

  &.right {
    align-self: flex-end;
    justify-content: flex-end;
  }

  &.center {
    align-self: center;
    max-width: 95%;
  }
}

.avatar-col {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);

  &.role-bull { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
  &.role-bear { background: linear-gradient(135deg, #ef4444 0%, #be123c 100%); }
  &.role-aggressive { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
  &.role-conservative { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }
  &.role-neutral { background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); }
  &.role-manager { background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); }
  &.role-default { background: linear-gradient(135deg, #94a3b8 0%, #475569 100%); }
}

.bubble-content-col {
  display: flex;
  flex-direction: column;
  min-width: 200px;
}

.chat-bubble-wrapper.right .bubble-content-col {
  align-items: flex-end;
}

.chat-bubble-wrapper.center .bubble-content-col {
  align-items: center;
}

.bubble-meta {
  margin-bottom: 6px;
  padding: 0 4px;
}

.bubble-name {
  font-size: 14px;
  font-weight: 600;
  color: #4b5563;
}

.bubble-body {
  padding: 16px 20px;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  background: white;
  border: 1px solid #e5e7eb;

  .chat-bubble-wrapper.left & {
    border-top-left-radius: 4px;
  }

  .chat-bubble-wrapper.right & {
    border-top-right-radius: 4px;
  }

  /* 根据角色微调边框颜色 */
  &.role-bull { border-left: 4px solid #10b981; }
  &.role-bear { border-right: 4px solid #ef4444; }
  &.role-aggressive { border-left: 4px solid #f59e0b; }
  &.role-conservative { border-right: 4px solid #3b82f6; }
  &.role-neutral { border-left: 4px solid #6b7280; }
  &.role-manager { border: 2px solid #8b5cf6; }
}

/* 覆盖 report-content 的默认样式以适应气泡 */
:deep(.report-content) {
  h1, h2, h3, h4 {
    margin-top: 0 !important;
  }

  p:last-child {
    margin-bottom: 0 !important;
  }

  font-size: 15px !important;
}

.fallback-view {
  background: var(--el-fill-color-light);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color);
}

/* 数据凭据条 */
.evidence-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 0 4px;
}

.evidence-label {
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  margin-right: 2px;
}

.evidence-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 1.4;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: default;

  .ev-icon {
    font-weight: 700;
  }

  &.ev-verified {
    background: #ecfdf5;
    color: #047857;
    border-color: #a7f3d0;
  }

  &.ev-estimated {
    background: #fffbeb;
    color: #b45309;
    border-color: #fde68a;
  }

  &.ev-missing {
    background: #fef2f2;
    color: #b91c1c;
    border-color: #fecaca;
    text-decoration: line-through;
    text-decoration-color: rgba(185, 28, 28, 0.4);
  }
}
</style>
