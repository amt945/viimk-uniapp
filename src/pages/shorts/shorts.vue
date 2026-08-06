<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <text class="header-title">短剧</text>
      <view class="icon-btn" @tap="goSearch">
        <VmkIcon name="search" :size="40" color="#FFFFFF" />
      </view>
    </view>

    <!-- 分类 chips：点击切换分类，重置列表并加载第 1 页 -->
    <scroll-view class="chips-scroll" scroll-x :show-scrollbar="false">
      <view class="chips-row">
        <view
          v-for="(c, i) in cats"
          :key="c"
          class="chip"
          :class="{ active: cat === i }"
          @tap="selectCategory(i)"
        >
          <text class="chip-text">{{ c }}</text>
        </view>
      </view>
    </scroll-view>

    <!-- 列表：scroll-view 高度 hack + 触底加载 -->
    <!-- :key=cat 切换分类时重建 scroll-view，避免 @scrolltolower 偶发不触发 -->
    <scroll-view
      ref="shortsScrollView"
      :key="'shorts-scroll-' + cat"
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
            <view v-for="i in 6" :key="i" class="thumb-card">
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
          <!-- 列表底部状态：加载中 / 没有更多 -->
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

    <BottomNav current="shorts" />
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import BottomNav from '@/components/BottomNav.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchShortsTabs, fetchShortsListPaged, navigateToPlayer } from '@/api/index.js'

export default {
  name: 'Shorts',
  components: { StatusBar, BottomNav, VmkIcon },
  data() {
    return {
      cats: [],
      cat: 0,
      loading: true,         // 首屏骨架屏
      list: [],
      page: 1,
      hasMore: true,
      listLoading: false,     // 触底加载中
      initialized: false,     // 首屏是否已加载
      _autoLoadCount: 0       // 自动补载安全锁
    }
  },
  async onShow() {
    if (this.cats.length === 0) {
      this.cats = await fetchShortsTabs()
    }
    await this.loadList(true)
  },
  methods: {
    // reset=true 表示切换分类/首次加载，重置列表；false 表示加载下一页
    async loadList(reset = false) {
      if (this.listLoading) return
      if (!reset && !this.hasMore) return
      this.listLoading = true
      if (reset) {
        this.page = 1
        this.hasMore = true
        this.list = []
        this._autoLoadCount = 0
      }
      const catName = this.cats[this.cat] || '推荐'
      const targetPg = this.page
      console.log('[shorts] loadList: cat=' + catName + ', pg=' + targetPg + ', reset=' + reset)
      const res = await fetchShortsListPaged(catName, targetPg)
      if (res && Array.isArray(res.list)) {
        if (res.list.length) {
          this.list = reset ? res.list : this.list.concat(res.list)
          // ffzy 每页 20 条，不满 20 条就是末页
          this.hasMore = res.list.length >= 20 ? !!res.hasMore : false
          if (this.hasMore) {
            this.page = (res.page || targetPg) + 1
          }
          console.log('[shorts] loadList ok: count=' + res.list.length + ', hasMore=' + this.hasMore + ', nextPg=' + this.page)
        } else if (reset) {
          this.list = []
          this.hasMore = false
        } else {
          this.hasMore = false
        }
      } else {
        // 请求失败：保留 hasMore 不变，下次重试同一页
        console.warn('[shorts] loadList FAIL: 请求失败，保留状态，下次重试 pg=' + targetPg)
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
    // 切换分类
    async selectCategory(i) {
      if (i === this.cat) return
      console.log('[shorts] selectCategory: ' + this.cats[i])
      this.cat = i
      this.loading = true
      await this.loadList(true)
    },
    // scroll-view 触底：加载下一页
    onScrollToLower() {
      console.log('[shorts] ★ scrolltolower! hasMore=' + this.hasMore + ', listLoading=' + this.listLoading)
      if (this.listLoading || !this.hasMore || !this.initialized) return
      this.loadList(false)
    },
    /**
     * 首屏内容不足时自动补载，确保出现滚动条（参考首页/片库实现）
     * 安全锁：最多自动补载 3 次
     */
    _ensureScrollable() {
      if (this._autoLoadCount >= 3) return
      if (!this.$el || !this.$el.querySelector) return
      let sv = this.$el.querySelector('.page-content .uni-scroll-view-scrollbar-hidden')
      if (!sv) {
        const outer = this.$el.querySelector('.page-content > div')
        sv = outer && outer.querySelector(':scope > div') ? outer.querySelector(':scope > div') : null
      }
      if (!sv) sv = this.$el.querySelector('.page-content .uni-scroll-view')
      if (!sv) sv = this.$refs.shortsScrollView && this.$refs.shortsScrollView.$el ? this.$refs.shortsScrollView.$el : null
      if (!sv) sv = this.$el.querySelector('.page-content')
      if (!sv) return
      const sh = sv.scrollHeight || 0
      const ch = sv.clientHeight || 0
      const canScroll = sh > ch + 10
      console.log('[shorts] ensureScrollable: autoLoad=' + this._autoLoadCount + '/3, sh=' + sh + ', ch=' + ch + ', canScroll=' + canScroll + ', hasMore=' + this.hasMore + ', len=' + this.list.length)
      if (!canScroll && this.hasMore && !this.listLoading && this.list.length > 0) {
        this._autoLoadCount++
        this.loadList(false).then(() => {
          this.$nextTick(() => {
            setTimeout(() => this._ensureScrollable(), 50)
          })
        })
      }
    },
    async goDetail(itemOrId) {
      if (!itemOrId) return
      try {
        uni.showLoading({ title: '加载中…', mask: true })
        await navigateToPlayer(itemOrId, null, 'shorts')
      } finally {
        uni.hideLoading()
      }
    },
    goSearch() {
      uni.navigateTo({ url: '/pages/search/search' })
    }
  }
}
</script>

<style scoped>
.app-shell {
  /* 固定视口高度，和首页/片库一样的高度模型 */
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
  height: 112rpx;
  padding: 0 32rpx;
  flex-shrink: 0;
}
.header-title {
  font-size: var(--vmk-text-xl);
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

/* Chips */
.chips-scroll {
  width: 100%;
  white-space: nowrap;
  margin-bottom: 16rpx;
  flex-shrink: 0;
}
.chips-row {
  display: flex;
  gap: 16rpx;
  padding: 0 32rpx;
}
.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 64rpx;
  padding: 0 32rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  flex-shrink: 0;
}
.chip.active {
  background-color: var(--vmk-primary);
  border-color: var(--vmk-primary);
}
.chip-text {
  font-size: var(--vmk-text-base);
  color: var(--vmk-foreground);
  white-space: nowrap;
}

/* scroll-view 高度 hack：flex:1 + height:0 + min-height:0 */
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

/* Grid（短剧 2 列竖版海报） */
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.thumb-card {
  width: calc((100% - 24rpx) / 2);
  display: flex;
  flex-direction: column;
}
.thumb-img {
  position: relative;
  width: 100%;
  aspect-ratio: 10 / 16;
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
  top: 16rpx;
  left: 16rpx;
  padding: 4rpx 12rpx;
  border-radius: var(--vmk-radius-sm);
  background-color: var(--vmk-warning);
}
.rating-text {
  font-size: 20rpx;
  font-weight: 700;
  color: var(--vmk-foreground);
}
.thumb-title {
  margin-top: 16rpx;
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.3;
  color: var(--vmk-foreground);
}
.thumb-meta {
  margin-top: 8rpx;
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
  aspect-ratio: 10 / 16;
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
