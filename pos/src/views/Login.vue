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
            placeholder="登录账号（工号）"
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
        <el-button type="primary" class="login-btn" :loading="loading" @click="doLogin">登 录</el-button>
      </el-form>
    </div>

    <!-- 底部版本信息 -->
    <div class="footer">鲜衡 POS v0.1</div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api'
import { usePosStore } from '../stores/posStore'

const router = useRouter()
const store = usePosStore()

// 登录表单数据
const form = reactive({ username: '', password: '' })
// 登录请求进行中（防止重复提交）
const loading = ref(false)

// 登录成功后跳转：优先回到被路由守卫拦截的目标页
const goAfterLogin = () => {
  const target = router.currentRoute.value.query.redirect
  router.push(typeof target === 'string' && target.startsWith('/') ? target : '/')
}

// 表单登录：调用后端接口校验账号密码，成功后进入收银台
const doLogin = async () => {
  const username = form.username.trim()
  if (!username || !form.password.trim()) {
    ElMessage.warning('请输入账号与密码')
    return
  }
  loading.value = true
  try {
    const result = await login(username, form.password.trim())
    // 保存令牌与收银员身份（启动后保持登录，结算时随订单上传工号）
    store.setAuth(result.access_token, {
      id: result.user.id,
      no: result.user.username,
      name: result.user.name,
      role: result.user.role,
    })
    ElMessage.success(`欢迎回来，${result.user.name}`)
    goAfterLogin()
  } catch (err) {
    ElMessage.error(err.message || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
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

/* ----- 底部版本 ----- */
.footer {
  font-size: 13px;
  color: oklch(70% 0.04 152);
}
</style>
