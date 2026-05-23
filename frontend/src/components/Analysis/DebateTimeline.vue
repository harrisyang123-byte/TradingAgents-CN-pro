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
const parsedBubbles = computed(() => {
  const historyStr = rawHistory.value
  if (!historyStr) return []

  // 尝试匹配常见的分析师发言开头格式
  // 例如： "Bull Analyst: xxx" 或 "**Bear Analyst:** xxx"
  const regex = /(?:^|\n)(?:\*\*)?(Bull Analyst|Bear Analyst|Aggressive Analyst|Conservative Analyst|Neutral Analyst|Manager Analyst|Fund Trader|Trader|裁判|多头分析师|空头分析师|激进分析师|保守分析师|中性分析师|分析师|Manager)(?:\*\*)?\s*[:：]\s*([\s\S]*?)(?=(?:\n(?:\*\*)?(?:Bull Analyst|Bear Analyst|Aggressive Analyst|Conservative Analyst|Neutral Analyst|Manager Analyst|Fund Trader|Trader|裁判|多头分析师|空头分析师|激进分析师|保守分析师|中性分析师|分析师|Manager)(?:\*\*)?\s*[:：]|$))/gi

  const bubbles = []
  let match

  while ((match = regex.exec(historyStr)) !== null) {
    const rawRole = match[1].trim()
    const content = match[2].trim()

    // 解析角色特征
    const roleFeature = getRoleFeature(rawRole)

    bubbles.push({
      roleName: roleFeature.name,
      roleClass: roleFeature.className,
      icon: roleFeature.icon,
      alignment: roleFeature.alignment,
      content: content
    })
  }

  return bubbles
})

// 根据角色名称获取特征
function getRoleFeature(rawRole: string) {
  const roleLower = rawRole.toLowerCase()

  // 多头特征 (左侧，绿色)
  if (roleLower.includes('bull') || roleLower.includes('多头')) {
    return {
      name: rawRole,
      className: 'role-bull',
      icon: '🐂',
      alignment: 'left'
    }
  }

  // 空头特征 (右侧，红色)
  if (roleLower.includes('bear') || roleLower.includes('空头')) {
    return {
      name: rawRole,
      className: 'role-bear',
      icon: '🐻',
      alignment: 'right'
    }
  }

  // 激进特征 (左侧，橙红)
  if (roleLower.includes('aggressive') || roleLower.includes('激进')) {
    return {
      name: rawRole,
      className: 'role-aggressive',
      icon: '⚡',
      alignment: 'left'
    }
  }

  // 保守特征 (右侧，蓝绿)
  if (roleLower.includes('conservative') || roleLower.includes('保守')) {
    return {
      name: rawRole,
      className: 'role-conservative',
      icon: '🛡️',
      alignment: 'right'
    }
  }

  // 中性特征 (居中偏左，灰色)
  if (roleLower.includes('neutral') || roleLower.includes('中性')) {
    return {
      name: rawRole,
      className: 'role-neutral',
      icon: '⚖️',
      alignment: 'left'
    }
  }

  // 管理者/裁判 (居中，紫色)
  if (roleLower.includes('manager') || roleLower.includes('裁判') || roleLower.includes('trader')) {
    return {
      name: rawRole,
      className: 'role-manager',
      icon: '👨‍⚖️',
      alignment: 'center'
    }
  }

  // 默认 (左侧，蓝色)
  return {
    name: rawRole,
    className: 'role-default',
    icon: '👤',
    alignment: 'left'
  }
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
</style>
