<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <text class="brand">VIIMK</text>
      <view class="header-actions">
        <view class="icon-btn" @tap="goSearch">
          <VmkIcon name="search" :size="40" color="#FFFFFF" />
        </view>
        <view class="icon-btn" @tap="onCast">
          <VmkIcon name="cast" :size="40" color="#FFFFFF" />
        </view>
      </view>
    </view>

    <!-- Page content -->
    <!-- :key=activeCategory 切换分类时重建 scroll-view，避免 @scrolltolower 偶发不触发（uni-app H5 端已知问题） -->
    <scroll-view
      ref="homeScrollView"
      :key="'home-scroll-' + activeCategory"
      class="page-content"
      scroll-y
      :show-scrollbar="false"
      :lower-threshold="150"
      @scrolltolower="onScrollToLower"
    >
      <!-- padding wrapper：外层.page-content高度已被flex严格约束，
           padding必须放在内部wrapper层，否则box-sizing算到外层导致高度溢出 -->
      <view class="page-padding-wrapper">
      <!-- Skeleton：加载中显示骨架屏，避免白屏/跳动 -->
      <template v-if="loading">
        <view class="skeleton hero-skeleton"></view>
        <view class="chips-skeleton-row">
          <view v-for="i in 5" :key="i" class="skeleton chip-skeleton"></view>
        </view>
        <view class="section">
          <view class="skeleton section-title-skeleton"></view>
          <view class="hot-grid">
            <view v-for="i in 6" :key="i" class="hot-skeleton">
              <view class="skeleton poster-skeleton"></view>
              <view class="skeleton text-skeleton"></view>
              <view class="skeleton text-skeleton short"></view>
            </view>
          </view>
        </view>
      </template>

      <template v-else>
        <!-- Hero banner -->
        <view class="hero" @tap="goDetail(heroBanner)">
          <image class="hero-img" :src="heroBanner.cover" mode="aspectFill" />
          <view class="hero-overlay"></view>
          <view class="hero-tag">
            <text class="hero-tag-text">{{ heroBanner.tag }}</text>
          </view>
          <view class="hero-info">
            <text class="hero-title">{{ heroBanner.title }}</text>
            <view class="hero-meta">
              <text class="hero-meta-text">{{ heroBanner.year }}</text>
              <text class="hero-meta-dot">·</text>
              <text class="hero-meta-text">{{ heroBanner.genre }}</text>
              <text class="hero-meta-dot">·</text>
              <text class="hero-meta-text">{{ heroBanner.region }}</text>
            </view>
            <view class="hero-bottom">
              <view class="hero-score">
                <text class="hero-score-text">{{ heroBanner.score }}分</text>
              </view>
              <view class="play-btn" @tap.stop="goPlayer(heroBanner)">
                <VmkIcon name="play" :size="28" color="#FFFFFF" />
                <text class="play-btn-text">立即播放</text>
              </view>
            </view>
          </view>
        </view>

        <!-- Category chips -->
        <scroll-view class="chips-scroll" scroll-x :show-scrollbar="false">
          <view class="chips-row">
            <view
              v-for="(c, i) in homeCategories"
              :key="c"
              class="chip"
              :class="{ active: activeCategory === i }"
              @tap="selectCategory(i)"
            >
              <text class="chip-text">{{ c }}</text>
            </view>
          </view>
        </scroll-view>

        <!-- 热门推荐（无限滚动懒加载） -->
        <view class="section">
          <view class="section-head">
            <text class="section-title">热门推荐</text>
            <view class="more-btn" @tap="goLibrary">
              <text class="more-btn-text">更多</text>
              <VmkIcon name="chevron-right" :size="24" color="var(--vmk-muted)" />
            </view>
          </view>
          <view class="hot-grid">
            <view
              v-for="item in hotList"
              :key="item.id"
              class="hot-card"
              @tap="goDetail(item)"
            >
              <view class="hot-poster">
                <image class="hot-poster-img" :src="item.cover" mode="aspectFill" />
              </view>
              <text class="hot-title ellipsis">{{ item.title }}</text>
              <text class="hot-tag ellipsis">{{ item.remarks || item.tag }}</text>
            </view>
          </view>
          <!-- 列表底部状态：加载中 / 没有更多 -->
          <view class="list-footer">
            <view v-if="hotLoading" class="list-footer-loading">
              <view class="mini-spinner"></view>
              <text class="list-footer-text">加载中…</text>
            </view>
            <text v-else-if="!hotHasMore && hotList.length" class="list-footer-text">没有更多了</text>
            <text v-else-if="!hotList.length && !hotLoading" class="list-footer-text">暂无数据</text>
          </view>
        </view>
      </template>

      <view class="bottom-spacer"></view>
      </view><!-- /page-padding-wrapper -->
    </scroll-view>

    <BottomNav current="home" />
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import BottomNav from '@/components/BottomNav.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import {
  fetchHeroBanner,
  fetchHomeCategories,
  fetchHomeList,
  navigateToPlayer
} from '@/api/index.js'

export default {
  name: 'Home',
  components: { StatusBar, BottomNav, VmkIcon },
  data() {
    return {
      heroBanner: {},
      homeCategories: [],
      activeCategory: 0,
      loading: true,
      // 热门推荐无限滚动相关
      hotList: [],
      hotPage: 1,
      hotHasMore: true,
      hotLoading: false,
      hotInitialized: false,   // 首屏是否已加载过列表（避免 onShow 重复首次加载）
      _autoLoadCount: 0        // _ensureScrollable 自动补载的页数（安全锁，防死循环）
    }
  },
  async onShow() {
    // 首次加载：尝试从持久化缓存恢复（秒出，无骨架屏），再后台静默刷新
    if (!this.hotInitialized) {
      if (this._restoreFromStorage()) {
        this.hotInitialized = true
        this.loading = false
        // 后台静默刷新（不显示骨架屏、不闪烁）
        this.loadAll(false, true)
        return
      }
    }
    // 无缓存：首次显示骨架屏；后续返回不闪骨架屏，静默刷新
    await this.loadAll(!this.hotInitialized)
  },
  methods: {
    async loadAll(showLoading = true, silent = false) {
      if (showLoading) this.loading = true
      try {
        // 并行加载：hero/categories 和列表同时发起
        // 列表就绪后立即隐藏骨架屏，不等 hero
        const listPromise = this.loadHotList(true, silent)
        const headerPromise = Promise.all([
          fetchHeroBanner(),
          fetchHomeCategories()
        ]).then(([banner, cats]) => {
          this.heroBanner = banner
          this.homeCategories = cats
        })
        // 等列表就绪即可隐藏骨架屏
        await listPromise
        this.loading = false
        // hero/categories 在后台继续加载（不阻塞列表显示）
        headerPromise.catch(() => {})
        // 首屏数据就绪后持久化，下次冷启动秒开
        headerPromise.then(() => this._saveToStorage())
      } finally {
        this.loading = false
        this.$nextTick(() => {
          this._ensureScrollable()
        })
      }
    },
    // 从持久化缓存恢复首屏数据（秒开，跳过骨架屏）
    _restoreFromStorage() {
      try {
        const raw = uni.getStorageSync('vmk_home_cache')
        if (!raw) return false
        const cache = typeof raw === 'string' ? JSON.parse(raw) : raw
        if (!cache || !cache.list || !cache.list.length) return false
        // 超过 2 小时的缓存不再用于秒开（太旧就走正常加载）
        if (cache.t && (Date.now() - cache.t) > 2 * 60 * 60 * 1000) return false
        this.hotList = cache.list
        this.heroBanner = cache.banner || {}
        if (cache.cats && cache.cats.length) this.homeCategories = cache.cats
        this.hotPage = 2   // 已有第 1 页，下次触底加载第 2 页
        this.hotHasMore = cache.hasMore !== false
        return true
      } catch (e) {
        return false
      }
    },
    // 持久化首屏数据，下次冷启动秒开
    _saveToStorage() {
      try {
        uni.setStorageSync('vmk_home_cache', {
          list: this.hotList,
          banner: this.heroBanner,
          cats: this.homeCategories,
          hasMore: this.hotHasMore,
          t: Date.now()
        })
      } catch (e) {}
    },
    /**
     * 保证首页首屏 6 条（2 行）可能不足以撑出滚动条，用户无法滚动，
     * scrolltolower 也不会触发。
     *
     * 特别注意 uni-app H5 端 scroll-view 的 DOM 结构：
     *   <uni-scroll-view class="page-content">   <- 外层自定义元素
     *     <div class="uni-scroll-view">          <- 真正的滚动容器(有 overflow)
     *       <div>...</div>                        <- 内容容器
     *   所以要优先拿到 .uni-scroll-view，拿不到再回退到外层 .page-content。
     *
     * 安全机制：最多自动补载 3 页（18 条），避免 canScroll 判断不准导致死循环。
     * 18 条（6 行）+ Hero Banner + Chips + Section 一定超过视口高度。
     */
    _ensureScrollable() {
      // 安全锁：自动补载不超过 3 次
      if (this._autoLoadCount >= 3) {
        console.log('[home] ensureScrollable: 已自动补载 ' + this._autoLoadCount + ' 次，停止（防死循环）。listLen=' + this.hotList.length)
        return
      }
      if (!this.$el || !this.$el.querySelector) return

      // 1) H5 端 scroll-view 真实 DOM 结构（从外到内）：
      //    UNI-SCROLL-VIEW.page-content   <- 我们加的 class
      //      DIV.uni-scroll-view           <- 外层 wrapper(overflow:visible)
      //        DIV.uni-scroll-view.uni-scroll-view-scrollbar-hidden  <- 真正滚动容器(overflow:auto)
      //    所以优先找带 scrollbar-hidden 的孙子元素（这个才有 overflow:auto）
      let sv = this.$el.querySelector('.page-content .uni-scroll-view-scrollbar-hidden')
      if (!sv) {
        // 兜底：page-content 下的第二个 div（孙子层）
        const outer = this.$el.querySelector('.page-content > div')
        sv = outer && outer.querySelector(':scope > div') ? outer.querySelector(':scope > div') : null
      }
      if (!sv) sv = this.$el.querySelector('.page-content .uni-scroll-view')
      // 2) 最后回退：外层元素 / $refs
      if (!sv) sv = this.$refs.homeScrollView && this.$refs.homeScrollView.$el ? this.$refs.homeScrollView.$el : null
      if (!sv) sv = this.$el.querySelector('.page-content')
      if (!sv) return

      const sh = sv.scrollHeight || 0
      const ch = sv.clientHeight || 0
      // 兼容性策略：除了 scrollHeight > clientHeight，
      // 还尝试设置 scrollTop 看是否能滚动（部分浏览器/布局下 scrollHeight 可能 == clientHeight 但实际可滚）
      let canScroll = sh > ch + 10
      if (!canScroll && ch > 0) {
        try {
          const old = sv.scrollTop
          sv.scrollTop = 1
          canScroll = sv.scrollTop !== 0 || sh > ch
          sv.scrollTop = old
        } catch (e) { /* ignore */ }
      }
      console.log('[home] ensureScrollable: autoLoad=' + this._autoLoadCount + '/3, el=' + (sv.tagName||'?') + ' scrollH=' + sh + ' clientH=' + ch + ' canScroll=' + canScroll + ' hasMore=' + this.hotHasMore + ' listLen=' + this.hotList.length)
      if (!canScroll && this.hotHasMore && !this.hotLoading && this.hotList.length > 0) {
        this._autoLoadCount++
        console.log('[home] 没有滚动条，自动补载第 ' + this._autoLoadCount + ' 页...')
        this.loadHotList(false).then(() => {
          this.$nextTick(() => {
            setTimeout(() => this._ensureScrollable(), 50)
          })
        })
      }
    },
    // 加载热门推荐列表（首页无限滚动）
    // reset=true 表示切换分类/首次加载，重置列表；false 表示加载下一页
    // silent=true 表示静默刷新（不先清空列表，失败时保留已有数据，避免闪烁）
    async loadHotList(reset = false, silent = false) {
      if (this.hotLoading) {
        console.log('[home] loadHotList skip: loading=true')
        return
      }
      if (!reset && !this.hotHasMore) {
        console.log('[home] loadHotList skip: no more')
        return
      }
      this.hotLoading = true
      if (reset) {
        this.hotPage = 1
        this.hotHasMore = true
        // 静默刷新不先清空列表，等新数据到达后原子替换，避免闪烁
        if (!silent) this.hotList = []
        this._autoLoadCount = 0   // 重置自动补载计数（切分类/首屏后又可以自动补 3 页）
      }
      const cat = this.homeCategories[this.activeCategory] || '推荐'
      const targetPg = this.hotPage
      console.log('[home] loadHotList start: cat=' + cat + ', pg=' + targetPg + ', reset=' + reset + ', silent=' + silent)
      const res = await fetchHomeList(cat, targetPg)
      // —— 三种情况分别处理：成功有数据 / 成功但空 / 请求失败(res=null) ——
      if (res && Array.isArray(res.list)) {
        // 情况 1 & 2：请求成功（无论有没有数据）
        if (res.list.length) {
          this.hotList = reset ? res.list : this.hotList.concat(res.list)
          // 本次返回条数判定 hasMore：不满 PAGE_SIZE(6) 就是末页
          this.hotHasMore = res.list.length >= 6 ? !!res.hasMore : false
          if (this.hotHasMore) {
            this.hotPage = (res.page || targetPg) + 1
          }
          console.log('[home] loadHotList ok: count=' + res.list.length + ', hasMore=' + this.hotHasMore + ', nextPg=' + this.hotPage)
        } else if (reset) {
          // reset 但返回空：分类下没有内容
          if (!silent) this.hotList = []
          this.hotHasMore = false
          console.log('[home] loadHotList reset empty (分类无数据)')
        } else {
          // 非 reset 返回空：没有更多了
          this.hotHasMore = false
          console.log('[home] loadHotList no more (后端返回空列表)')
        }
      } else {
        // 情况 3：请求失败（res=null，比如网络错误/代理失败）
        // 失败不能把 hasMore 设 false，否则用户永远不能再触底重试；
        // 也不能推进页码，下次重试还是同一页
        console.warn('[home] loadHotList FAIL: 请求失败，保留 hasMore=true，下次重试 pg=' + targetPg)
        if (reset && !silent) {
          // reset 失败至少清空 loading 状态，列表保持空（静默刷新失败保留已有数据）
          this.hotList = []
        }
      }
      this.hotLoading = false
      this.hotInitialized = true
    },
    // 切换分类：重置列表并加载第 1 页
    async selectCategory(i) {
      if (i === this.activeCategory) return
      console.log('[home] selectCategory: ' + this.homeCategories[i] + ' (idx=' + i + ')')
      this.activeCategory = i
      await this.loadHotList(true)
      // 切换分类后同样要保证有滚动条
      this.$nextTick(() => {
        this._ensureScrollable()
      })
    },
    // scroll-view 触底：加载下一页
    onScrollToLower() {
      console.log('[home] ★ scrolltolower fired! hotInitialized=' + this.hotInitialized + ', hotLoading=' + this.hotLoading + ', hotHasMore=' + this.hotHasMore)
      if (this.hotLoading) {
        console.log('[home] scrolltolower skip: loading')
        return
      }
      if (!this.hotHasMore) {
        console.log('[home] scrolltolower skip: no more')
        return
      }
      // 必须至少有数据才允许触底加载（首屏加载完hotInitialized=true）
      if (!this.hotInitialized) {
        console.log('[home] scrolltolower skip: not initialized')
        return
      }
      this.loadHotList(false)
    },
    // 跳转片库（更多列表页）
    goLibrary() {
      uni.navigateTo({ url: '/pages/library/library' })
    },
    // 列表卡片直接跳播放页（跳过详情页）
    goDetail(itemOrId) {
      if (!itemOrId) return
      navigateToPlayer(itemOrId)
    },
    goPlayer(itemOrId) {
      this.goDetail(itemOrId)
    },
    goSearch() {
      uni.navigateTo({ url: '/pages/search/search' })
    },
    onCast() {
      uni.showToast({ title: '投屏功能开发中', icon: 'none' })
    }
  }
}
</script>

<style scoped>
.app-shell {
  /* 必须用固定 height: 100vh，不能 min-height！
     否则内容少时 shell 高度=内容高度，scroll-view 没有固定高度，
     flex:1 无法生效，导致没有滚动条，@scrolltolower 永不触发 */
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
  padding: 0 32rpx;
}

.brand {
  font-size: var(--vmk-text-xl);
  font-weight: 700;
  letter-spacing: 2rpx;
  color: var(--vmk-foreground);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 32rpx;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.page-content {
  /* 关键：作为 flex item 要正确分配剩余高度：
   * flex:1 分配空间 + height:0 防止被内容撑开 + min-height:0 允许收缩
   * 这三项组合让自定义 <uni-scroll-view> 获得"严格的视口剩余高度"，
   * 否则内部孙子级 div 的 overflow:auto 永远 scrollHeight===clientHeight，没有滚动条 */
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  display: block;
  /* padding 只留给内部内容；外层不要再让它被 padding 撑大 */
  box-sizing: border-box;
}

/* Hero */
.page-padding-wrapper {
  padding: 0 32rpx;
  /* 底部留出 nav bar 高度 + 安全距离 */
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}

.hero {
  position: relative;
  width: 100%;
  height: 360rpx;
  border-radius: var(--vmk-radius-lg);
  overflow: hidden;
  margin-bottom: 32rpx;
}

.hero-img {
  width: 100%;
  height: 100%;
}

.hero-overlay {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(to top, rgba(13,13,18,0.94) 0%, rgba(13,13,18,0.4) 50%, transparent 100%);
}

.hero-tag {
  position: absolute;
  top: 24rpx;
  left: 24rpx;
  height: 40rpx;
  padding: 0 16rpx;
  background-color: var(--vmk-primary);
  border-radius: var(--vmk-radius-sm);
  display: inline-flex;
  align-items: center;
}

.hero-tag-text {
  font-size: var(--vmk-text-xs);
  font-weight: 600;
  color: var(--vmk-foreground);
}

.hero-info {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 24rpx;
}

.hero-title {
  font-size: var(--vmk-text-2xl);
  font-weight: 700;
  color: var(--vmk-foreground);
  margin-bottom: 8rpx;
}

.hero-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6rpx;
  margin-bottom: 16rpx;
}

.hero-meta-text {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.hero-meta-dot {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
}

.hero-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hero-score {
  height: 40rpx;
  padding: 0 12rpx;
  background-color: var(--vmk-warning);
  border-radius: var(--vmk-radius-sm);
  display: inline-flex;
  align-items: center;
}

.hero-score-text {
  font-size: var(--vmk-text-xs);
  font-weight: 700;
  color: var(--vmk-background);
}

.play-btn {
  display: inline-flex;
  align-items: center;
  gap: 12rpx;
  height: 80rpx;
  padding: 0 40rpx;
  border-radius: var(--vmk-radius-xl);
  background-color: var(--vmk-primary);
}

.play-btn-text {
  font-size: var(--vmk-text-base);
  font-weight: 600;
  color: #FFFFFF;
}

/* Chips */
.chips-scroll {
  width: 100%;
  margin-bottom: 32rpx;
  white-space: nowrap;
}

.chips-row {
  display: flex;
  gap: 16rpx;
  padding-bottom: 4rpx;
}

.chip {
  display: inline-flex;
  align-items: center;
  height: 56rpx;
  padding: 0 28rpx;
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
  font-size: var(--vmk-text-sm);
  color: var(--vmk-foreground);
  white-space: nowrap;
}

/* Section */
.section {
  margin-bottom: 32rpx;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}

.section-title {
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
}

.more-btn {
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  padding: 8rpx 4rpx;
}

.more-btn-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}

/* Hot grid */
.hot-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}

.hot-card {
  width: calc((100% - 48rpx) / 3);
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}

.hot-poster {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-xl);
  overflow: hidden;
  background-color: var(--vmk-card);
}

.hot-poster-img {
  width: 100%;
  height: 100%;
}

.hot-title {
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.3;
  color: var(--vmk-foreground);
}

.hot-tag {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
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

.bottom-spacer {
  height: 32rpx;
}

/* ========================= 骨架屏 ========================= */
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
.hero-skeleton {
  width: 100%;
  height: 360rpx;
  border-radius: var(--vmk-radius-lg);
  margin-bottom: 32rpx;
}
.chips-skeleton-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.chip-skeleton {
  width: 120rpx;
  height: 56rpx;
  border-radius: var(--vmk-radius-full);
}
.section-title-skeleton {
  width: 200rpx;
  height: 36rpx;
  border-radius: 8rpx;
  margin-bottom: 24rpx;
}
.hot-skeleton {
  width: calc((100% - 48rpx) / 3);
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.poster-skeleton {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-xl);
}
.text-skeleton {
  width: 100%;
  height: 28rpx;
  border-radius: 6rpx;
}
.text-skeleton.short { width: 60%; }
</style>
