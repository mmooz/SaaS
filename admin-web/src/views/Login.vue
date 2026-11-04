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
          <el-button type="primary" class="login-btn" @click="handleLogin">
            登 录
          </el-button>
        </el-form>
        <div class="quick-roles">
          <span class="qr-label">快捷体验：</span>
          <el-tag class="qr-tag" @click="quickLogin('店长')">店长</el-tag>
          <el-tag class="qr-tag" type="info" @click="quickLogin('管理员')">管理员</el-tag>
        </div>
      </div>
      <div class="login-footer">© 2026 鲜衡云 · 电子秤收银系统</div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 登录表单数据（页面设计阶段为模拟值）
const form = reactive({
  username: '',
  password: '',
})

// 登录：校验后跳转仪表盘
const handleLogin = () => {
  if (!form.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  router.push('/dashboard')
}

// 快捷登录：以对应角色进入后台
const quickLogin = (role) => {
  ElMessage.success(`以「${role}」身份进入演示环境`)
  router.push('/dashboard')
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
.quick-roles {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: center;
}
.qr-label {
  font-size: 12px;
  color: var(--neutral-400);
}
.qr-tag {
  cursor: pointer;
}
.login-footer {
  position: absolute;
  bottom: 24px;
  color: var(--neutral-400);
  font-size: 12px;
}
</style>
