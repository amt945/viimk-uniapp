<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">用户协议</text>
      <view class="icon-btn"></view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <view class="card">
        <text class="update-time">更新日期：2026 年 8 月 5 日</text>
        <text class="section-title">一、服务说明</text>
        <text class="section-text">欢迎使用 VIIMK（以下简称"本应用"）。本应用是一款专注于优质短剧与影视内容的流媒体应用，为用户提供视频检索、播放及相关服务。使用本应用即表示您同意本协议全部条款。</text>

        <text class="section-title">二、用户行为规范</text>
        <text class="section-text">1. 您不得利用本应用从事任何违反法律法规的活动，包括但不限于传播违法信息、侵犯他人合法权益等。</text>
        <text class="section-text">2. 您不得对本应用进行反向工程、反编译、破解或修改，亦不得干扰本应用的正常运行。</text>
        <text class="section-text">3. 您不得以任何方式批量抓取、复制本应用的内容用于商业用途。</text>

        <text class="section-title">三、内容来源</text>
        <text class="section-text">本应用的视频内容来源于公开的第三方采集站接口，本应用不对内容的版权归属作出承诺。如内容侵犯您的合法权益，请联系我们，我们将在核实后及时处理。</text>

        <text class="section-title">四、知识产权</text>
        <text class="section-text">本应用的软件代码、界面设计、图标、logo 等知识产权归本应用所有，未经书面授权不得复制、传播或商用。</text>

        <text class="section-title">五、免责声明</text>
        <text class="section-text">1. 本应用不保证服务持续可用，因网络、设备、第三方接口等因素导致的服务中断，本应用不承担责任。</text>
        <text class="section-text">2. 您使用本应用所产生的任何直接或间接损失，本应用不承担责任。</text>

        <text class="section-title">六、协议变更</text>
        <text class="section-text">本应用有权根据需要修改本协议，修改后的协议自发布之日起生效。继续使用本应用即视为您同意修改后的协议。</text>

        <text class="section-title">七、联系方式</text>
        <text class="section-text">如对本协议有任何疑问，可通过"关于"页面的微信号联系我们。</text>
      </view>
      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'

export default {
  name: 'Agreement',
  components: { StatusBar, VmkIcon },
  methods: {
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
  min-height: 100vh;
  background-color: var(--vmk-background);
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 24rpx;
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
  flex: 1;
  padding: 32rpx;
  padding-bottom: calc(var(--vmk-bottom-nav) + 32rpx);
}

.card {
  background-color: var(--vmk-card);
  border-radius: var(--vmk-radius-lg);
  padding: 40rpx 32rpx;
  display: flex;
  flex-direction: column;
}

.update-time {
  font-size: var(--vmk-text-xs);
  color: var(--vmk-muted);
  margin-bottom: 32rpx;
}

.section-title {
  font-size: var(--vmk-text-base);
  font-weight: 600;
  color: var(--vmk-foreground);
  margin-top: 24rpx;
  margin-bottom: 12rpx;
}

.section-title:first-of-type {
  margin-top: 0;
}

.section-text {
  font-size: var(--vmk-text-sm);
  line-height: 1.8;
  color: var(--vmk-muted);
  margin-bottom: 8rpx;
}

.bottom-spacer {
  height: 32rpx;
}
</style>
