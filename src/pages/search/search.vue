<template>
  <view class="app-shell">
    <StatusBar />
    <view class="header">
      <view class="back-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <view class="search-box">
        <view class="search-icon">
          <VmkIcon name="search" :size="32" color="#9CA3AF" />
        </view>
        <input
          class="search-input"
          v-model="keyword"
          :placeholder="currentTab.placeholder"
          placeholder-class="search-ph"
          confirm-type="search"
          @confirm="onSearch"
          @input="onInput"
        />
        <view v-if="keyword" class="clear-btn" @tap="clearKeyword">
          <text class="clear-text">×</text>
        </view>
      </view>
      <text class="search-action" @tap="onSearch">搜索</text>
    </view>

    <!-- 搜索类型切换：片库 / 短剧 -->
    <view class="tab-bar">
      <view
        v-for="(t, i) in tabs"
        :key="t.key"
        class="tab-chip"
        :class="{ active: tabIdx === i }"
        @tap="switchTab(i)"
      >
        <text class="tab-chip-text">{{ t.label }}</text>
      </view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <!-- 搜索结果 -->
      <view v-if="searched">
        <view class="result-head">
          <text class="result-title">搜索结果 ({{ results.length }})</text>
        </view>
        <view v-if="loading" class="loading-wrap">
          <view class="spinner"></view>
          <text class="loading-text">正在搜索…</text>
        </view>
        <view v-else-if="results.length" class="foryou-list">
          <view
            v-for="item in results"
            :key="item.id"
            class="foryou-card"
            @tap="handleItemClick(item)"
          >
            <view class="foryou-poster">
              <image
                class="foryou-poster-img"
                :src="item.cover"
                mode="aspectFill"
                @error="onCoverError"
              />
            </view>
            <view class="foryou-info">
              <text class="foryou-title ellipsis">{{ item.title }}</text>
              <text class="foryou-meta">{{ item.meta || item.desc }}</text>
            </view>
          </view>
        </view>
        <view v-else class="empty">
          <text class="empty-text">未找到相关内容</text>
        </view>
      </view>

      <!-- 默认: 热搜 + 历史 -->
      <view v-else>
        <view class="section">
          <text class="section-title">热门搜索</text>
          <view class="hot-tags">
            <view
              v-for="(t, i) in hotWords"
              :key="t"
              class="hot-tag"
              @tap="searchWord(t)"
            >
              <text class="hot-rank" :class="{ top: i < 3 }">{{ i + 1 }}</text>
              <text class="hot-tag-text">{{ t }}</text>
            </view>
          </view>
        </view>

        <view class="section">
          <view class="section-head">
            <text class="section-title">搜索历史</text>
            <text class="clear-history" @tap="history = []">清空</text>
          </view>
          <view v-if="history.length" class="history-tags">
            <view
              v-for="h in history"
              :key="h"
              class="history-tag"
              @tap="searchWord(h)"
            >
              <text class="history-tag-text">{{ h }}</text>
            </view>
          </view>
          <view v-else class="empty-sm">
            <text class="empty-text">暂无搜索历史</text>
          </view>
        </view>
      </view>

      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'
import {
  fetchSearchHotWords,
  fetchOnlineSearch,
  fetchShortsSearch,
  navigateToPlayer
} from '@/api/index.js'

const TABS = [
  { key: 'library', label: '片库', placeholder: '搜索电影/电视剧/综艺/动漫', searchFn: fetchOnlineSearch },
  { key: 'shorts', label: '短剧', placeholder: '搜索短剧', searchFn: fetchShortsSearch }
]

export default {
  name: 'Search',
  components: { StatusBar, VmkIcon },
  data() {
    return {
      keyword: '',
      searched: false,
      results: [],
      history: [],
      hotWords: [],
      tabIdx: 0,
      tabs: TABS,
      loading: false
    }
  },
  computed: {
    currentTab() {
      return this.tabs[this.tabIdx] || {}
    }
  },
  async onShow() {
    this.hotWords = await fetchSearchHotWords()
  },
  methods: {
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/home/home' })
    },
    switchTab(i) {
      if (this.tabIdx === i) return
      this.tabIdx = i
      this.results = []
      if (this.searched && this.keyword.trim()) {
        this.doSearch(this.keyword.trim())
      }
    },
    onInput() {
      if (!this.keyword) {
        this.searched = false
        this.results = []
      }
    },
    onSearch() {
      const kw = this.keyword.trim()
      if (!kw) return
      this.doSearch(kw)
    },
    searchWord(w) {
      this.keyword = w
      this.doSearch(w)
    },
    async doSearch(kw) {
      this.loading = true
      this.searched = true
      this.results = []
      uni.showLoading({ title: '正在搜索…', mask: true })
      try {
        const fn = this.currentTab.searchFn || fetchOnlineSearch
        const list = (await fn(kw)) || []
        this.results = list
        if (!list.length) {
          uni.showToast({ title: '未搜到结果', icon: 'none', duration: 2000 })
        }
      } catch (e) {
        uni.showToast({ title: '搜索失败，请稍后重试', icon: 'none' })
      } finally {
        this.loading = false
        uni.hideLoading()
      }
      if (!this.history.includes(kw)) {
        this.history.unshift(kw)
        if (this.history.length > 10) this.history.pop()
      }
    },
    clearKeyword() {
      this.keyword = ''
      this.searched = false
      this.results = []
    },
    handleItemClick(item) {
      if (!item) return
      const ct = this.currentTab.key === 'shorts' ? 'shorts' : ''
      navigateToPlayer(item, null, ct)
    },
    onCoverError(e) {}
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
  gap: 16rpx;
  height: 112rpx;
  padding: 0 32rpx;
}
.back-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.search-box {
  flex: 1;
  height: 72rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  display: flex;
  align-items: center;
  padding: 0 24rpx;
  gap: 12rpx;
}
.search-icon {
  display: inline-flex;
  align-items: center;
}
.search-input {
  flex: 1;
  height: 72rpx;
  font-size: var(--vmk-text-base);
  color: var(--vmk-foreground);
}
.search-ph {
  color: var(--vmk-muted);
}
.clear-btn {
  width: 40rpx;
  height: 40rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.clear-text {
  font-size: 40rpx;
  color: var(--vmk-muted);
  line-height: 1;
}
.search-action {
  font-size: var(--vmk-text-base);
  color: var(--vmk-primary);
  flex-shrink: 0;
}

/* 搜索类型切换栏 */
.tab-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 0 32rpx 20rpx;
}
.tab-chip {
  height: 56rpx;
  padding: 0 32rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  border: 1px solid var(--vmk-border);
  display: inline-flex;
  align-items: center;
}
.tab-chip.active {
  background-color: var(--vmk-primary);
  border-color: var(--vmk-primary);
}
.tab-chip-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-foreground);
  white-space: nowrap;
}
.tab-chip.active .tab-chip-text {
  color: #FFFFFF;
}

.page-content {
  flex: 1 1 auto;
  height: 0;
  min-height: 0;
  padding: 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}
.section {
  margin-bottom: 48rpx;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}
.section-title {
  display: block;
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
  margin-bottom: 24rpx;
}
.clear-history {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.hot-tag {
  display: inline-flex;
  align-items: center;
  gap: 12rpx;
  height: 64rpx;
  padding: 0 24rpx;
  border-radius: var(--vmk-radius-md);
  background-color: var(--vmk-card);
  border: 1px solid var(--vmk-border);
}
.hot-rank {
  font-size: var(--vmk-text-base);
  font-weight: 700;
  color: var(--vmk-muted);
}
.hot-rank.top {
  color: var(--vmk-warning);
}
.hot-tag-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-foreground);
}
.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.history-tag {
  height: 56rpx;
  padding: 0 24rpx;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-muted-bg);
  display: inline-flex;
  align-items: center;
}
.history-tag-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.result-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 24rpx;
}
.result-title {
  display: block;
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.foryou-list {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}
.foryou-card {
  display: flex;
  gap: 24rpx;
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  padding: 24rpx;
}
.foryou-poster {
  position: relative;
  width: 144rpx;
  aspect-ratio: 3 / 4;
  border-radius: var(--vmk-radius-md);
  overflow: hidden;
  flex-shrink: 0;
  background-color: var(--vmk-muted-bg);
}
.foryou-poster-img {
  width: 100%;
  height: 100%;
}
.foryou-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10rpx;
}
.foryou-title {
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
}
.foryou-meta {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
  line-height: 1.5;
}
.empty {
  padding: 120rpx 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-sm {
  padding: 48rpx 0;
}
.empty-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.loading-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
  gap: 24rpx;
}
.spinner {
  width: 64rpx;
  height: 64rpx;
  border: 6rpx solid rgba(255,255,255,0.1);
  border-top-color: var(--vmk-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text {
  font-size: var(--vmk-text-sm);
  color: var(--vmk-muted);
}
.bottom-spacer {
  height: 32rpx;
}
</style>
