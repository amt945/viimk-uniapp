<script>
export default {
  onLaunch() {
    // #ifdef APP-PLUS
    // App 端沉浸式状态栏
    plus.navigator.setStatusBarStyle('light')
    plus.navigator.setFullscreen(false)
    // #endif
  },
  onShow() {},
  onHide() {}
}
</script>

<style lang="scss">
/* ===== VIIMK Design Tokens (CSS Variables) ===== */
page {
  /* 颜色 */
  --vmk-primary: #2B7FFF;
  --vmk-primary-dark: #1A6DE5;
  --vmk-background: #0D0D12;
  --vmk-card: #18181F;
  --vmk-foreground: #FFFFFF;
  --vmk-muted: #9CA3AF;
  --vmk-border: #2A2A35;
  --vmk-muted-bg: #23232B;
  --vmk-success: #22C55E;
  --vmk-warning: #F59E0B;
  --vmk-error: #EF4444;
  /* 圆角 */
  --vmk-radius-sm: 4px;
  --vmk-radius-md: 8px;
  --vmk-radius-lg: 12px;
  --vmk-radius-xl: 16px;
  --vmk-radius-full: 9999px;
  /* 字号 */
  --vmk-text-xs: 22rpx;
  --vmk-text-sm: 24rpx;
  --vmk-text-base: 28rpx;
  --vmk-text-lg: 32rpx;
  --vmk-text-xl: 36rpx;
  --vmk-text-2xl: 44rpx;
  /* 布局 */
  --vmk-page-padding: 32rpx;
  --vmk-gap: 24rpx;
  --vmk-status-bar: 88rpx;
  --vmk-bottom-nav: 112rpx;

  background-color: var(--vmk-background);
  color: var(--vmk-foreground);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: var(--vmk-text-base);
  -webkit-font-smoothing: antialiased;
}

/* ===== 全局重置 ===== */
view, text, image, scroll-view, swiper, button, input, textarea {
  box-sizing: border-box;
}

/* 隐藏滚动条 */
::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

/* ===== 通用工具类 ===== */
.vmk-app-shell {
  min-height: 100vh;
  background-color: var(--vmk-background);
  position: relative;
  overflow-x: hidden;
}

.vmk-status-bar {
  height: var(--vmk-status-bar);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--vmk-page-padding);
  font-size: var(--vmk-text-sm);
  font-weight: 600;
  color: var(--vmk-foreground);
  /* #ifdef APP-PLUS || MP */
  padding-top: var(--vmk-status-bar-safe);
  /* #endif */
}

.vmk-page-content {
  padding: 0 var(--vmk-page-padding);
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}

.vmk-card {
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  overflow: hidden;
}

.vmk-section-title {
  font-size: var(--vmk-text-lg);
  font-weight: 700;
  color: var(--vmk-foreground);
}

.vmk-text-muted {
  color: var(--vmk-muted);
}

.vmk-chip {
  display: inline-flex;
  align-items: center;
  height: 56rpx;
  padding: 0 28rpx;
  border-radius: var(--vmk-radius-full);
  font-size: var(--vmk-text-sm);
  background-color: var(--vmk-muted-bg);
  color: var(--vmk-foreground);
  border: 1px solid var(--vmk-border);
  white-space: nowrap;
  flex-shrink: 0;
}

.vmk-chip.active {
  background-color: var(--vmk-primary);
  border-color: var(--vmk-primary);
}

.vmk-btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12rpx;
  height: 80rpx;
  padding: 0 40rpx;
  border-radius: var(--vmk-radius-xl);
  background-color: var(--vmk-primary);
  color: #fff;
  font-size: var(--vmk-text-base);
  font-weight: 600;
  border: none;
  line-height: 1;
}

.vmk-btn-primary::after {
  border: none;
}

.vmk-btn-icon {
  width: 80rpx;
  height: 80rpx;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--vmk-radius-full);
  background-color: var(--vmk-card);
  color: var(--vmk-foreground);
  border: 1px solid var(--vmk-border);
  padding: 0;
}

.vmk-btn-icon::after {
  border: none;
}

/* 隐藏滚动条 (小程序/app) */
.no-scrollbar {
  /* #ifdef H5 */
  scrollbar-width: none;
  /* #endif */
}

/* 单行省略 */
.ellipsis {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* 两行省略 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.line-clamp-4 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}

/* flex 工具 */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.flex-1 { flex: 1; }
.shrink-0 { flex-shrink: 0; }
.min-w-0 { min-width: 0; }
.gap-2 { gap: 8rpx; }
.gap-3 { gap: 12rpx; }
.gap-4 { gap: 16rpx; }
</style>
