<template>
  <!-- 递归渲染任意 JSON 值：保证「完全展示」零字段丢失 -->
  <div class="jt">
    <!-- 原始值 -->
    <span v-if="isPrimitive" class="jt-val" :class="primClass">{{ displayPrim }}</span>

    <!-- 数组 -->
    <ul v-else-if="isArray" class="jt-list">
      <li v-for="(item, i) in (value as any[])" :key="i" class="jt-li">
        <span class="jt-idx">[{{ i }}]</span>
        <JsonTree :value="item" :depth="depth + 1" />
      </li>
    </ul>

    <!-- 对象 -->
    <div v-else-if="isObject" class="jt-obj">
      <div v-for="(v, k) in (value as Record<string, any>)" :key="k" class="jt-kv">
        <span class="jt-key">{{ k }}</span>
        <JsonTree :value="v" :depth="depth + 1" />
      </div>
    </div>

    <span v-else class="jt-null">—</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ value: any; depth?: number }>(), { depth: 0 })

const isPrimitive = computed(() =>
  props.value == null || ['string', 'number', 'boolean'].includes(typeof props.value)
)
const isArray = computed(() => Array.isArray(props.value))
const isObject = computed(() => !isArray.value && props.value != null && typeof props.value === 'object')

const displayPrim = computed(() => {
  if (props.value == null) return '—'
  if (typeof props.value === 'boolean') return props.value ? '是' : '否'
  return String(props.value)
})
const primClass = computed(() => {
  if (typeof props.value === 'number') return 'jt-num'
  if (typeof props.value === 'boolean') return 'jt-bool'
  return 'jt-str'
})
</script>

<style scoped>
.jt { display: inline; }
.jt-list { list-style: none; padding-left: 14px; margin: 2px 0; border-left: 1px dashed #e4e7ed; }
.jt-li { font-size: 12.5px; line-height: 1.7; padding: 1px 0; }
.jt-idx { color: #c0c4cc; font-size: 11px; margin-right: 6px; }
.jt-obj { padding-left: 14px; border-left: 1px dashed #e4e7ed; margin: 2px 0; }
.jt-kv { font-size: 12.5px; line-height: 1.7; padding: 2px 0; display: flex; gap: 8px; align-items: baseline; }
.jt-key { font-weight: 600; color: #5b6dde; white-space: nowrap; flex-shrink: 0; }
.jt-val { color: #4e5969; word-break: break-word; }
.jt-num { color: #d46b08; font-weight: 600; }
.jt-bool { color: #722ed1; }
.jt-str { color: #4e5969; }
.jt-null { color: #c0c4cc; }
</style>
