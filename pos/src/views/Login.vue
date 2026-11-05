<template>
  <div class="login-page">
    <!-- 品牌区：Logo + 系统名 -->
    <div class="brand">
      <div class="logo">衡</div>
      <h1 class="sys-name">鲜衡 POS</h1>
      <p class="sys-desc">电子秤收银终端 · 生鲜零售</p>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card">
      <el-form @submit.prevent="doLogin">
        <el-form-item>
          <el-input
            v-model="form.username"
            size="large"
            placeholder="收银员工号 / 姓名"
            clearable
            @keyup.enter="doLogin"
          >
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            show-password
            placeholder="登录密码"
            @keyup.enter="doLogin"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" class="login-btn" @click="doLogin">登 录</el-button>
      </el-form>
    </div>

    <!-- 收银员快捷选择区：点击头像一键登录 -->
    <div class="quick-block">
      <div class="quick-title">快捷登录</div>
      <div class="quick-list">
        <button
          v-for="c in cashiers"
          :key="c.id"
          class="cashier-btn"
          @click="quickLogin(c)"
        >
          <span class="avatar">{{ c.avatar }}</span>
          <span class="cashier-name">{{ c.name }}</span>
          <span class="cashier-no num">{{ c.no }}</span>
        </button>
      </div>
    </div>

    <!-- 底部版本信息 -->
    <div class="footer">鲜衡 POS v0.1 演示版</div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { usePosStore } from '../stores/posStore'

const router = useRouter()
const store = usePosStore()

// 登录表单数据（演示：任意输入均可登录）
const form = reactive({ username: '', password: '' })

// 快捷登录收银员列表（模拟数据）
const cashiers = [
  { id: 1, no: 'A1001', name: '收银员 小李', avatar: '🍎' },
  { id: 2, no: 'A1002', name: '收银员 小王', avatar: '🍊' },
  { id: 3, no: 'A1003', name: '收银员 小张', avatar: '🥬' },
]

// 登录成功后跳转：优先回到被路由守卫拦截的目标页
const goAfterLogin = () => {
  const target = router.currentRoute.value.query.redirect
  router.push(typeof target === 'string' && target.startsWith('/') ? target : '/')
}

// 表单登录：校验工号与密码后进入收银台
const doLogin = () => {
  if (!form.username.trim() || !form.password.trim()) {
    ElMessage.warning('请输入工号与密码')
    return
  }
  // 记录当前收银员（演示：用户名即身份，S6 对接真实登录接口）
  store.setCashier({ id: 1, no: 'A1001', name: form.username, role: 'cashier' })
  ElMessage.success(`欢迎回来，${form.username}`)
  goAfterLogin()
}

// 快捷登录：点击头像一键进入收银台
const quickLogin = (c) => {
  // 记录当前收银员，结算时随订单上传
  store.setCashier({ id: c.id, no: c.no, name: c.name, role: 'cashier' })
  ElMessage.success(`${c.name} 登录成功`)
  goAfterLogin()
}
</script>

<style scoped>
/* 全屏生鲜绿深色渐变背景 */
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-5);
  padding: var(--space-5);
  background: linear-gradient(165deg, var(--brand-deep) 0%, var(--neutral-900) 100%);
  color: #fff;
}

/* ----- 品牌区 ----- */
.brand {
  text-align: center;
}
.logo {
  width: 92px;
  height: 92px;
  margin: 0 auto 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 46px;
  font-weight: 700;
  color: #fff;
  background: var(--brand);
  border-radius: 28px;
  box-shadow: 0 8px 24px oklch(52% 0.15 152 / 0.5);
}
.sys-name {
  margin: 0;
  font-size: 30px;
  letter-spacing: 2px;
}
.sys-desc {
  margin: 6px 0 0;
  font-size: 14px;
  color: oklch(80% 0.05 152);
}

/* ----- 登录卡片 ----- */
.login-card {
  width: min(420px, 90vw);
  background: #fff;
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-md);
}
.login-card :deep(.el-input__wrapper) {
  min-height: 50px;
  border-radius: var(--radius-md);
}
.login-card :deep(.el-input__inner) {
  font-size: 17px;
}
.login-btn {
  width: 100%;
  height: 52px;
  font-size: 20px;
  letter-spacing: 6px;
  border-radius: var(--radius-md);
  margin-top: var(--space-1);
}

/* ----- 快捷选择区 ----- */
.quick-block {
  text-align: center;
}
.quick-title {
  font-size: 16px;
  color: oklch(85% 0.04 152);
  margin-bottom: var(--space-3);
}
.quick-list {
  display: flex;
  gap: var(--space-3);
}
.cashier-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 100px;
  padding: var(--space-3) var(--space-2);
  background: oklch(32% 0.08 152 / 0.9);
  border: 1px solid oklch(55% 0.12 152 / 0.6);
  border-radius: var(--radius-lg);
  color: #fff;
  cursor: pointer;
  transition: transform 0.12s, background 0.12s;
}
.cashier-btn:hover {
  transform: translateY(-2px);
  background: var(--brand);
}
.avatar {
  font-size: 34px;
}
.cashier-name {
  font-size: 15px;
  font-weight: 600;
}
.cashier-no {
  font-size: 12px;
  color: oklch(78% 0.04 152);
}

/* ----- 底部版本 ----- */
.footer {
  font-size: 13px;
  color: oklch(70% 0.04 152);
}
</style>
