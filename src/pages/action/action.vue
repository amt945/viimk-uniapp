<template>
  <view class="app-shell">
    <StatusBar />
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">动作片</text>
      <view class="icon-btn"></view>
    </view>

    <scroll-view
      ref="actScrollView"
      class="page-content"
      scroll-y
      :show-scrollbar="false"
      :lower-threshold="150"
      @scrolltolower="onScrollToLower"
    >
      <view class="page-padding-wrapper">
        <!-- 骨架屏 -->
        <template v-if="loading">
          <view class="grid">
            <view v-for="i in 9" :key="i" class="thumb-card">
              <view class="skeleton thumb-skeleton"></view>
              <view class="skeleton text-skeleton"></view>
              <view class="skeleton text-skeleton short"></view>
            </view>
          </view>
        </template>

        <template v-else>
          <!-- 错误态：接口拉取失败且无缓存 -->
          <view v-if="errMsg && !list.length" class="error-state">
            <VmkIcon name="play" :size="64" color="#3A3A45" />
            <text class="error-text">{{ errMsg }}</text>
            <view class="retry-btn" @tap="loadList(true)">
              <text class="retry-text">重试</text>
            </view>
          </view>

          <template v-else>
            <view class="grid">
              <view
                v-for="item in list"
                :key="item.id"
                class="thumb-card"
                @tap="goDetail(item)"
              >
                <view class="thumb-img">
                  <image
                    v-if="item.cover"
                    class="thumb-img-inner"
                    :src="item.cover"
                    mode="aspectFill"
                    @error="onCoverError(item)"
                  />
                  <view v-else class="thumb-img-placeholder">
                    <VmkIcon name="play" :size="36" color="#6B7280" />
                  </view>
                  <view class="type-badge">
                    <text class="type-text">{{ item.videoType || 'MP4' }}</text>
                  </view>
                </view>
                <text class="thumb-title ellipsis">{{ item.title }}</text>
                <text class="thumb-meta ellipsis">{{ item.site || '动作片' }}</text>
              </view>
            </view>
            <view class="list-footer">
              <view v-if="listLoading" class="list-footer-loading">
                <view class="mini-spinner"></view>
                <text class="list-footer-text">加载中…</text>
              </view>
              <text v-else-if="!hasMore && list.length" class="list-footer-text">没有更多了</text>
              <text v-else-if="!list.length && !listLoading" class="list-footer-text">暂无数据</text>
            </view>
          </template>
        </template>

        <view class="bottom-spacer"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchActionList } from '@/api/index.js'

export default {
  name: 'Action',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      loading: true,
      list: [],
      page: 1,
      pagecount: 1,
      hasMore: false,
      listLoading: false,
      initialized: false,
      errMsg: ''
    }
  },
  async onShow() {
    if (!this.initialized) {
      if (this._restoreFromStorage()) {
        this.initialized = true
        this.loading = false
        this.loadList(true)
        return
      }
      await this.loadList(true)
    } else {
      await this.loadList(true)
    }
  },
  methods: {
    // 兼容 storage：优先 localStorage（WebView 原生），兜底 uni.storage
    _cacheGet() {
      // 兼容 storage：优先 localStorage（WebView 原生），兜底 uni.storage
      // 注意 uni.setStorageSync 在 H5 下会包装为 {type,data} 格式存入 localStorage，
      // 直接 JSON.parse(localStorage) 会得到包装对象，需取 .data。
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          const raw = window.localStorage.getItem('vmk_action_cache')
          if (raw != null) {
            const parsed = JSON.parse(raw)
            // uni.storage 包装格式 {type:"object", data:{...}}
            if (parsed && parsed.type === 'object' && parsed.data) return parsed.data
            return parsed
          }
        }
      } catch (e) {}
      try {
        if (typeof uni !== 'undefined' && uni.getStorageSync) {
          const v = uni.getStorageSync('vmk_action_cache')
          if (v) return typeof v === 'string' ? JSON.parse(v) : v
        }
      } catch (e) {}
      return null
    },
    _cacheSet(data) {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.setItem('vmk_action_cache', JSON.stringify(data))
        }
      } catch (e) {}
      try { if (typeof uni !== 'undefined' && uni.setStorageSync) uni.setStorageSync('vmk_action_cache', data) } catch (e) {}
    },
    _clearStorage() {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.removeItem('vmk_action_cache')
        }
      } catch (e) {}
      try { if (typeof uni !== 'undefined' && uni.removeStorageSync) uni.removeStorageSync('vmk_action_cache') } catch (e) {}
    },
    _restoreFromStorage() {
      const cache = this._cacheGet()
      if (!cache || !cache.list || !cache.list.length) return false
      // 缓存超过 6 小时视为过期
      if (cache.t && (Date.now() - cache.t) > 6 * 60 * 60 * 1000) return false
      // 旧版缓存可能是片库数据（id=online:xxx, 无 url），不是爬虫数据，丢弃
      const first = cache.list[0]
      if (first && (first.id || '').indexOf('online:') === 0) return false
      this.list = cache.list
      this.page = cache.page || 1
      this.pagecount = cache.pagecount || 1
      // 恢复 hasMore：缓存可能不完整，保守设为 true 让触底能继续尝试
      // 若已是最后一页则后端返回空列表 + hasMore=false，前端自然停止
      this.hasMore = this.page < this.pagecount
      return true
    },
    _saveToStorage() {
      this._cacheSet({ list: this.list, page: this.page, pagecount: this.pagecount, t: Date.now() })
    },
    async loadList(reset = false) {
      if (this.listLoading) return
      // 触底追加时，没有下一页则不请求
      if (!reset && !this.hasMore) return
      this.listLoading = true
      this.errMsg = ''
      const pg = reset ? 1 : this.page + 1
      const res = await fetchActionList(pg)
      if (res && Array.isArray(res.list)) {
        if (reset) {
          this.list = res.list
        } else {
          // 追加：按 id 去重，避免边界重复
          const ids = new Set(this.list.map(i => i.id))
          this.list = this.list.concat(res.list.filter(i => !ids.has(i.id)))
        }
        this.page = res.page || pg
        this.pagecount = res.pagecount || 1
        this.hasMore = res.hasMore
        this._saveToStorage()
      } else if (reset && !this.list.length) {
        // 首屏无缓存且拉取失败 → 显示错误态
        this.errMsg = '数据加载失败，请检查网络后重试'
      }
      this.listLoading = false
      this.initialized = true
      if (reset) {
        this.loading = false
      }
    },
    onScrollToLower() {
      // 触底加载下一页
      if (this.hasMore && !this.listLoading) {
        this.loadList(false)
      }
    },
    onCoverError(item) {
      // 封面加载失败 (如加密图片无法解密) → 清空 cover 触发占位符显示
      if (item && item.cover) {
        item.cover = ''
        if (item.coverUrl) item.coverUrl = ''
      }
    },
    goDetail(item) {
      if (!item || !item.url) {
        uni.showToast({ title: '暂无可播放地址', icon: 'none' })
        return
      }
      // 直接带 url 跳播放页，播放器会自动检测视频方向切换布局
      const params = [
        'url=' + encodeURIComponent(item.url),
        'title=' + encodeURIComponent(item.title || ''),
        'contentType=action'
      ]
      if (item.cover) params.push('poster=' + encodeURIComponent(item.cover))
      uni.navigateTo({ url: '/pages/player/player?' + params.join('&') })
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/about/about' })
    }
  }
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
  background-color: var(--vmk-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 24rpx;
  flex-shrink: 0;
}
.header-title {
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
}
.icon-btn {
  width: 80rpx;
  height: 80rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.page-content {
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  display: block;
  box-sizing: border-box;
}
.page-padding-wrapper {
  padding: 16rpx 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.thumb-card {
  width: calc((100% - 48rpx) / 3);
  display: flex;
  flex-direction: column;
}
.thumb-img {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-md);
  overflow: hidden;
  background-color: var(--vmk-card);
}
.thumb-img-inner {
  width: 100%;
  height: 100%;
}
.thumb-img-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--vmk-muted-bg);
}
.type-badge {
  position: absolute;
  top: 12rpx;
  right: 12rpx;
  padding: 2rpx 10rpx;
  border-radius: var(--vmk-radius-sm);
  background-color: rgba(0, 0, 0, 0.6);
}
.type-text {
  font-size: 20rpx;
  font-weight: 600;
  color: #FFFFFF;
  text-transform: uppercase;
}
.thumb-title {
  margin-top: 12rpx;
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1.3;
  color: var(--vmk-foreground);
}
.thumb-meta {
  margin-top: 6rpx;
  font-size: var(--vmk-text-xs);
  line-height: 1.4;
  color: var(--vmk-muted);
}
.bottom-spacer {
  height: 32rpx;
}

.list-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 32rpx 0 8rpx;
}
.list-footer-loading {
  display: inline-flex;
  align-items: center;
  gap: 12rpx;
}
.mini-spinner {
  width: 28rpx;
  height: 28rpx;
  border: 3rpx solid var(--vmk-muted-bg);
  border-top-color: var(--vmk-primary);
  border-radius: 50%;
  animation: mini-spin 0.8s linear infinite;
}
@keyframes mini-spin {
  100% { transform: rotate(360deg); }
}
.list-footer-text {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.skeleton {
  position: relative;
  background-color: var(--vmk-card);
  overflow: hidden;
  border-radius: var(--vmk-radius-md);
}
.skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.08) 50%, transparent 100%);
  animation: skel-shimmer 1.4s infinite;
}
@keyframes skel-shimmer {
  100% { transform: translateX(100%); }
}
.thumb-skeleton {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-md);
}
.text-skeleton {
  width: 100%;
  height: 28rpx;
  border-radius: 6rpx;
  margin-top: 12rpx;
}
.text-skeleton.short { width: 60%; }

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 40rpx;
  gap: 24rpx;
}
.error-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
  text-align: center;
  line-height: 1.5;
}
.retry-btn {
  padding: 16rpx 56rpx;
  border-radius: var(--vmk-radius-md);
  background-color: var(--vmk-primary);
}
.retry-text {
  font-size: var(--vmk-text-sm);
  font-weight: 600;
  color: #FFFFFF;
}
</style>
