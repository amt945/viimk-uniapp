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

    <!-- 列表：scroll-view 高度 hack + 触底加载 -->
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
          <view class="grid">
            <view
              v-for="item in list"
              :key="item.id"
              class="thumb-card"
              @tap="goDetail(item)"
            >
              <view class="thumb-img">
                <image class="thumb-img-inner" :src="item.cover" mode="aspectFill" />
                <view class="rating-badge">
                  <text class="rating-text">{{ item.rating || item.score || '0.0' }}</text>
                </view>
              </view>
              <text class="thumb-title ellipsis">{{ item.title }}</text>
              <text class="thumb-meta ellipsis">{{ item.meta || (item.year + ' · ' + (item.area || '')) }}</text>
            </view>
          </view>
          <!-- 列表底部状态 -->
          <view class="list-footer">
            <view v-if="listLoading" class="list-footer-loading">
              <view class="mini-spinner"></view>
              <text class="list-footer-text">加载中…</text>
            </view>
            <text v-else-if="!hasMore && list.length" class="list-footer-text">没有更多了</text>
            <text v-else-if="!list.length && !listLoading" class="list-footer-text">暂无数据</text>
          </view>
        </template>

        <view class="bottom-spacer"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchActionListPaged, navigateToPlayer } from '@/api/index.js'

export default {
  name: 'Action',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      loading: true,
      list: [],
      page: 1,
      hasMore: true,
      listLoading: false,
      initialized: false,
      _autoLoadCount: 0
    }
  },
  async onShow() {
    if (!this.initialized) {
      // 尝试从缓存恢复
      if (this._restoreFromStorage()) {
        this.initialized = true
        this.loading = false
        this.loadList(true, true)
        return
      }
      await this.loadList(true)
    } else {
      await this.loadList(true, true)
    }
  },
  methods: {
    _restoreFromStorage() {
      try {
        const raw = uni.getStorageSync('vmk_action_cache')
        if (!raw) return false
        const cache = typeof raw === 'string' ? JSON.parse(raw) : raw
        if (!cache || !cache.list || !cache.list.length) return false
        if (cache.t && (Date.now() - cache.t) > 2 * 60 * 60 * 1000) return false
        this.list = cache.list
        this.page = 2
        this.hasMore = cache.hasMore !== false
        return true
      } catch (e) {
        return false
      }
    },
    _saveToStorage() {
      try {
        uni.setStorageSync('vmk_action_cache', {
          list: this.list,
          hasMore: this.hasMore,
          t: Date.now()
        })
      } catch (e) {}
    },
    async loadList(reset = false, silent = false) {
      if (this.listLoading) return
      if (!reset && !this.hasMore) return
      this.listLoading = true
      if (reset) {
        this.page = 1
        this.hasMore = true
        if (!silent) this.list = []
        this._autoLoadCount = 0
      }
      const targetPg = this.page
      const res = await fetchActionListPaged(targetPg)
      if (res && Array.isArray(res.list)) {
        if (res.list.length) {
          this.list = reset ? res.list : this.list.concat(res.list)
          this.hasMore = res.list.length >= 20 ? !!res.hasMore : false
          if (this.hasMore) {
            this.page = (res.page || targetPg) + 1
          }
          if (reset) this._saveToStorage()
        } else if (reset) {
          if (!silent) this.list = []
          this.hasMore = false
        } else {
          this.hasMore = false
        }
      }
      this.listLoading = false
      this.initialized = true
      if (reset) {
        this.loading = false
        this.$nextTick(() => {
          setTimeout(() => this._ensureScrollable(), 50)
        })
      }
    },
    onScrollToLower() {
      if (this.listLoading || !this.hasMore || !this.initialized) return
      this.loadList(false)
    },
    _ensureScrollable() {
      if (this._autoLoadCount >= 3) return
      if (!this.$el || !this.$el.querySelector) return
      let sv = this.$el.querySelector('.page-content .uni-scroll-view-scrollbar-hidden')
      if (!sv) {
        const outer = this.$el.querySelector('.page-content > div')
        sv = outer && outer.querySelector(':scope > div') ? outer.querySelector(':scope > div') : null
      }
      if (!sv) sv = this.$el.querySelector('.page-content .uni-scroll-view')
      if (!sv) sv = this.$refs.actScrollView && this.$refs.actScrollView.$el ? this.$refs.actScrollView.$el : null
      if (!sv) sv = this.$el.querySelector('.page-content')
      if (!sv) return
      const sh = sv.scrollHeight || 0
      const ch = sv.clientHeight || 0
      const canScroll = sh > ch + 10
      if (!canScroll && this.hasMore && !this.listLoading && this.list.length > 0) {
        this._autoLoadCount++
        this.loadList(false).then(() => {
          this.$nextTick(() => {
            setTimeout(() => this._ensureScrollable(), 50)
          })
        })
      }
    },
    goDetail(itemOrId) {
      if (!itemOrId) return
      navigateToPlayer(itemOrId)
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

/* scroll-view 高度 hack */
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
.rating-badge {
  position: absolute;
  top: 12rpx;
  left: 12rpx;
  padding: 2rpx 10rpx;
  border-radius: var(--vmk-radius-sm);
  background-color: var(--vmk-warning);
}
.rating-text {
  font-size: 20rpx;
  font-weight: 700;
  color: var(--vmk-foreground);
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

/* 列表底部加载状态 */
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

/* 骨架屏 */
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
</style>
