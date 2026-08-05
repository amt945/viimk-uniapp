<template>
  <view class="splash">
    <view class="splash-stage">
      <view class="splash-logo-card">
        <text class="splash-wordmark">VIIMK</text>
      </view>
      <text class="splash-tagline">看见每一部热爱</text>
      <view class="splash-loader">
        <view class="splash-loader-fill"></view>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'Splash',
  data() {
    return { timer: null }
  },
  onLoad() {
    // 2 秒后进入首页
    this.timer = setTimeout(() => {
      uni.redirectTo({ url: '/pages/home/home' })
    }, 2000)
  },
  onUnload() {
    if (this.timer) clearTimeout(this.timer)
  }
}
</script>

<style scoped>
.splash {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(180deg, #2B7FFF 0%, #1A6DE5 100%);
  display: flex;
  justify-content: center;
}

.splash-stage {
  position: relative;
  width: 100%;
  min-height: 100vh;
}

.splash-logo-card {
  position: absolute;
  top: 45%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 192rpx;
  height: 192rpx;
  border-radius: 32rpx;
  background-color: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 80rpx rgba(255, 255, 255, 0.25);
}

.splash-wordmark {
  font-size: 56rpx;
  line-height: 1.2;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: -1rpx;
}

.splash-tagline {
  position: absolute;
  top: calc(45% + 96rpx + 48rpx);
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--vmk-text-base);
  line-height: 1.4;
  color: #FFFFFF;
  opacity: 0.9;
  white-space: nowrap;
}

.splash-loader {
  position: absolute;
  left: 50%;
  bottom: 192rpx;
  transform: translateX(-50%);
  width: 240rpx;
  height: 4rpx;
  border-radius: 9999rpx;
  background-color: rgba(255, 255, 255, 0.3);
  overflow: hidden;
}

.splash-loader-fill {
  width: 60%;
  height: 100%;
  background-color: #FFFFFF;
  border-radius: 9999rpx;
  animation: vmk-splash-loading 1.8s ease-in-out infinite;
}

@keyframes vmk-splash-loading {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(40%); }
  100% { transform: translateX(100%); }
}
</style>
