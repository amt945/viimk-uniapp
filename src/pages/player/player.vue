<template>
  <view
    class="player-page"
    :class="{ 'shorts-mode': isShorts, 'movie-mode': !isShorts, 'fs-active': isFullscreen }"
    @tap="onPageTap"
    @touchstart="onTouchStart"
    @touchmove="onTouchMove"
    @touchend="onTouchEnd"
    @touchcancel="onTouchEnd"
  >
    <!-- 视频背景 -->
    <view class="video-bg">
      <!-- 统一使用 H5 video slot（App 端 WebView 也支持） -->
      <view id="vmk-video-slot" class="video-el" :class="{ 'video-el-shorts': isShorts }"></view>

      <!-- 加载中 -->
      <view v-if="loading" class="overlay loading-overlay" @tap.stop>
        <view class="spinner"></view>
        <text class="overlay-text">{{ loadingText }}</text>
      </view>

      <!-- 错误 -->
      <view v-if="errMsg" class="overlay error-overlay" @tap.stop>
        <text class="overlay-text error-text">{{ errMsg }}</text>
        <view class="retry-btn" @tap.stop="retry">
          <text class="retry-text">重试</text>
        </view>
      </view>

      <!-- H5 点击播放 / 取消静音 -->
      <!-- #ifdef H5 -->
      <view v-if="needTapPlay && !errMsg" class="overlay tap-play-overlay" @tap.stop="tapToPlay">
        <view class="tap-play-icon">
          <VmkIcon name="play" :size="64" color="#FFFFFF" />
        </view>
        <text class="overlay-text">点击播放</text>
      </view>
      <!-- #endif -->
    </view>

    <!-- ========== 短剧布局（竖屏/短视频风格） ========== -->
    <template v-if="isShorts">
      <!-- 上下滑动换集提示（轻量常驻） -->
      <view v-if="!showPanel && !showSpeedMenu && !showMoreMenu" class="swipe-hint" @tap.stop>
        <view class="swipe-hint-arrows">
          <view class="swipe-hint-arrow" :class="{ disabled: currentEpIdx <= 0 }">
            <VmkIcon name="chevron-up" :size="28" color="#FFFFFF" />
          </view>
          <text class="swipe-hint-ep">第 {{ currentEpIdx + 1 }} / {{ episodes.length || '?' }} 集</text>
          <view class="swipe-hint-arrow" :class="{ disabled: currentEpIdx >= episodes.length - 1 }">
            <VmkIcon name="chevron-down" :size="28" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 顶部控制栏（参考电影播放器） -->
      <view v-if="showTopBar" class="shorts-top-bar" :style="{ paddingTop: statusBarHeight + 'px' }" @tap.stop>
        <view class="shorts-top-btn" @tap="goBack">
          <VmkIcon name="chevron-left" :size="44" color="#FFFFFF" />
        </view>
        <view class="shorts-top-info">
          <text class="shorts-top-title ellipsis">{{ headerTitle }}</text>
          <text class="shorts-top-sub" v-if="detail && detail.remarks">{{ detail.remarks }}</text>
        </view>
        <view class="shorts-top-actions">
          <view class="shorts-top-btn" @tap="toggleFavorite">
            <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="36" :color="isFavorited ? '#FFB800' : '#FFFFFF'" />
          </view>
          <view class="shorts-top-btn" @tap="openMoreMenu">
            <VmkIcon name="more" :size="36" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 中央：暂停时显示大播放按钮 -->
      <view v-if="!isPlaying || showCenterControl" class="shorts-center-overlay" @tap.stop>
        <view v-if="showCenterControl || !isPlaying" class="shorts-center-play-btn" @tap="togglePlay">
          <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="72" color="#FFFFFF" />
        </view>
      </view>

      <!-- 底部控制栏：播放/暂停 + 时间 + 进度条 + 静音 + 倍速 + 全屏（参考电影播放器） -->
      <view class="shorts-control-bar" v-if="showTopBar && !loading && !errMsg" @tap.stop>
        <view class="shorts-ctrl-btn" @tap="togglePlay">
          <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="28" color="#FFFFFF" />
        </view>
        <text class="shorts-ctrl-time">{{ currentTimeStr }}</text>
        <view
          class="shorts-progress-track"
          @tap="onSeekProgress"
          @touchstart="onSeekStart"
          @touchmove.prevent="onSeekMove"
          @touchend="onSeekEnd"
        >
          <view class="progress-buffered" :style="{ width: bufferedPercent + '%' }"></view>
          <view class="progress-played" :style="{ width: playedPercent + '%' }"></view>
          <view class="progress-thumb" :style="{ left: playedPercent + '%' }"></view>
        </view>
        <text class="shorts-ctrl-time">{{ durationStr }}</text>
        <view class="shorts-ctrl-btn" @tap="toggleMute">
          <VmkIcon :name="isMuted ? 'volume-off' : 'volume-2'" :size="24" color="#FFFFFF" />
        </view>
        <view class="shorts-ctrl-btn" @tap="openSpeedMenu">
          <text class="shorts-ctrl-speed">{{ currentSpeed }}x</text>
        </view>
        <view class="shorts-ctrl-btn" @tap="toggleFullscreen">
          <VmkIcon :name="isFullscreen ? 'minimize' : 'expand'" :size="24" color="#FFFFFF" />
        </view>
      </view>

      <!-- 底部选集栏 -->
      <view v-if="!showPanel" class="shorts-bottom-bar" @tap.stop="togglePanel">
        <view class="shorts-ep-scroll">
          <view class="shorts-ep-info">
            <text class="shorts-ep-title">选集</text>
            <text class="shorts-ep-divider">·</text>
            <text class="shorts-ep-status">{{ detail && detail.remarks ? detail.remarks : '已完结' }}</text>
            <text class="shorts-ep-divider">·</text>
            <text class="shorts-ep-count">全{{ episodes.length || '?' }}集</text>
          </view>
          <scroll-view class="shorts-ep-strip" scroll-x :show-scrollbar="false" v-if="episodes.length">
            <view class="shorts-ep-list">
              <view
                v-for="(ep, i) in episodes"
                :key="i"
                class="shorts-ep-chip"
                :class="{ active: currentEpIdx === i }"
                @tap.stop="selectEpisode(i)"
              >
                <text class="shorts-ep-chip-name">{{ ep.name }}</text>
              </view>
            </view>
          </scroll-view>
          <view class="shorts-ep-expand" @tap.stop="togglePanel">
            <text class="shorts-ep-expand-text">展开</text>
            <VmkIcon name="chevron-up" :size="28" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 底部弹出面板 -->
      <view v-if="showPanel" class="panel-mask" @tap="togglePanel">
        <view class="panel" @tap.stop>
          <view class="panel-handle"></view>

          <view class="work-info">
            <image class="work-cover" :src="detail ? detail.cover : poster" mode="aspectFill" />
            <view class="work-meta">
              <view class="work-title-row">
                <text class="work-title ellipsis">{{ detail ? detail.title : playTitle }}</text>
              </view>
              <text class="work-subtitle ellipsis">{{ workSubtitle }}</text>
              <text v-if="detail && detail.content" class="work-desc ellipsis-2">{{ detail.content }}</text>
            </view>
          </view>

          <view class="panel-tabs">
            <view
              v-for="t in panelTabs"
              :key="t.key"
              class="panel-tab"
              :class="{ active: panelTab === t.key }"
              @tap="panelTab = t.key"
            >
              <text class="panel-tab-text">{{ t.label }}</text>
            </view>
          </view>

          <scroll-view v-if="panelTab === 'episodes'" class="panel-content" scroll-y>
            <view class="ep-grid">
              <view
                v-for="(ep, i) in episodes"
                :key="i"
                class="ep-item"
                :class="{ active: currentEpIdx === i }"
                @tap="selectEpisode(i)"
              >
                <text class="ep-name">{{ ep.name }}</text>
              </view>
            </view>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <scroll-view v-else-if="panelTab === 'intro'" class="panel-content" scroll-y>
            <text class="intro-text">{{ introText }}</text>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <scroll-view v-else class="panel-content" scroll-y>
            <view class="series-list">
              <view
                v-for="(s, i) in seriesList"
                :key="i"
                class="series-item"
                @tap="goSeries(s)"
              >
                <image class="series-cover" :src="s.cover" mode="aspectFill" />
                <text class="series-title ellipsis">{{ s.title }}</text>
                <text v-if="s.flag" class="series-tag ellipsis">{{ s.flag }}</text>
              </view>
            </view>
            <view class="panel-bottom-spacer"></view>
          </scroll-view>

          <view class="favorite-btn" @tap="toggleFavorite">
            <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="32" color="#FFB800" />
            <text class="favorite-text">{{ isFavorited ? '已收藏' : '收藏' }}</text>
          </view>
        </view>
      </view>
    </template>

    <!-- ========== 电影/电视剧布局（1/3 视频 + 控制栏叠加 + 底部选集栏 + 弹出面板） ========== -->
    <template v-else>
      <!-- 视频区控制层（叠加在 1/3 视频上） -->
      <view class="movie-video-controls"
        @tap.stop
        @touchstart.stop="onMovieVideoTouchStart"
        @touchmove.stop="onMovieVideoTouchMove"
        @touchend.stop="onMovieVideoTouchEnd"
        @touchcancel.stop="onMovieVideoTouchEnd"
      >
        <!-- 顶部栏：返回 + 标题 + 收藏 + 更多 -->
        <view class="movie-top-bar" :style="{ paddingTop: statusBarHeight + 'px' }" v-if="showTopBar">
          <view class="top-btn" @tap="goBack">
            <VmkIcon name="chevron-left" :size="44" color="#FFFFFF" />
          </view>
          <view class="top-title-wrap">
            <text class="top-title ellipsis">{{ headerTitle }}</text>
          </view>
          <view class="top-actions">
            <view class="top-btn" @tap="toggleFavorite">
              <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="36" :color="isFavorited ? '#FFB800' : '#FFFFFF'" />
            </view>
            <view class="top-btn" @tap="openMoreMenu">
              <VmkIcon name="more" :size="36" color="#FFFFFF" />
            </view>
          </view>
        </view>

        <!-- 中央：暂停时显示大播放按钮 -->
        <view v-if="!isPlaying || showCenterControl" class="movie-center-overlay">
          <view v-if="showCenterControl || !isPlaying" class="movie-center-play-btn" @tap="togglePlay">
            <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="72" color="#FFFFFF" />
          </view>
        </view>

        <!-- 上下滑动换集提示（多集时显示，轻量常驻） -->
        <view v-if="episodes.length > 1 && !showSpeedMenu && !showMoreMenu" class="movie-swipe-hint" @tap.stop>
          <view class="movie-swipe-arrow" :class="{ disabled: currentEpIdx <= 0 }">
            <VmkIcon name="chevron-up" :size="24" color="#FFFFFF" />
          </view>
          <text class="movie-swipe-ep">{{ currentEpIdx + 1 }}/{{ episodes.length }}</text>
          <view class="movie-swipe-arrow" :class="{ disabled: currentEpIdx >= episodes.length - 1 }">
            <VmkIcon name="chevron-down" :size="24" color="#FFFFFF" />
          </view>
        </view>

        <!-- 底部控制栏：播放/暂停 + 时间 + 进度条 + 倍速 + 静音 + 全屏 -->
        <view class="movie-bottom-bar" v-if="showTopBar && !loading && !errMsg">
          <view class="movie-bottom-btn" @tap="togglePlay">
            <VmkIcon :name="isPlaying ? 'pause' : 'play'" :size="28" color="#FFFFFF" />
          </view>
          <text class="movie-bottom-time">{{ currentTimeStr }}</text>
          <view
            class="movie-progress-track"
            ref="progressTrack"
            @tap="onSeekProgress"
            @touchstart="onSeekStart"
            @touchmove.prevent="onSeekMove"
            @touchend="onSeekEnd"
          >
            <view class="progress-buffered" :style="{ width: bufferedPercent + '%' }"></view>
            <view class="progress-played" :style="{ width: playedPercent + '%' }"></view>
            <view class="progress-thumb" :style="{ left: playedPercent + '%' }"></view>
          </view>
          <text class="movie-bottom-time">{{ durationStr }}</text>
          <view class="movie-bottom-btn" @tap="toggleMute">
            <VmkIcon :name="isMuted ? 'volume-off' : 'volume-2'" :size="24" color="#FFFFFF" />
          </view>
          <view class="movie-bottom-btn" @tap="openSpeedMenu">
            <text class="movie-bottom-speed">{{ currentSpeed }}x</text>
          </view>
          <view class="movie-bottom-btn" @tap="toggleFullscreen">
            <VmkIcon :name="isFullscreen ? 'minimize' : 'expand'" :size="24" color="#FFFFFF" />
          </view>
        </view>
      </view>

      <!-- 内容区（视频下方，默认展开，不遮挡播放器） -->
      <view class="movie-info-area" @tap.stop="showTopBar = false">
        <!-- Tab 栏 -->
        <view class="movie-info-tabs">
          <view
            v-for="t in panelTabs"
            :key="t.key"
            class="movie-info-tab"
            :class="{ active: panelTab === t.key }"
            @tap.stop="panelTab = t.key"
          >
            <text class="movie-info-tab-text">{{ t.label }}</text>
          </view>
        </view>

        <!-- 选集 tab -->
        <scroll-view v-if="panelTab === 'episodes'" class="movie-info-content" scroll-y :show-scrollbar="false">
          <view class="ep-grid">
            <view
              v-for="(ep, i) in episodes"
              :key="i"
              class="ep-item"
              :class="{ active: currentEpIdx === i }"
              @tap.stop="selectEpisode(i)"
            >
              <text class="ep-name">{{ ep.name }}</text>
            </view>
          </view>
          <view class="panel-lines" v-if="detail && detail.lines && detail.lines.length > 1">
            <text class="panel-lines-title">播放线路</text>
            <view class="panel-lines-list">
              <view
                v-for="(line, li) in detail.lines"
                :key="li"
                class="panel-line-chip"
                :class="{ active: lineIdx === li }"
                @tap.stop="switchLine(li)"
              >
                <text class="panel-line-text">{{ line.flag || ('线路' + (li + 1)) }}</text>
              </view>
            </view>
          </view>
          <view class="movie-info-spacer"></view>
        </scroll-view>

        <!-- 简介 tab -->
        <scroll-view v-else-if="panelTab === 'intro'" class="movie-info-content" scroll-y :show-scrollbar="false">
          <!-- 作品信息（移到简介上方） -->
          <view class="movie-info-header">
            <image class="movie-info-cover" :src="detail ? detail.cover : poster" mode="aspectFill" />
            <view class="movie-info-meta">
              <view class="movie-info-title-row">
                <text class="movie-info-title ellipsis">{{ detail ? detail.title : playTitle }}</text>
                <text v-if="detail && detail.score" class="movie-info-score">{{ detail.score }}</text>
              </view>
              <text class="movie-info-subtitle ellipsis">{{ workSubtitle }}</text>
              <view class="movie-info-actions">
                <view class="movie-info-fav" @tap.stop="toggleFavorite">
                  <VmkIcon :name="isFavorited ? 'star-filled' : 'star'" :size="32" :color="isFavorited ? '#FFB800' : '#FFFFFF'" />
                  <text class="movie-info-fav-text">{{ isFavorited ? '已收藏' : '收藏' }}</text>
                </view>
              </view>
            </view>
          </view>
          <view class="panel-credits" v-if="detail && (detail.director || detail.actor)">
            <text class="panel-credit-line" v-if="detail.director">导演：{{ detail.director }}</text>
            <text class="panel-credit-line" v-if="detail.actor">主演：{{ detail.actor }}</text>
          </view>
          <text class="intro-text">{{ introText }}</text>
          <view class="panel-lines" v-if="detail && detail.lines && detail.lines.length > 1">
            <text class="panel-lines-title">播放线路</text>
            <view class="panel-lines-list">
              <view
                v-for="(line, li) in detail.lines"
                :key="li"
                class="panel-line-chip"
                :class="{ active: lineIdx === li }"
                @tap.stop="switchLine(li)"
              >
                <text class="panel-line-text">{{ line.flag || ('线路' + (li + 1)) }}</text>
              </view>
            </view>
          </view>
          <view class="movie-info-spacer"></view>
        </scroll-view>

        <!-- 系列剧 tab -->
        <scroll-view v-else class="movie-info-content" scroll-y :show-scrollbar="false">
          <view class="series-list">
            <view
              v-for="(s, i) in seriesList"
              :key="i"
              class="series-item"
              @tap="goSeries(s)"
            >
              <image class="series-cover" :src="s.cover" mode="aspectFill" />
              <text class="series-title ellipsis">{{ s.title }}</text>
              <text v-if="s.flag" class="series-tag ellipsis">{{ s.flag }}</text>
            </view>
          </view>
          <view class="movie-info-spacer"></view>
        </scroll-view>
      </view>
    </template>

    <!-- 倍速选择弹窗 -->
    <view v-if="showSpeedMenu" class="modal-mask" @tap="showSpeedMenu = false">
      <view class="modal-list" @tap.stop>
        <view
          v-for="s in speedOptions"
          :key="s"
          class="modal-item"
          :class="{ active: currentSpeed === s }"
          @tap="selectSpeed(s)"
        >
          <text class="modal-item-text">{{ s }}x</text>
          <view v-if="currentSpeed === s" class="modal-check">✓</view>
        </view>
      </view>
    </view>

    <!-- 更多操作弹窗 -->
    <view v-if="showMoreMenu" class="modal-mask" @tap="showMoreMenu = false">
      <view class="modal-list" @tap.stop>
        <view class="modal-item" @tap="addToOffline">
          <text class="modal-item-text">加入缓存</text>
        </view>
        <view class="modal-item" @tap="copyLink">
          <text class="modal-item-text">复制链接</text>
        </view>
        <view class="modal-item" @tap="shareVideo">
          <text class="modal-item-text">分享</text>
        </view>
        <view class="modal-item" @tap="toggleFavorite">
          <text class="modal-item-text">{{ isFavorited ? '取消收藏' : '收藏' }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import VmkIcon from '@/components/VmkIcon.vue'
import { fetchOnlineDetail, fetchOnlineResolve, toggleFavorite, isFavorited, updateHistory, addOfflineItem } from '@/api/index.js'

const IS_H5 = true  // App 端也是 WebView，统一使用 H5 播放方案

export default {
  name: 'Player',
  components: { VmkIcon },
  data() {
    return {
      playTitle: '正在播放',
      poster: '',
      loading: false,
      loadingText: '加载中…',
      errMsg: '',
      statusBarHeight: 20,
      vodId: '',
      siteKey: '',
      rawUrl: '',
      isDirect: false,
      contentType: '',
      detail: null,
      episodes: [],
      currentEpIdx: 0,
      lineIdx: 0,
      _hls: null,
      _h5Video: null,
      _resolved: false,
      _orientationDetected: false,
      mutedAuto: true,
      isMuted: true,
      needTapPlay: false,
      isPlaying: false,
      isFullscreen: false,
      showTopBar: true,
      showCenterControl: false,
      showPanel: false,
      showSpeedMenu: false,
      showMoreMenu: false,
      currentSpeed: 1.0,
      speedOptions: [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
      panelTab: 'episodes',
      panelTabs: [
        { key: 'intro', label: '简介' },
        { key: 'episodes', label: '选集' },
        { key: 'series', label: '系列剧' }
      ],
      isFavorited: false,
      seriesList: [],
      synopsisExpanded: false,
      // 进度条状态（H5 自定义控制）
      currentTime: 0,
      duration: 0,
      buffered: 0,
      _seeking: false
    }
  },
  computed: {
    isShorts() {
      return this.contentType === 'shorts'
    },
    currentLine() {
      if (!this.detail || !this.detail.lines || !this.detail.lines.length) return null
      return this.detail.lines[this.lineIdx] || this.detail.lines[0]
    },
    headerTitle() {
      const ep = this.episodes[this.currentEpIdx]
      if (!this.detail) return this.playTitle
      const epName = ep ? ep.name : ''
      return epName || this.playTitle
    },
    workSubtitle() {
      if (!this.detail) return ''
      const parts = []
      if (this.detail.year) parts.push(this.detail.year)
      if (this.detail.area) parts.push(this.detail.area)
      const count = this.episodes.length
      if (count) parts.push('全' + count + '集')
      return parts.join(' · ')
    },
    introText() {
      if (!this.detail) return '暂无简介'
      return this.detail.content || '暂无简介'
    },
    // 进度条百分比
    playedPercent() {
      if (!this.duration) return 0
      return Math.min(100, Math.max(0, (this.currentTime / this.duration) * 100))
    },
    bufferedPercent() {
      if (!this.duration) return 0
      return Math.min(100, Math.max(0, (this.buffered / this.duration) * 100))
    },
    currentTimeStr() {
      return this._formatTime(this.currentTime)
    },
    durationStr() {
      return this._formatTime(this.duration)
    }
  },
  mounted() {
    if (IS_H5) {
      this.$nextTick(() => this._createH5Video())
    }
    // 调试/预览环境：暴露组件实例到全局，便于手动调用方法验证
    if (typeof window !== 'undefined') {
      try { window.__vmkPlayer = this } catch (_) {}
    }
    // 监听原生 Android 返回键触发的退出全屏事件
    if (typeof window !== 'undefined') {
      this._onNativeExitFs = () => {
        if (this.isFullscreen) {
          this.isFullscreen = false
          this.showTopBar = true
        }
      }
      window.addEventListener('viimkExitFullscreen', this._onNativeExitFs)
      window.__vmkExitFullscreen = this._onNativeExitFs
    }
    // 监听页面可见性变化（手机息屏/切后台 → 亮屏恢复）
    // Android WebView 息屏时会自动暂停 video，亮屏后需手动恢复播放
    if (typeof document !== 'undefined') {
      this._onVisibilityChange = () => {
        if (document.hidden) {
          // 息屏/切后台：记录播放状态，暂停视频（不销毁，保留进度）
          this._wasPlayingBeforeHidden = this.isPlaying
          const v = this._h5Video
          if (v && !v.paused) {
            try { v.pause() } catch (e) {}
          }
        } else {
          // 亮屏/恢复：如果之前在播放，恢复播放
          if (this._wasPlayingBeforeHidden) {
            this._wasPlayingBeforeHidden = false
            // 延迟 300ms 确保 WebView 完全恢复后再 play
            setTimeout(() => {
              this._resumePlayback()
            }, 300)
          }
        }
      }
      document.addEventListener('visibilitychange', this._onVisibilityChange)
    }
  },
  beforeUnmount() {
    // 离开播放页前恢复竖屏，避免别的页面也是横屏
    this._nativeSetOrientation('portrait')
    if (typeof window !== 'undefined') {
      window.removeEventListener('viimkExitFullscreen', this._onNativeExitFs)
      if (window.__vmkExitFullscreen === this._onNativeExitFs) {
        window.__vmkExitFullscreen = null
      }
    }
    if (typeof document !== 'undefined' && this._onVisibilityChange) {
      document.removeEventListener('visibilitychange', this._onVisibilityChange)
      this._onVisibilityChange = null
    }
  },
  updated() {
    if (IS_H5) this._ensureH5Video()
  },
  async onLoad(options) {
    const q = options || {}
    this.contentType = q.contentType || ''
    this.vodId = q.vodId || q.vod_id || q.id || ''
    this.siteKey = q.site || q.online_site || ''
    const initEp = parseInt(q.epIdx || q.ep || '0', 10)
    this.currentEpIdx = isNaN(initEp) ? 0 : initEp
    if (q.url) {
      try { this.rawUrl = decodeURIComponent(q.url) } catch (e) { this.rawUrl = q.url }
    }
    if (q.title) {
      try { this.playTitle = decodeURIComponent(q.title) } catch (e) { this.playTitle = q.title }
    }
    if (q.poster) {
      try { this.poster = decodeURIComponent(q.poster) } catch (e) { this.poster = q.poster }
    }
    this._initSafeArea()

    if (this.vodId) {
      await this.loadDetail()
      await this.$nextTick()
      await this.playEpisode(this.currentEpIdx)
      this.loadRecommend()
      return
    }
    if (this.rawUrl) {
      this.isDirect = this._isDirectUrl(this.rawUrl)
      // action / 直接 url 模式：先判断是否已收藏
      this.isFavorited = isFavorited('', '', this.rawUrl)
      this.startPlayUrl(this.rawUrl)
    }
  },
  onUnload() {
    this.destroyHls()
    // 离开页面时强制恢复竖屏
    this._nativeSetOrientation('portrait')
    if (typeof window !== 'undefined') {
      window.removeEventListener('viimkExitFullscreen', this._onNativeExitFs)
      if (window.__vmkExitFullscreen === this._onNativeExitFs) {
        window.__vmkExitFullscreen = null
      }
    }
    if (typeof document !== 'undefined' && this._onVisibilityChange) {
      document.removeEventListener('visibilitychange', this._onVisibilityChange)
      this._onVisibilityChange = null
    }
  },
  onHide() {
    // 页面被覆盖（跳转其他页面）：记录播放状态后销毁，onShow 时重建恢复
    this._wasPlayingBeforeHide = this.isPlaying
    this._resumeTime = this.currentTime || 0
    this._suspendedByHide = true
    this.destroyHls()
  },
  onShow() {
    // 从其他页面返回：如果 onHide 销毁了播放器，重建并恢复到之前的进度
    if (this._suspendedByHide) {
      this._suspendedByHide = false
      const wasPlaying = this._wasPlayingBeforeHide
      const resumeTime = this._resumeTime || 0
      this._wasPlayingBeforeHide = false
      this._resumeTime = 0
      // 重置 resolved 标志，强制重新解析（避免复用已失效的地址）
      this._resolved = false
      this._pendingResumeTime = resumeTime
      this._pendingAutoPlay = wasPlaying
      if (this.vodId && this.episodes.length) {
        this.playEpisode(this.currentEpIdx)
      } else if (this.rawUrl) {
        this.startPlayUrl(this.rawUrl)
      }
    }
  },
  methods: {
    _isDirectUrl(url) {
      if (!url) return false
      return /\.(m3u8|mp4|flv|ts|mov|mkv|avi|webm)(\?|#|$)/i.test(url)
    },
    _initSafeArea() {
      if (IS_H5) {
        this.statusBarHeight = 20
        return
      }
      try {
        const info = uni.getSystemInfoSync()
        this.statusBarHeight = (info.statusBarHeight || 20)
      } catch (e) {}
    },
    onPageTap() {
      // 滑动换集后会触发 tap，这里抑制掉
      if (this._swipeSuppress) {
        this._swipeSuppress = false
        return
      }
      this.showTopBar = !this.showTopBar
      // 显示控制栏时同时显示中央按钮，3 秒后自动隐藏中央按钮
      if (this.showTopBar) {
        this.showCenterControl = true
        clearTimeout(this._centerTimer)
        this._centerTimer = setTimeout(() => {
          this.showCenterControl = false
        }, 3000)
      }
    },
    togglePanel() {
      this.showPanel = !this.showPanel
      if (this.showPanel) this.showTopBar = false
      else this.showTopBar = true
    },
    openSpeedMenu() {
      this.showSpeedMenu = true
      this.showMoreMenu = false
    },
    openMoreMenu() {
      this.showMoreMenu = true
      this.showSpeedMenu = false
    },
    selectSpeed(s) {
      this.currentSpeed = s
      this.showSpeedMenu = false
      if (this._h5Video) {
        this._h5Video.playbackRate = s
      }
    },
    togglePlay() {
      const v = this._h5Video
      if (!v) return
      if (v.paused) {
        // 用户点击播放按钮（手势上下文）：优先尝试解除静音出声
        const needTapPlay = this.needTapPlay
        this.needTapPlay = false
        const tryWithSound = () => {
          if (this.mutedAuto && v.muted) {
            v.muted = false
            this.isMuted = false
            this.mutedAuto = false
          }
          return v.play()
        }
        tryWithSound().catch((e) => {
          // 浏览器策略阻止有声音播放：静音重试（不丢失自动播放）
          if (e && (e.name === 'NotAllowedError' || e.name === 'AbortError')) {
            v.muted = true
            this.isMuted = true
            this.mutedAuto = true
            v.play().catch(() => {
              // 连静音播放都被阻止（需要用户手势）→ 显示点击播放
              this.needTapPlay = needTapPlay !== false
            })
          }
        })
      } else {
        v.pause()
      }
    },
    // 快进 / 快退（±delta 秒）
    seekBy(delta) {
      const v = this._h5Video
      if (!v || !v.duration) return
      const target = Math.max(0, Math.min(v.duration, (v.currentTime || 0) + delta))
      v.currentTime = target
      this.currentTime = target
      this._flashControls()
    },
    // 短暂显示控制栏（快进/快退反馈）
    _flashControls() {
      this.showTopBar = true
      this.showCenterControl = true
      if (this._ctrlTimer) clearTimeout(this._ctrlTimer)
      this._ctrlTimer = setTimeout(() => {
        if (this.isPlaying) {
          this.showCenterControl = false
        }
      }, 2000)
    },
    // ================ 电影/电视剧模式：视频区上下滑动换集 ================
    // 仅在 1/3 视频区域内生效，不影响下方内容区滚动
    onMovieVideoTouchStart(e) {
      const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (!t) return
      this._mvTouchStartX = t.clientX
      this._mvTouchStartY = t.clientY
      this._mvTouchStartTime = Date.now()
      this._mvTouchMoved = false
    },
    onMovieVideoTouchMove(e) {
      const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (!t || this._mvTouchStartY == null) return
      const dy = t.clientY - this._mvTouchStartY
      const dx = t.clientX - this._mvTouchStartX
      if (Math.abs(dy) > 10 || Math.abs(dx) > 10) this._mvTouchMoved = true
    },
    onMovieVideoTouchEnd(e) {
      if (this._mvTouchStartY == null) return
      const t = (e.changedTouches && e.changedTouches[0]) || (e.touches && e.touches[0])
      const endY = t ? t.clientY : this._mvTouchStartY
      const endX = t ? t.clientX : this._mvTouchStartX
      const dy = endY - this._mvTouchStartY
      const dx = endX - this._mvTouchStartX
      const dt = Date.now() - (this._mvTouchStartTime || 0)
      this._mvTouchStartY = null
      this._mvTouchStartX = null
      this._mvTouchStartTime = null
      // 没有明显移动 → 视为点击，交给 tap 处理（控制栏显隐）
      if (!this._mvTouchMoved) return
      // 必须以垂直滑动为主
      const isVertical = Math.abs(dy) > Math.abs(dx)
      if (!isVertical) return
      const SWIPE_THRESHOLD = 60
      const SWIPE_VELOCITY = 0.5
      const fast = dt > 0 && (Math.abs(dy) / dt) >= SWIPE_VELOCITY
      if (Math.abs(dy) < SWIPE_THRESHOLD && !fast) return
      if (this.showPanel || this.showSpeedMenu || this.showMoreMenu) return
      // 抑制紧随其后的 tap
      this._swipeSuppress = true
      if (dy < 0) {
        this._swipeEpisode(1)   // 上滑 → 下一集
      } else {
        this._swipeEpisode(-1)  // 下滑 → 上一集
      }
    },
    // ================ 短剧模式：上下滑动换集 ================
    onTouchStart(e) {
      if (!this.isShorts) return
      const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (!t) return
      this._touchStartX = t.clientX
      this._touchStartY = t.clientY
      this._touchStartTime = Date.now()
      this._touchMoved = false
    },
    onTouchMove(e) {
      if (!this.isShorts) return
      const t = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (!t || this._touchStartY == null) return
      const dy = t.clientY - this._touchStartY
      const dx = t.clientX - this._touchStartX
      // 标记是否发生过明显移动（用于区分点击与滑动）
      if (Math.abs(dy) > 10 || Math.abs(dx) > 10) this._touchMoved = true
    },
    onTouchEnd(e) {
      if (!this.isShorts) return
      if (this._touchStartY == null) return
      const t = (e.changedTouches && e.changedTouches[0]) || (e.touches && e.touches[0])
      const endY = t ? t.clientY : this._touchStartY
      const endX = t ? t.clientX : this._touchStartX
      const dy = endY - this._touchStartY
      const dx = endX - this._touchStartX
      const dt = Date.now() - (this._touchStartTime || 0)
      this._touchStartY = null
      this._touchStartX = null
      this._touchStartTime = null
      // 没有明显移动 → 视为点击，交给 onPageTap 处理
      if (!this._touchMoved) return
      // 必须以垂直滑动为主（|dy| > |dx|），且超过阈值或速度足够快
      const SWIPE_THRESHOLD = 60 // 像素
      const SWIPE_VELOCITY = 0.5  // px/ms
      const isVertical = Math.abs(dy) > Math.abs(dx)
      if (!isVertical) return
      const fast = dt > 0 && (Math.abs(dy) / dt) >= SWIPE_VELOCITY
      if (Math.abs(dy) < SWIPE_THRESHOLD && !fast) return
      // 面板打开时不切集（避免误触）
      if (this.showPanel || this.showSpeedMenu || this.showMoreMenu) return
      // 抑制紧随其后的 tap 事件（避免误触顶栏）
      this._swipeSuppress = true
      if (dy < 0) {
        // 上滑 → 下一集
        this._swipeEpisode(1)
      } else {
        // 下滑 → 上一集
        this._swipeEpisode(-1)
      }
    },
    _swipeEpisode(dir) {
      const next = this.currentEpIdx + dir
      if (next < 0) {
        uni.showToast({ title: '已经是第一集了', icon: 'none' })
        return
      }
      if (next >= this.episodes.length) {
        uni.showToast({ title: '已经是最后一集了', icon: 'none' })
        return
      }
      // 切集时给出视觉反馈
      uni.showToast({ title: dir > 0 ? '下一集' : '上一集', icon: 'none', duration: 600 })
      this.selectEpisode(next)
    },
    // 进度条：格式化时间 00:00
    _formatTime(s) {
      if (!s || isNaN(s) || s < 0) return '00:00'
      const total = Math.floor(s)
      const m = Math.floor(total / 60)
      const sec = total % 60
      const mm = m >= 60 ? Math.floor(m / 60) : 0
      const rest = m % 60
      const pad = (n) => String(n).padStart(2, '0')
      if (mm > 0) return pad(mm) + ':' + pad(rest) + ':' + pad(sec)
      return pad(m) + ':' + pad(sec)
    },
    // 进度条：从触摸/点击事件计算 seek 位置
    _updateSeekFromEvent(e) {
      const v = this._h5Video
      if (!v || !this.duration) return
      const trackEl = this.$refs.progressTrack
      if (!trackEl) return
      // H5 端 ref 是 DOM 元素
      const el = trackEl.$el || trackEl
      const rect = el.getBoundingClientRect()
      let x = 0
      const touch = (e.touches && e.touches[0]) || (e.changedTouches && e.changedTouches[0])
      if (touch && typeof touch.clientX === 'number') {
        x = touch.clientX
      } else if (e.detail && typeof e.detail.x === 'number') {
        x = e.detail.x
      }
      const ratio = Math.max(0, Math.min(1, (x - rect.left) / rect.width))
      v.currentTime = ratio * this.duration
      this.currentTime = v.currentTime
    },
    onSeekProgress(e) {
      if (this._seeking) return
      this._updateSeekFromEvent(e)
    },
    onSeekStart(e) {
      this._seeking = true
      this._updateSeekFromEvent(e)
    },
    onSeekMove(e) {
      if (this._seeking) this._updateSeekFromEvent(e)
    },
    onSeekEnd(e) {
      if (this._seeking) {
        this._updateSeekFromEvent(e)
        this._seeking = false
      }
    },
    toggleFullscreen() {
      // 电影/电视剧 进入全屏 → 横屏；退出 → 竖屏
      // 短剧默认竖屏，全屏只做 CSS 铺满不切横屏
      this.isFullscreen = !this.isFullscreen
      this.showTopBar = true
      if (!this.isShorts) {
        if (this.isFullscreen) {
          this._nativeSetOrientation('landscape')
        } else {
          this._nativeSetOrientation('portrait')
        }
      }
    },
    /** 调 Android VIIMKAppBridge.setOrientation 切横竖屏
     *  非原生 WebView（纯 H5 浏览器）时尝试 screen.orientation.lock，不成就静默失败
     */
    _nativeSetOrientation(orientation) {
      const o = orientation || 'portrait'
      if (typeof window === 'undefined') return
      // 1) 原生桥：VIIMKAppBridge.setOrientation
      const bridge = window.VIIMKAppBridge
      if (bridge && typeof bridge.setOrientation === 'function') {
        try {
          bridge.setOrientation(o)
          return
        } catch (e) {
          console.warn('[player] bridge.setOrientation failed:', e)
        }
      }
      // 2) uni-app 云打包端兜底
      // #ifdef APP-PLUS
      try {
        if (o === 'landscape') {
          plus.screen.lockOrientation('landscape-primary')
        } else {
          plus.screen.lockOrientation('portrait-primary')
        }
        return
      } catch (_) {}
      // #endif
      // 3) 浏览器端尝试 screen.orientation.lock（需在用户手势里，且移动端多数浏览器不支持，忽略）
      try {
        const scr = window.screen
        if (scr && scr.orientation && typeof scr.orientation.lock === 'function') {
          const map = {
            portrait: 'portrait-primary',
            landscape: 'landscape-primary',
            unspecified: 'any'
          }
          scr.orientation.lock(map[o] || 'any').catch(() => {})
        }
      } catch (_) {}
    },
    toggleMute() {
      const v = this._h5Video
      if (!v) return
      v.muted = !v.muted
      this.isMuted = v.muted
      this.mutedAuto = v.muted
      if (!v.muted) v.play().catch(() => {})
    },
    async toggleFavorite() {
      const hasVodId = !!this.vodId
      const hasUrl = !!this.rawUrl
      if (!hasVodId && !hasUrl) {
        uni.showToast({ title: '暂无可收藏内容', icon: 'none' })
        return
      }
      const res = await toggleFavorite({
        vodId: this.vodId,
        onlineSite: this.siteKey || 'ffzy',
        url: this.rawUrl || '',
        title: this.detail ? this.detail.title : this.playTitle,
        cover: this.detail ? this.detail.cover : this.poster,
        meta: this.detail ? this.detail.remarks : (this.contentType || ''),
        contentType: this.contentType || ''
      })
      this.isFavorited = !!(res && res.favorited)
      uni.showToast({ title: this.isFavorited ? '已收藏' : '已取消收藏', icon: 'none' })
    },
    // 写入历史记录（每次开始播放 1.5s 后调用一次）
    _savePlayHistory() {
      const id = this.vodId
        ? (this.siteKey || 'ffzy') + ':' + this.vodId + ':' + this.currentEpIdx
        : (this.rawUrl ? 'action:' + this.rawUrl : '')
      if (!id) return
      const ep = this.episodes[this.currentEpIdx]
      updateHistory({
        id,
        vodId: this.vodId || '',
        onlineSite: this.siteKey || '',
        url: this.rawUrl || (ep && ep.url) || '',
        title: this.detail ? this.detail.title : this.playTitle,
        cover: this.detail ? this.detail.cover : this.poster,
        meta: this.detail
          ? (this.detail.year || '') + (this.detail.year && this.detail.area ? ' · ' : '') + (this.detail.area || '') +
            (this.detail.genre ? ' · ' + this.detail.genre : '')
          : (this.contentType || '动作片'),
        remarks: this.detail ? (this.detail.remarks || '') : '',
        contentType: this.contentType || '',
        episode: (ep && ep.name) ? ep.name : '',
        episodeIndex: this.currentEpIdx
      }).catch(() => {})
    },
    // 加入离线缓存（仅登记下载记录，不做实际下载）
    async addToOffline() {
      const id = this.vodId
        ? (this.siteKey || 'ffzy') + ':' + this.vodId
        : (this.rawUrl ? 'action:' + this.rawUrl : '')
      if (!id) {
        uni.showToast({ title: '暂无可缓存内容', icon: 'none' })
        return
      }
      const ok = await addOfflineItem({
        id,
        url: this.rawUrl || '',
        title: this.detail ? this.detail.title : this.playTitle,
        cover: this.detail ? this.detail.cover : this.poster,
        meta: this.detail
          ? (this.detail.remarks || '') + (this.episodes.length ? ' · 全' + this.episodes.length + '集' : '')
          : (this.contentType || '动作片'),
        size: this.duration ? Math.round(this.duration * 0.2 / 1024 / 1024) + 'MB' : '未知'
      })
      this.showMoreMenu = false
      if (ok) {
        uni.showToast({ title: '已加入下载队列', icon: 'none' })
      }
    },
    copyLink() {
      const url = window.location.href
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
          uni.showToast({ title: '链接已复制', icon: 'none' })
        })
      }
      this.showMoreMenu = false
    },
    shareVideo() {
      uni.showToast({ title: '分享功能开发中', icon: 'none' })
      this.showMoreMenu = false
    },
    goSeries(s) {
      if (!s) return
      const params = [
        'vodId=' + encodeURIComponent(s.vodId || s.id || ''),
        'site=' + encodeURIComponent(s.onlineSite || 'ffzy'),
        'title=' + encodeURIComponent(s.title || '')
      ]
      if (s.cover) params.push('poster=' + encodeURIComponent(s.cover))
      if (this.contentType) params.push('contentType=' + encodeURIComponent(this.contentType))
      uni.redirectTo({ url: '/pages/player/player?' + params.join('&') })
    },
    _createH5Video() {
      if (this._h5Video) return this._h5Video
      const video = document.createElement('video')
      video.id = 'vmk-h5-video'
      video.controls = false
      video.autoplay = true
      video.muted = true
      video.setAttribute('playsinline', '')
      video.setAttribute('webkit-playsinline', '')
      const fit = this.isShorts ? 'cover' : 'contain'
      video.style.cssText = 'width:100%;height:100%;object-fit:' + fit + ';background:#000;'
      if (this.poster) video.poster = this.poster
      video.addEventListener('click', () => {
        // 上下滑动换集后会触发 click，这里抑制掉
        if (this._swipeSuppress) {
          this._swipeSuppress = false
          return
        }
        if (video.muted) {
          video.muted = false
          this.isMuted = false
          this.mutedAuto = false
          video.play().catch(() => {})
        } else {
          this.showTopBar = !this.showTopBar
          this.isPlaying = !video.paused
        }
      })
      video.addEventListener('play', () => {
        this.isPlaying = true
        // 开始播放后写入历史记录（防抖，避免频繁 seek 触发多次）
        clearTimeout(this._historyDebounce)
        this._historyDebounce = setTimeout(() => this._savePlayHistory(), 1500)
      })
      video.addEventListener('pause', () => { this.isPlaying = false })
      video.addEventListener('ratechange', () => {})
      // 播完自动播放下一集（ended 事件在 HLS.js 暂停/恢复后可能不触发，作兜底）
      video.addEventListener('ended', () => {
        this._autoPlayNext()
      })
      // 进度条：监听时间/时长/缓冲
      // 同时用 timeupdate 检测接近结尾，触发自动播放下一集（比 ended 更可靠）
      video.addEventListener('timeupdate', () => {
        if (!this._seeking) this.currentTime = video.currentTime || 0
        this._checkEndedAutoNext()
      })
      video.addEventListener('loadedmetadata', () => {
        this.duration = video.duration || 0
        // 动作片：根据视频方向自动切换布局
        // 横向视频(width > height) → 电影模式；竖向视频(height > width) → 短剧模式
        if (this.contentType === 'action' && !this._orientationDetected) {
          this._orientationDetected = true
          const vw = video.videoWidth || 0
          const vh = video.videoHeight || 0
          if (vw > 0 && vh > 0) {
            if (vh > vw) {
              // 竖向视频 → 短剧模式
              this.contentType = 'shorts'
              this._h5Video.style.objectFit = 'cover'
              console.log('[player] action video is vertical → shorts mode')
            } else {
              // 横向视频 → 电影模式
              this.contentType = ''
              console.log('[player] action video is horizontal → movie mode')
            }
            // 强制重新渲染模板（isShorts 计算属性会跟随更新）
            this.$forceUpdate()
          }
        }
        // 从其他页面返回时恢复到之前的播放进度
        if (this._pendingResumeTime && this._pendingResumeTime > 1) {
          try {
            video.currentTime = this._pendingResumeTime
          } catch (e) {}
          this._pendingResumeTime = 0
        }
      })
      video.addEventListener('durationchange', () => {
        this.duration = video.duration || 0
      })
      video.addEventListener('progress', () => {
        try {
          if (video.buffered && video.buffered.length > 0) {
            this.buffered = video.buffered.end(video.buffered.length - 1) || 0
          }
        } catch (e) {}
      })
      const slot = document.getElementById('vmk-video-slot')
      if (slot) slot.appendChild(video)
      this._h5Video = video
      return video
    },
    _ensureH5Video() {
      if (!this._h5Video) return
      if (!this._h5Video.parentNode) {
        const slot = document.getElementById('vmk-video-slot')
        if (slot) slot.appendChild(this._h5Video)
      }
    },
    async loadDetail() {
      this.loading = true
      this.loadingText = '加载详情…'
      try {
        const d = await fetchOnlineDetail(this.vodId, this.siteKey)
        if (d) {
          this.detail = d
          this.playTitle = d.title || this.playTitle
          this.poster = d.cover || this.poster
          const line = this.currentLine
          this.episodes = (line && line.eps) || []
          this.isFavorited = isFavorited(this.vodId, this.siteKey, this.rawUrl)
          // 兜底：URL 未传 contentType 时，根据详情自动识别短剧并修正布局
          if (!this.contentType && d) {
            const detailType = (d.contentType || '') + ''
            const g = (d.genre || d.remarks || d.tag || '') + ''
            if (detailType === 'shorts' || g.indexOf('短剧') > -1) {
              this.contentType = 'shorts'
            }
          }
        } else {
          this.errMsg = '加载详情失败'
        }
      } catch (e) {
        this.errMsg = '加载详情失败'
      } finally {
        this.loading = false
      }
    },
    async loadRecommend() {
      if (this.detail && this.detail.lines && this.detail.lines.length) {
        this.seriesList = this.detail.lines.map((l, i) => ({
          vodId: this.vodId,
          title: this.detail.title,
          cover: this.detail.cover,
          onlineSite: this.siteKey,
          lineIndex: i,
          flag: l.flag
        }))
      }
    },
    switchLine(i) {
      if (i === this.lineIdx || !this.detail || !this.detail.lines) return
      this.lineIdx = i
      const line = this.detail.lines[i]
      this.episodes = (line && line.eps) || []
      this.currentEpIdx = 0
      this._resolved = false
      this.needTapPlay = false
      this.errMsg = ''
      this.playEpisode(0)
    },
    async playEpisode(idx) {
      if (!this.episodes.length || idx < 0 || idx >= this.episodes.length) return
      this.currentEpIdx = idx
      const ep = this.episodes[idx]
      if (!ep || !ep.url) {
        this.errMsg = '选集无效'
        return
      }
      const line = this.currentLine
      const flag = (line && line.flag) || ''
      this.playTitle = ((this.detail && this.detail.title) || '正在播放') + (flag ? ' · ' + flag : '') + ' · ' + ep.name
      await this.$nextTick()
      this.startPlayUrl(ep.url)
    },
    async startPlayUrl(url) {
      if (!url) {
        this.errMsg = '播放地址为空'
        return
      }
      this.loading = true
      this.loadingText = '加载中…'
      this.errMsg = ''
      // 重置进度条
      this.currentTime = 0
      this.duration = 0
      this.buffered = 0
      // 重置自动播放下一集标志位，允许本次播放结束后再次触发
      this._autoNextTriggered = false
      // 重置视频方向检测标志（允许新视频重新检测）
      this._orientationDetected = false
      let m3u8Url = url
      if (!this._isDirectUrl(url) && !this._resolved) {
        this.loadingText = '解析播放地址…'
        try {
          const resolved = await fetchOnlineResolve(url)
          if (resolved) {
            m3u8Url = resolved
            this._resolved = true
          } else {
            this.loading = false
            this.errMsg = '无法解析视频地址，请重试或更换线路'
            return
          }
        } catch (e) {
          this.loading = false
          this.errMsg = '解析失败'
          return
        }
      }
      // 统一使用 H5/HLS 播放方案（App 端 WebView 也支持）
      this._playH5(m3u8Url)
    },
    _playH5(m3u8Url) {
      const proxiedUrl = this._toStreamUrl(m3u8Url)
      let video = this._createH5Video()
      this._ensureH5Video()

      // 成功 play 后的后处理：
      // 1) 如果不是用户手动设的静音，自动解除静音（优先保证有声音）
      // 2) 浏览器强制静音才 needTapPlay
      const afterPlay = (playResult) => {
        if (playResult && typeof playResult.catch === 'function') {
          playResult.catch((e) => {
            if (e && (e.name === 'NotAllowedError' || e.name === 'AbortError')) {
              this.needTapPlay = true
            }
          })
        }
        // 如果 mutedAuto 为 true（表示只是因为 autoplay 策略而静音），
        // 在 play 成功后尝试解除静音（配合 play() 的链式 Promise 或 setTimeout 兜底）
        const tryUnmute = () => {
          if (video && this.mutedAuto && video.muted) {
            video.muted = false
            this.isMuted = false
            this.mutedAuto = false
            // 某些环境需再次 play 才能出声
            video.play().catch(() => {})
          }
        }
        if (playResult && typeof playResult.then === 'function') {
          playResult.then(() => tryUnmute()).catch(() => {})
        } else {
          setTimeout(tryUnmute, 0)
        }
      }

      // 非 m3u8 直接用 video.src 播放
      if (!proxiedUrl.includes('.m3u8')) {
        video.src = proxiedUrl
        this.loading = false
        afterPlay(video.play())
        return
      }

      // m3u8 用 HLS.js 播放
      this._loadHls().then((Hls) => {
        if (!Hls) {
          this.loading = false
          this.errMsg = 'HLS 加载失败'
          return
        }

        // 如果原生支持 HLS（iOS Safari），直接设 src
        if (video.canPlayType('application/vnd.apple.mpegurl')) {
          video.src = proxiedUrl
          this.loading = false
          video.addEventListener('loadedmetadata', () => {
            afterPlay(video.play())
          }, { once: true })
          return
        }

        if (Hls.isSupported()) {
          this.destroyHls()
          video = this._createH5Video()
          this._ensureH5Video()
          // file:// 环境下 Web Worker 不可用，必须禁用
          const isFileProtocol = typeof window !== 'undefined' && window.location && window.location.protocol === 'file:'
          const hls = new Hls({
            enableWorker: !isFileProtocol,
            lowLatencyMode: false,
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            fragLoadingTimeOut: 60000,
            manifestLoadingTimeOut: 30000,
            levelLoadingTimeOut: 30000,
            fragLoadingMaxRetry: 6,
            manifestLoadingMaxRetry: 4,
            levelLoadingMaxRetry: 4
          })
          this._hls = hls
          hls.loadSource(proxiedUrl)
          hls.attachMedia(video)
          hls.on(Hls.Events.MANIFEST_PARSED, () => {
            this.loading = false
            afterPlay(video.play())
          })
          hls.on(Hls.Events.ERROR, (_, data) => {
            console.error('[player] HLS error:', data)
            if (data && data.fatal) {
              if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                hls.startLoad()
              } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                hls.recoverMediaError()
              } else {
                this.loading = false
                this.errMsg = '播放错误: ' + (data.details || 'unknown')
              }
            }
          })
        } else {
          this.loading = false
          this.errMsg = '当前浏览器不支持 HLS 播放'
        }
      }).catch((err) => {
        console.error('[player] HLS.js load failed:', err)
        this.loading = false
        this.errMsg = '视频解码器加载失败'
      })
    },
    _toStreamUrl(url) {
      // 非 m3u8/video 格式直接返回
      if (/\.(mp4|flv|ts|mov|mkv|avi|webm)(\?|#|$)/i.test(url)) return url
      // 运行时检测：file:// 环境（App WebView）用远程代理，http(s):// 环境用本地代理
      const REMOTE = 'https://1302446649-7terr1rghd.ap-guangzhou.tencentscf.com'
      let base
      if (typeof window !== 'undefined' && window.location && window.location.protocol === 'file:') {
        // App WebView (file://) — 直连远程流代理
        base = REMOTE
      } else if (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost') {
        // 本地开发 — 走 Vite 代理
        base = '/__pyapi'
      } else {
        // H5 部署 — 直连远程
        base = REMOTE
      }
      return base + '/api/stream?url=' + encodeURIComponent(url) + '&prefix=' + encodeURIComponent(base)
    },
    _loadHls() {
      // file:// 环境（App WebView）下 import() 不可用，优先用 script 标签加载
      if (typeof window !== 'undefined' && window.location && window.location.protocol === 'file:') {
        return new Promise((resolve, reject) => {
          if (window.Hls) return resolve(window.Hls)
          const s = document.createElement('script')
          s.src = './static/hls.min.js'
          s.onload = () => {
            if (window.Hls) resolve(window.Hls)
            else reject(new Error('Hls not found after load'))
          }
          s.onerror = () => reject(new Error('hls.js script load failed'))
          document.head.appendChild(s)
        })
      }
      // 正常 web 环境用 ES module
      return import('hls.js').then((m) => m.default || m.Hls || window.Hls).catch(() => {
        return new Promise((resolve, reject) => {
          if (window.Hls) return resolve(window.Hls)
          const s = document.createElement('script')
          s.src = './static/hls.min.js'
          s.onload = () => resolve(window.Hls)
          s.onerror = () => reject(new Error('hls.js load failed'))
          document.head.appendChild(s)
        })
      })
    },
    destroyHls() {
      if (this._hls) {
        try { this._hls.destroy() } catch (e) {}
        this._hls = null
      }
      if (this._h5Video) {
        if (this._h5Video.parentNode) {
          this._h5Video.parentNode.removeChild(this._h5Video)
        }
        this._h5Video = null
      }
    },
    // 息屏亮屏后恢复播放（video 元素仍在，只是被 WebView 暂停了）
    _resumePlayback() {
      const v = this._h5Video
      if (!v) {
        // video 已被销毁（onHide 触发了 destroyHls），需要重建
        if (this.rawUrl || (this.vodId && this.episodes.length)) {
          this._pendingResumeTime = this.currentTime || 0
          this._pendingAutoPlay = true
          this._resolved = false
          if (this.vodId && this.episodes.length) {
            this.playEpisode(this.currentEpIdx)
          } else if (this.rawUrl) {
            this.startPlayUrl(this.rawUrl)
          }
        }
        return
      }
      // video 元素还在，直接恢复播放
      // HLS 长时间暂停后可能缓冲过期，先尝试 play，失败则重新加载
      const tryPlay = () => {
        v.play().catch((err) => {
          // 自动播放被浏览器策略阻止，显示点击播放按钮
          if (err && (err.name === 'NotAllowedError' || err.name === 'AbortError')) {
            this.needTapPlay = true
            this.isPlaying = false
            return
          }
          // 其它错误（如缓冲过期）：尝试从当前位置重新加载
          if (this._hls) {
            try { this._hls.startLoad(v.currentTime || 0) } catch (e) {}
            v.play().catch(() => {
              this.needTapPlay = true
              this.isPlaying = false
            })
          }
        })
      }
      tryPlay()
    },
    selectEpisode(i) {
      if (i === this.currentEpIdx) {
        this.showPanel = false
        return
      }
      this._resolved = false
      this.needTapPlay = false
      this.errMsg = ''
      this.playEpisode(i)
      this.showPanel = false
    },
    // 播完自动播放下一集（已是最后一集则停留）
    _autoPlayNext() {
      if (this._autoNextTriggered) return
      this._autoNextTriggered = true
      if (!this.episodes.length) return
      const next = this.currentEpIdx + 1
      if (next >= this.episodes.length) {
        // 最后一集，不自动播放
        this.isPlaying = false
        return
      }
      this._resolved = false
      this.needTapPlay = false
      this.errMsg = ''
      // 自动续播时取消静音状态，让下一集正常发声
      const video = this._h5Video
      if (video && video.muted) {
        video.muted = false
        this.isMuted = false
        this.mutedAuto = false
      }
      this.playEpisode(next)
    },
    // timeupdate 检测接近结尾，提前触发自动播放下一集（ended 在 HLS 暂停/恢复后常不触发）
    _checkEndedAutoNext() {
      const video = this._h5Video
      if (!video) return
      // 需要有效时长且非拖拽中
      if (!this.duration || this.duration <= 0 || this._seeking) return
      const remaining = this.duration - (video.currentTime || 0)
      // 剩余不足 0.5 秒视为播完（兼容 HLS 直播流时长不准的情况）
      if (remaining < 0.5 && video.currentTime > 0) {
        this._autoPlayNext()
      }
    },
    onLoaded() {
      this.loading = false
      this.showTopBar = true
    },
    onVideoError(e) {
      this.loading = false
      this.errMsg = '播放失败'
    },
    tapToPlay() {
      this.needTapPlay = false
      const video = this._h5Video
      if (!video) return
      video.muted = false
      this.isMuted = false
      this.mutedAuto = false
      video.play().catch(() => {
        video.muted = true
        this.isMuted = true
        this.mutedAuto = true
        video.play().catch(() => {})
      })
    },
    retry() {
      this.errMsg = ''
      this.needTapPlay = false
      this._resolved = false
      if (this.vodId && this.episodes.length) {
        this.playEpisode(this.currentEpIdx)
      } else if (this.rawUrl) {
        this.startPlayUrl(this.rawUrl)
      }
    },
    goBack() {
      const pages = getCurrentPages()
      if (pages.length > 1) uni.navigateBack()
      else uni.redirectTo({ url: '/pages/home/home' })
    }
  }
}
</script>

<style scoped>
.player-page {
  position: fixed;
  inset: 0;
  background-color: #000;
  overflow: hidden;
}
.video-bg {
  position: absolute;
  inset: 0;
  background-color: #000;
}
.video-el {
  width: 100%;
  height: 100%;
  background-color: #000;
  object-fit: contain;
}
.video-el-shorts {
  object-fit: cover;
}

/* ================ 电影/电视剧模式：视频区占页面高度 1/3 + 下方选集 ================ */
.player-page.movie-mode {
  display: flex;
  flex-direction: column;
  background-color: #1a1a1a;
}
.movie-mode .video-bg {
  position: relative;
  width: 100%;
  height: 33.3333vh; /* 占页面高度 1/3 */
  flex-shrink: 0;
}
.movie-mode .video-el {
  height: 100%;
}

/* ================ CSS 全屏模式（兼容 Android WebView） ================ */
.player-page.fs-active {
  display: block;
}
.player-page.fs-active .video-bg {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  background-color: #000;
}
/* 电影/电视剧进入横屏全屏时：video 的 object-fit 改为 contain，视频按比例真正铺满 */
.player-page.movie-mode.fs-active .video-el {
  object-fit: contain !important;
  width: 100%;
  height: 100%;
}
.player-page.fs-active .movie-video-controls {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  /* 横屏全屏时控制层要覆盖整个屏幕（不是原来的 1/3 高度） */
  height: 100vh;
  height: 100dvh;
  z-index: 10000;
}
/* 横屏全屏隐藏右侧换集提示（横屏时用选集栏更直观） */
.player-page.fs-active .movie-swipe-hint {
  display: none !important;
}
/* 全屏时隐藏简介/选集/系列剧等内容区、短剧底部选集栏、面板 */
.player-page.fs-active .movie-info-area,
.player-page.fs-active .shorts-bottom-bar,
.player-page.fs-active .shorts-panel,
.player-page.fs-active .panel-mask {
  display: none !important;
}
/* 全屏时面板 Tab、选集、内容区全部隐藏，确保只剩视频 + 控制层 */
.player-page.fs-active .movie-info-tabs,
.player-page.fs-active .movie-info-panes {
  display: none !important;
}
/* 横屏时底部控制栏、顶栏在横屏时稍微加大点击区域，避免误触 */
.player-page.movie-mode.fs-active .movie-bottom-bar {
  padding-left: calc(24rpx + env(safe-area-inset-left));
  padding-right: calc(24rpx + env(safe-area-inset-right));
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
}
.player-page.movie-mode.fs-active .movie-top-bar {
  padding-left: calc(24rpx + env(safe-area-inset-left));
  padding-right: calc(24rpx + env(safe-area-inset-right));
  padding-top: calc(env(safe-area-inset-top));
  height: calc(88rpx + env(safe-area-inset-top));
}

/* ================ 电影/电视剧视频控制层（叠加在 1/3 视频上） ================ */
.movie-video-controls {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 33.3333vh;
  z-index: 15;
  overflow: hidden;
}

/* 顶部栏（叠加在视频上，带渐变背景） */
.movie-video-controls .movie-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  background: linear-gradient(180deg, rgba(0,0,0,0.75) 0%, transparent 100%);
  z-index: 20;
}

/* 中央叠加层：暂停时大按钮，播放时集数信息 */
.movie-center-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12;
  pointer-events: none;
}
.movie-center-play-btn {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.55);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}
/* 电影/电视剧：视频区右侧上下滑动换集提示 */
.movie-swipe-hint {
  position: absolute;
  right: 16rpx;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  padding: 14rpx 8rpx;
  border-radius: 9999rpx;
  background-color: rgba(0, 0, 0, 0.35);
  z-index: 13;
  pointer-events: none;
}
.movie-swipe-arrow {
  opacity: 0.85;
}
.movie-swipe-arrow.disabled {
  opacity: 0.25;
}
.movie-swipe-ep {
  font-size: 20rpx;
  color: #FFFFFF;
  line-height: 1;
}
.movie-center-episode {
  pointer-events: none;
}
.movie-center-ep-text {
  font-size: 30rpx;
  color: #FFFFFF;
  font-weight: 600;
  text-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.6);
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 底部控制栏（叠加在视频底部） */
.movie-bottom-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 80rpx;
  display: flex;
  align-items: center;
  padding: 0 16rpx;
  gap: 10rpx;
  background: linear-gradient(0deg, rgba(0,0,0,0.75) 0%, transparent 100%);
  z-index: 20;
}
.movie-bottom-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.movie-bottom-time {
  font-size: 22rpx;
  color: #FFFFFF;
  font-variant-numeric: tabular-nums;
  min-width: 72rpx;
  text-align: center;
  flex-shrink: 0;
}
.movie-bottom-speed {
  font-size: 26rpx;
  font-weight: 600;
  color: #FFFFFF;
  padding: 6rpx 14rpx;
  border-radius: 8rpx;
  background-color: rgba(255, 255, 255, 0.15);
}
.movie-progress-track {
  position: relative;
  flex: 1;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.25);
  min-width: 40rpx;
}
.movie-progress-track .progress-buffered {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.4);
  transition: width 0.2s;
}
.movie-progress-track .progress-played {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: #FFB800;
}
.movie-progress-track .progress-thumb {
  position: absolute;
  top: 50%;
  width: 22rpx;
  height: 22rpx;
  border-radius: 50%;
  background-color: #FFFFFF;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 6rpx rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

/* 通用遮罩层 */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24rpx;
  z-index: 5;
}
.loading-overlay { background-color: rgba(0, 0, 0, 0.5); }
.error-overlay { background-color: rgba(0, 0, 0, 0.85); }
.tap-play-overlay {
  background-color: rgba(0, 0, 0, 0.5);
  cursor: pointer;
}
.spinner {
  width: 72rpx;
  height: 72rpx;
  border: 6rpx solid rgba(255, 255, 255, 0.2);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.overlay-text {
  font-size: 26rpx;
  color: #FFFFFF;
  text-align: center;
}
.error-text { color: #FF6B6B; }
.retry-btn {
  height: 72rpx;
  padding: 0 48rpx;
  border-radius: 36rpx;
  background-color: #2B7FFF;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.retry-text { font-size: 26rpx; color: #FFFFFF; font-weight: 600; }
.tap-play-icon {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding-left: 10rpx;
}

/* ================ H5 自定义进度条 ================ */
.player-progress {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 64rpx;
  display: flex;
  align-items: center;
  padding: 0 20rpx;
  padding-bottom: calc(8rpx + env(safe-area-inset-bottom));
  background: linear-gradient(0deg, rgba(0,0,0,0.7) 0%, transparent 100%);
  z-index: 25;
  gap: 16rpx;
}
/* 短剧模式：进度条避开底部选集栏 */
.shorts-progress {
  bottom: calc(200rpx + env(safe-area-inset-bottom));
  background: none;
  padding-bottom: 0;
}
.progress-time {
  font-size: 22rpx;
  color: #FFFFFF;
  font-variant-numeric: tabular-nums;
  min-width: 64rpx;
  text-align: center;
  flex-shrink: 0;
}
.progress-track {
  position: relative;
  flex: 1;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.25);
  cursor: pointer;
}
.progress-buffered {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.4);
  transition: width 0.2s;
}
.progress-played {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 3rpx;
  background-color: #FFB800;
}
.progress-thumb {
  position: absolute;
  top: 50%;
  width: 22rpx;
  height: 22rpx;
  border-radius: 50%;
  background-color: #FFFFFF;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 6rpx rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

/* ================ 电影/电视剧布局 ================ */
/* 注：顶部栏、中央叠加层、底部控制栏样式见上方 “电影/电视剧视频控制层” 区块 */

.top-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.top-title-wrap {
  flex: 1;
  margin: 0 16rpx;
  text-align: center;
}
.top-title {
  font-size: 32rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.speed-btn-text {
  font-size: 28rpx;
  color: #FFFFFF;
  font-weight: 500;
}

/* 内容区（视频下方，默认展开） */
.movie-info-area {
  position: absolute;
  top: 33.3333vh;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background-color: #0D0D12;
  overflow: hidden;
}
.movie-info-header {
  display: flex;
  gap: 20rpx;
  padding: 24rpx 32rpx 16rpx;
  flex-shrink: 0;
}
.movie-info-cover {
  width: 120rpx;
  height: 160rpx;
  border-radius: 12rpx;
  flex-shrink: 0;
  background-color: rgba(255, 255, 255, 0.05);
}
.movie-info-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}
.movie-info-title-row {
  display: flex;
  align-items: center;
}
.movie-info-title {
  font-size: 34rpx;
  font-weight: 700;
  color: #FFFFFF;
  flex: 1;
  min-width: 0;
}
.movie-info-score {
  font-size: 28rpx;
  font-weight: 700;
  color: #FFB800;
  margin-left: 12rpx;
  flex-shrink: 0;
}
.movie-info-subtitle {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.6);
}
.movie-info-actions {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-top: 4rpx;
}
.movie-info-fav {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 24rpx;
  border-radius: 9999rpx;
  background-color: rgba(255, 255, 255, 0.1);
}
.movie-info-fav-text {
  font-size: 24rpx;
  color: #FFFFFF;
}
.movie-info-tabs {
  display: flex;
  gap: 0;
  padding: 0 32rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}
.movie-info-tab {
  padding: 16rpx 0;
  margin-right: 48rpx;
}
.movie-info-tab.active {
  border-bottom: 4rpx solid #FFB800;
}
.movie-info-tab-text {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.5);
}
.movie-info-tab.active .movie-info-tab-text {
  color: #FFFFFF;
  font-weight: 600;
}
.movie-info-content {
  flex: 1;
  overflow-y: auto;
  padding: 24rpx 32rpx;
}
/* 简介 tab 内部的 header：抵消 scroll-view 的 padding 保持原视觉效果 */
.movie-info-content .movie-info-header {
  padding: 0 0 16rpx;
}
.movie-info-spacer {
  height: calc(32rpx + env(safe-area-inset-bottom));
}
.work-score {
  font-size: 28rpx;
  font-weight: 700;
  color: #FFB800;
  margin-left: 12rpx;
}

/* 面板内演职信息 */
.panel-credits {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-bottom: 24rpx;
}
.panel-credit-line {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

/* 面板内播放线路 */
.panel-lines {
  margin-top: 32rpx;
}
.panel-lines-title {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 16rpx;
}
.panel-lines-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.panel-line-chip {
  height: 56rpx;
  padding: 0 28rpx;
  border-radius: 9999rpx;
  background-color: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
}
.panel-line-chip.active {
  background-color: #FFB800;
}
.panel-line-text {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}
.panel-line-chip.active .panel-line-text {
  color: #1C1C1E;
  font-weight: 600;
}

/* ================ 短剧布局（竖屏风格） ================ */
.shorts-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 140rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  background: linear-gradient(180deg, rgba(0,0,0,0.7) 0%, transparent 100%);
  z-index: 20;
}
.shorts-top-btn {
  width: 72rpx;
  height: 72rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.4);
  flex-shrink: 0;
}
.shorts-top-info {
  flex: 1;
  margin: 0 20rpx;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}
.shorts-top-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.shorts-top-sub {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.7);
}

/* 上下滑动换集提示 */
.swipe-hint {
  position: absolute;
  left: 28rpx;
  top: 50%;
  transform: translateY(-50%);
  z-index: 15;
  pointer-events: none;
}
.swipe-hint-arrows {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16rpx;
  padding: 20rpx 14rpx;
  border-radius: 9999px;
  background-color: rgba(0, 0, 0, 0.32);
  backdrop-filter: blur(4px);
}
.swipe-hint-arrow {
  width: 48rpx;
  height: 48rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.14);
}
.swipe-hint-arrow.disabled {
  opacity: 0.3;
}
.swipe-hint-ep {
  font-size: 20rpx;
  color: #FFFFFF;
  writing-mode: vertical-rl;
  letter-spacing: 1rpx;
  opacity: 0.85;
}

/* 顶部右侧操作区 */
.shorts-top-actions {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-shrink: 0;
}

/* 中央播放按钮叠加层 */
.shorts-center-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12;
  pointer-events: none;
}
.shorts-center-play-btn {
  width: 140rpx;
  height: 140rpx;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.55);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

/* 底部控制栏（参考电影播放器） */
.shorts-control-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(160rpx + env(safe-area-inset-bottom) + 5px);
  height: 80rpx;
  display: flex;
  align-items: center;
  padding: 0 16rpx;
  gap: 10rpx;
  background: linear-gradient(0deg, rgba(0,0,0,0.6) 0%, transparent 100%);
  z-index: 20;
}
.shorts-ctrl-btn {
  width: 64rpx;
  height: 64rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.shorts-ctrl-time {
  font-size: 22rpx;
  color: #FFFFFF;
  font-variant-numeric: tabular-nums;
  min-width: 72rpx;
  text-align: center;
  flex-shrink: 0;
}
.shorts-ctrl-speed {
  font-size: 26rpx;
  font-weight: 600;
  color: #FFFFFF;
  padding: 6rpx 14rpx;
  border-radius: 8rpx;
  background-color: rgba(255, 255, 255, 0.15);
}
.shorts-progress-track {
  position: relative;
  flex: 1;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: rgba(255, 255, 255, 0.25);
  min-width: 40rpx;
}

/* 底部选集栏 */
.shorts-bottom-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 32rpx 24rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  background: linear-gradient(0deg, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 70%, transparent 100%);
  z-index: 20;
}
.shorts-ep-scroll {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}
.shorts-ep-info {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.shorts-ep-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #FFFFFF;
}
.shorts-ep-divider {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.5);
}
.shorts-ep-status {
  font-size: 26rpx;
  color: #FFB800;
  font-weight: 500;
}
.shorts-ep-count {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.7);
}
.shorts-ep-strip {
  white-space: nowrap;
  margin: 0 -24rpx;
  padding: 0 24rpx;
}
.shorts-ep-list {
  display: inline-flex;
  gap: 16rpx;
  padding-right: 120rpx;
}
.shorts-ep-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112rpx;
  height: 72rpx;
  padding: 0 24rpx;
  border-radius: 36rpx;
  background-color: rgba(255, 255, 255, 0.12);
  flex-shrink: 0;
}
.shorts-ep-chip.active {
  background-color: #FFB800;
}
.shorts-ep-chip-name {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}
.shorts-ep-chip.active .shorts-ep-chip-name {
  color: #1C1C1E;
  font-weight: 700;
}
.shorts-ep-expand {
  position: absolute;
  right: 24rpx;
  bottom: calc(32rpx + env(safe-area-inset-bottom));
  height: 72rpx;
  padding: 0 20rpx;
  display: inline-flex;
  align-items: center;
  gap: 4rpx;
  border-radius: 36rpx;
  background-color: rgba(255, 184, 0, 0.9);
}
.shorts-ep-expand-text {
  font-size: 26rpx;
  color: #1C1C1E;
  font-weight: 600;
}

/* ================ 底部弹出面板（共用） ================ */
.panel-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.6);
  z-index: 30;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.panel {
  background-color: #1C1C1E;
  border-radius: 32rpx 32rpx 0 0;
  max-height: 75vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.panel-handle {
  width: 64rpx;
  height: 8rpx;
  border-radius: 4rpx;
  background-color: rgba(255, 255, 255, 0.2);
  margin: 16rpx auto 0;
}

.work-info {
  display: flex;
  gap: 20rpx;
  padding: 24rpx 32rpx 20rpx;
}
.work-cover {
  width: 120rpx;
  height: 160rpx;
  border-radius: 12rpx;
  background-color: #333;
  flex-shrink: 0;
}
.work-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8rpx;
}
.work-title-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.work-title {
  font-size: 34rpx;
  font-weight: 700;
  color: #FFFFFF;
  flex: 1;
}
.work-subtitle {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.5);
}
.work-desc {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.ellipsis-2 {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.panel-tabs {
  display: flex;
  gap: 48rpx;
  padding: 0 32rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.1);
}
.panel-tab {
  padding: 20rpx 0;
  position: relative;
}
.panel-tab.active .panel-tab-text {
  color: #FFFFFF;
  font-weight: 600;
}
.panel-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  border-radius: 3rpx;
  background-color: #FFB800;
}
.panel-tab-text {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.5);
}

.panel-content {
  flex: 1;
  max-height: 50vh;
  padding: 24rpx 32rpx;
}
.intro-text {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}
.ep-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.ep-item {
  width: calc((100% - 80rpx) / 6);
  height: 80rpx;
  border-radius: 12rpx;
  background-color: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ep-item.active {
  background-color: #FFB800;
}
.ep-item .ep-name {
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.8);
}
.ep-item.active .ep-name {
  color: #1C1C1E;
  font-weight: 700;
}

.series-list {
  display: flex;
  flex-wrap: wrap;
  gap: 24rpx;
}
.series-item {
  width: calc((100% - 48rpx) / 3);
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.series-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 12rpx;
  background-color: #333;
}
.series-title {
  font-size: 26rpx;
  font-weight: 600;
  line-height: 1.3;
  color: rgba(255, 255, 255, 0.9);
}
.series-tag {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.5);
}

.panel-bottom-spacer {
  height: 16rpx;
}

.favorite-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 24rpx 32rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.1);
  background-color: #1C1C1E;
}
.favorite-text {
  font-size: 30rpx;
  font-weight: 600;
  color: #FFB800;
}

/* Modal */
.modal-mask {
  position: absolute;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.7);
  z-index: 40;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
.modal-list {
  background-color: #2C2C2E;
  border-radius: 24rpx;
  min-width: 300rpx;
  overflow: hidden;
}
.modal-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 48rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.08);
}
.modal-item:last-child { border-bottom: none; }
.modal-item.active .modal-item-text { color: #FFB800; }
.modal-item-text {
  font-size: 30rpx;
  color: #FFFFFF;
}
.modal-check {
  font-size: 28rpx;
  color: #FFB800;
}
</style>
