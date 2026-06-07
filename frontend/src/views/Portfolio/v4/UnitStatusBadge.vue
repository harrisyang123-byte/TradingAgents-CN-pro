<template>
  <span class="unit-status-badge">
    <el-tooltip
      :disabled="!tooltipContent"
      placement="top"
      :show-after="200"
      effect="dark"
    >
      <template #content>
        <div class="usb-tooltip">
          <div v-if="staleReason" class="usb-stale">⚠ {{ staleReason }}</div>
          <div v-if="cliHint" class="usb-hint">
            <div class="usb-hint-title">在 CLI 中触发（前端不直接调起分析）：</div>
            <code>{{ cliHint }}</code>
          </div>
          <div v-if="meta?.generated_at" class="usb-meta">
            更新于 {{ formatTime(meta.generated_at) }}
            <span v-if="meta?.version != null"> · v{{ meta.version }}</span>
          </div>
        </div>
      </template>
      <span
        class="usb-dot"
        :style="{ color: style.color, background: style.bg }"
        :class="{ 'usb-spin': status === 'blue' }"
      >
        <span class="usb-icon">{{ style.icon }}</span>
        <span class="usb-label">{{ style.label }}</span>
        <span v-if="staleReason" class="usb-warn-mark">!</span>
      </span>
    </el-tooltip>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { statusStyle } from './assetClasses'
import type { UnitMeta } from '@/api/portfolioV4'

const props = defineProps<{
  status: string
  staleReason?: string | null
  cliHint?: string
  meta?: UnitMeta | null
}>()

const style = computed(() => statusStyle(props.status))
const tooltipContent = computed(
  () => !!(props.staleReason || props.cliHint || props.meta?.generated_at),
)

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}
</script>

<style scoped>
.unit-status-badge {
  display: inline-flex;
  align-items: center;
}
.usb-dot {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 18px;
  font-weight: 500;
  white-space: nowrap;
}
.usb-icon {
  font-size: 11px;
}
.usb-spin .usb-icon {
  animation: usb-rotate 1.2s linear infinite;
}
.usb-warn-mark {
  display: inline-block;
  width: 13px;
  height: 13px;
  line-height: 13px;
  text-align: center;
  border-radius: 50%;
  background: #e6a23c;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}
@keyframes usb-rotate {
  to {
    transform: rotate(360deg);
  }
}
.usb-tooltip {
  max-width: 320px;
  line-height: 1.5;
}
.usb-stale {
  color: #ffd666;
  margin-bottom: 6px;
}
.usb-hint-title {
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 2px;
}
.usb-hint code {
  display: block;
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}
.usb-meta {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.7;
}
</style>
