<template>
  <div class="login-page">
    <!-- 品牌区：Logo + 系统名 -->
    <div class="brand">
      <div class="logo">衡</div>
      <h1 class="sys-name">鲜衡 POS</h1>
      <p class="sys-desc">电子秤收银终端 · 生鲜零售</p>
    </div>

    <!-- 登录卡片：R19 待改密账号切换为强制改密表单 -->
    <div class="login-card">
      <p v-if="needChange" class="change-tip">
        当前账号使用临时口令，请先设置新密码（至少 8 位，不得与原密码相同）
      </p>
      <el-form v-if="!needChange" @submit.prevent="doLogin">
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
      <el-form v-else @submit.prevent="doChangePassword">
        <el-form-item>
          <el-input
            v-model="changeForm.newPassword"
            size="large"
            type="password"
            show-password
            placeholder="新密码（至少 8 位）"
            @keyup.enter="doChangePassword"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="changeForm.confirmPassword"
            size="large"
            type="password"
            show-password
            placeholder="确认新密码"
            @keyup.enter="doChangePassword"
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="doChangePassword">
          设置新密码并登录
        </el-button>
        <el-button class="login-btn back-btn" :disabled="loading" @click="cancelChange">
          返回登录
        </el-button>
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
import { login, changePassword, setAuthToken, clearAuthToken } from '../api'
import { usePosStore } from '../stores/posStore'

const router = useRouter()
const store = usePosStore()

// 登录表单数据
const form = reactive({ username: '', password: '' })
// 强制改密表单数据
const changeForm = reactive({ newPassword: '', confirmPassword: '' })
// 登录请求进行中（防止重复提交）
const loading = ref(false)
// R19：服务端判定当前账号使用临时口令时，切换到强制改密视图
const needChange = ref(false)

// 登录成功后跳转：优先回到被路由守卫拦截的目标页
const goAfterLogin = () => {
  const target = router.currentRoute.value.query.redirect
  router.push(typeof target === 'string' && target.startsWith('/') ? target : '/')
}

/**
 * 保存登录态并进入收银台（登录成功与改密成功后共用）
 * @param {object} result 登录响应
 * @returns {void}
 */
const finishLogin = (result) => {
  // setAuth 内部会写入 pos_token，覆盖改密阶段暂存的临时令牌
  store.setAuth(
    result.access_token,
    {
      id: result.user.id,
      no: result.user.username,
      name: result.user.name,
      role: result.user.role,
    },
    result.stores || [],
  )
  ElMessage.success(`欢迎回来，${result.user.name}`)
  goAfterLogin()
}

// 表单登录：校验账号密码；待改密账号先进入改密视图，不落地登录态
const doLogin = async () => {
  const username = form.username.trim()
  if (!username || !form.password.trim()) {
    ElMessage.warning('请输入账号与密码')
    return
  }
  loading.value = true
  try {
    const result = await login(username, form.password.trim())
    if (result.must_change_password) {
      // 仅暂存令牌供改密接口携带；此时不写入收银员身份与门店缓存
      setAuthToken(result.access_token)
      needChange.value = true
      return
    }
    finishLogin(result)
  } catch (err) {
    ElMessage.error(err.message || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * R19：用临时口令换绑新密码。改密成功后旧令牌立即失效，须用新密码重新登录。
 * @returns {Promise<void>}
 */
const doChangePassword = async () => {
  if (!changeForm.newPassword || changeForm.newPassword.length < 8) {
    ElMessage.warning('新密码至少需要 8 位')
    return
  }
  if (changeForm.newPassword !== changeForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  loading.value = true
  try {
    await changePassword(form.password.trim(), changeForm.newPassword)
    // 改密已生效，后续任何请求都必须使用新密码签发的令牌
    let result
    try {
      result = await login(form.username.trim(), changeForm.newPassword)
    } catch (err) {
      ElMessage.success('密码已修改，请用新密码重新登录')
      cancelChange()
      return
    }
    needChange.value = false
    form.password = ''
    changeForm.newPassword = ''
    changeForm.confirmPassword = ''
    finishLogin(result)
  } catch (err) {
    ElMessage.error(err.message || '修改密码失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * 放弃本次改密：清除暂存的临时令牌，回到登录表单
 * @returns {void}
 */
const cancelChange = () => {
  clearAuthToken()
  needChange.value = false
  changeForm.newPassword = ''
  changeForm.confirmPassword = ''
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

/* ----- R19 强制改密 ----- */
.change-tip {
  margin: 0 0 var(--space-4);
  font-size: 14px;
  line-height: 1.6;
  color: var(--neutral-600, #5a6270);
}
.back-btn {
  margin-top: var(--space-2);
}
</style>
