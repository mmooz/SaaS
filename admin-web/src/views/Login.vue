<template>
  <div class="login-page">
    <!-- 左侧品牌展示区 -->
    <div class="login-brand">
      <div class="brand-card">
        <div class="brand-logo">衡</div>
        <h1>鲜衡云</h1>
        <p class="brand-slogan">电子秤收银系统 · 生鲜超市场景</p>
        <div class="brand-features">
          <div class="feature"><span class="fi">⚖️</span>称重计价</div>
          <div class="feature"><span class="fi">🏷️</span>标签打印</div>
          <div class="feature"><span class="fi">📊</span>经营分析</div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单区 -->
    <div class="login-panel">
      <div class="login-card">
        <h2>登录后台管理</h2>
        <p class="login-tip">请使用店长或管理员账号登录</p>
        <el-form :model="form" size="large" @keyup.enter="handleLogin">
          <el-form-item>
            <el-input v-model="form.username" placeholder="用户名 / 手机号" clearable>
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" type="password" placeholder="密码" show-password>
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form>
      </div>
      <div class="login-footer">© 2026 鲜衡云 · 电子秤收银系统</div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login, setAdminToken } from '../api'

const router = useRouter()

// 登录中状态（防止重复提交）
const loading = ref(false)

// 登录表单数据
const form = reactive({
  username: '',
  password: '',
})

/**
 * 登录：调用后端认证接口，校验角色后保存令牌并跳转仪表盘
 * @returns {Promise<void>}
 */
const handleLogin = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名与密码')
    return
  }
  loading.value = true
  try {
    const res = await login(form.username, form.password)
    // 仅店长/管理员可进入后台
    if (!['admin', 'manager'].includes(res.user.role)) {
      ElMessage.warning('该账号无后台管理权限')
      return
    }
    setAdminToken(res.access_token)
    ElMessage.success(`欢迎回来，${res.user.name}`)
    router.push('/dashboard')
  } catch (err) {
    ElMessage.error(`登录失败：${err.message}`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
}
.login-brand {
  flex: 1.2;
  background: linear-gradient(150deg, var(--neutral-900) 0%, oklch(24% 0.04 152) 60%, oklch(30% 0.09 152) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.login-brand::before {
  content: '';
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: radial-gradient(circle, oklch(52% 0.15 152 / 0.25), transparent 70%);
  top: -80px;
  right: -120px;
}
.brand-card {
  text-align: center;
  z-index: 1;
}
.brand-logo {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  border-radius: 20px;
  background: linear-gradient(135deg, var(--brand), oklch(60% 0.15 120));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 34px;
  font-weight: 700;
  box-shadow: 0 8px 24px oklch(52% 0.15 152 / 0.5);
}
.brand-card h1 {
  color: #fff;
  font-size: 30px;
  letter-spacing: 3px;
}
.brand-slogan {
  color: oklch(85% 0.03 152);
  margin: 10px 0 32px;
  font-size: 14px;
}
.brand-features {
  display: flex;
  gap: 14px;
  justify-content: center;
}
.feature {
  background: oklch(90% 0.02 152 / 0.08);
  border: 1px solid oklch(90% 0.02 152 / 0.16);
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 13px;
  color: oklch(92% 0.03 152);
}
.fi {
  margin-right: 6px;
}
.login-panel {
  flex: 1;
  background: var(--neutral-50);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}
.login-card {
  width: 360px;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 36px 32px;
  box-shadow: var(--shadow-md);
}
.login-card h2 {
  font-size: 21px;
  margin-bottom: 6px;
}
.login-tip {
  color: var(--neutral-500);
  font-size: 13px;
  margin: 0 0 26px;
}
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: var(--radius-md);
  font-weight: 600;
}
.login-footer {
  position: absolute;
  bottom: 24px;
  color: var(--neutral-400);
  font-size: 12px;
}
</style>
