/**
 * 页面数据缓存 composable
 *
 * 在内存中缓存 API 返回的数据，TTL 内回访同一页面时跳过网络请求。
 * Ctrl+R / 关闭标签页会清空内存缓存，不影响首次加载行为。
 */

import { ref } from 'vue'

interface CacheEntry<T> {
  data: T
  expiry: number
}

// 模块级 Map，跨组件实例共享（切换页面不走 SSR，内存常驻）
const store = new Map<string, CacheEntry<any>>()

export function usePageCache() {
  const isLoading = ref(false)

  /**
   * 加载数据：ttl 内有缓存则直接返回，否则调用 fetcher
   *
   * @param key      缓存键，建议用页面名（如 'overview', 'holdings'）
   * @param fetcher  实际发起 API 请求的异步函数
   * @param ttlMs    缓存有效期（毫秒），默认 30 秒
   * @returns fetcher 的返回值
   */
  async function loadWithCache<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttlMs = 30_000
  ): Promise<T> {
    const cached = store.get(key)
    if (cached && Date.now() < cached.expiry) {
      return cached.data
    }

    isLoading.value = true
    try {
      const data = await fetcher()
      store.set(key, { data, expiry: Date.now() + ttlMs })
      return data
    } finally {
      isLoading.value = false
    }
  }

  /** 强制刷新（绕过缓存） */
  async function forceRefresh<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttlMs = 30_000
  ): Promise<T> {
    store.delete(key)
    return loadWithCache(key, fetcher, ttlMs)
  }

  /** 清除指定 key 的缓存 */
  function invalidate(key: string) {
    store.delete(key)
  }

  return { loadWithCache, forceRefresh, invalidate, isLoading }
}
