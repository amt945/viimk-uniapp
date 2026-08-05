<template>
  <view class="app-shell">
    <StatusBar />

    <!-- Header -->
    <view class="header">
      <view class="icon-btn" @tap="goBack">
        <VmkIcon name="chevron-left" :size="40" color="#FFFFFF" />
      </view>
      <text class="header-title">隐私政策</text>
      <view class="icon-btn"></view>
    </view>

    <scroll-view class="page-content" scroll-y :show-scrollbar="false">
      <view class="card">
        <text class="update-time">更新日期：2026 年 8 月 5 日</text>
        <text class="section-title">一、引言</text>
        <text class="section-text">VIIMK（以下简称"本应用"）非常重视您的隐私。本政策说明本应用在您使用过程中收集、使用、存储和保护您个人信息的方式。</text>

        <text class="section-title">二、我们收集的信息</text>
        <text class="section-text">1. 本地存储信息：您的观看历史、收藏记录保存在本地设备，不会上传到服务器。</text>
        <text class="section-text">2. 使用数据：本应用不主动收集您的设备标识、位置信息或使用行为数据。</text>
        <text class="section-text">3. 网络请求：视频检索、播放请求会发送到本应用后端及第三方采集站接口，仅包含搜索关键词和视频 ID，不包含个人身份信息。</text>

        <text class="section-title">三、信息使用</text>
        <text class="section-text">本应用收集的信息仅用于提供视频检索、播放服务及改善用户体验，不会用于商业营销或出售给第三方。</text>

        <text class="section-title">四、信息存储</text>
        <text class="section-text">1. 观看历史和收藏记录存储在您的本地设备，卸载本应用后即被清除。</text>
        <text class="section-text">2. 服务器不存储您的个人信息，仅作为视频接口代理转发请求。</text>

        <text class="section-title">五、第三方服务</text>
        <text class="section-text">本应用的视频内容来源于第三方采集站，您在播放视频时会直接或间接访问这些第三方服务。本应用不对第三方的隐私政策负责，建议您查阅相关第三方的隐私条款。</text>

        <text class="section-title">六、信息保护</text>
        <text class="section-text">本应用采取合理的技术措施保护您的信息，但无法保证绝对安全。因不可抗力或第三方原因导致的信息泄露，本应用不承担责任。</text>

        <text class="section-title">七、未成年人保护</text>
        <text class="section-text">本应用不针对未成年人，未成年人应在监护人指导下使用。若发现未成年人不当使用，请及时制止。</text>

        <text class="section-title">八、政策变更</text>
        <text class="section-text">本应用有权根据需要修改本政策，修改后的政策自发布之日起生效。继续使用本应用即视为您同意修改后的政策。</text>

        <text class="section-title">九、联系我们</text>
        <text class="section-text">如对本政策有任何疑问，可通过"关于"页面的微信号联系我们。</text>
      </view>
      <view class="bottom-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import StatusBar from '@/components/StatusBar.vue'
import VmkIcon from '@/components/VmkIcon.vue'

export default {
  name: 'Privacy',
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
