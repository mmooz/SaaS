<template>
  <div class="members-page">
    <!-- 顶部页签：会员档案 / 储值充值 / 积分记录 / 会员分析 -->
    <div class="tabs-card">
      <el-tabs v-model="activeTab">
        <!-- ==================== 会员档案 ==================== -->
        <el-tab-pane label="会员档案" name="profile">
          <div class="pane-body">
            <!-- 搜索工具栏 -->
            <div class="toolbar">
              <el-input
                v-model="memberSearch"
                placeholder="搜索手机号 / 姓名"
                clearable
                class="search-input"
                @keyup.enter="memberPage = 1"
                @clear="memberPage = 1"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <div class="toolbar-right">
                <el-button type="primary" @click="openAddMember">
                  <el-icon><Plus /></el-icon>新增会员
                </el-button>
              </div>
            </div>

            <!-- 会员列表 -->
            <el-table v-loading="memberLoading" :data="pagedMembers" stripe>
              <el-table-column prop="phone" label="手机号" width="130">
                <template #default="{ row }"><span class="num">{{ row.phone }}</span></template>
              </el-table-column>
              <el-table-column prop="name" label="姓名" width="110" />
              <el-table-column label="等级" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="levelTagType(row.level)" effect="light">{{ row.level }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="points" label="积分" width="90" align="right">
                <template #default="{ row }"><span class="num">{{ row.points }}</span></template>
              </el-table-column>
              <el-table-column label="储值余额(元)" width="120" align="right">
                <template #default="{ row }"><span class="num balance">¥{{ row.balance.toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column label="累计消费(元)" width="120" align="right">
                <template #default="{ row }"><span class="num">¥{{ row.totalSpent.toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column prop="regDate" label="注册时间" width="110" />
              <el-table-column label="操作" width="180" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openEditMember(row)">编辑</el-button>
                  <el-button link type="warning" size="small" @click="goRecharge(row)">充值</el-button>
                  <el-button link size="small" @click="openDetail(row)">查看明细</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无会员数据" />
              </template>
            </el-table>

            <!-- 分页（模拟总数） -->
            <div class="pagination-wrap">
              <el-pagination
                v-model:current-page="memberPage"
                v-model:page-size="memberPageSize"
                :total="memberTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next, jumper"
                background
              />
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== 储值充值 ==================== -->
        <el-tab-pane label="储值充值" name="recharge">
          <div class="pane-body recharge-layout">
            <!-- 充值操作区 -->
            <div class="recharge-card">
              <h4 class="pane-title">会员充值</h4>
              <el-form label-width="92px">
                <el-form-item label="选择会员" required>
                  <el-select
                    v-model="rechargeMemberId"
                    filterable
                    placeholder="输入手机号 / 姓名搜索会员"
                    style="width: 100%"
                    @change="onSelectRechargeMember"
                  >
                    <el-option v-for="m in members" :key="m.id" :label="`${m.name}（${m.phone}）`" :value="m.id" />
                  </el-select>
                </el-form-item>
                <div v-if="rechargeMember" class="member-info">
                  <span class="mi-name">{{ rechargeMember.name }}</span>
                  <el-tag size="small" :type="levelTagType(rechargeMember.level)" effect="light">{{ rechargeMember.level }}</el-tag>
                  <span class="mi-balance">当前余额 <b class="num">¥{{ rechargeMember.balance.toFixed(2) }}</b></span>
                </div>
                <el-form-item label="充值金额">
                  <el-input-number v-model="rechargeAmount" :min="0" :max="9999" :precision="2" :step="100" style="width: 100%" />
                </el-form-item>
                <el-form-item label="赠送金额">
                  <span class="gift-amount num">¥{{ giftAmount.toFixed(2) }}</span>
                  <span class="gift-tip">满 200 送 15 / 满 500 送 50 / 满 1000 送 120</span>
                </el-form-item>
                <el-form-item label="支付方式">
                  <el-radio-group v-model="payMethod">
                    <el-radio value="微信">微信</el-radio>
                    <el-radio value="支付宝">支付宝</el-radio>
                    <el-radio value="现金">现金</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :disabled="!rechargeMember || rechargeAmount <= 0" @click="submitRecharge">
                    <el-icon><Wallet /></el-icon>确认充值
                  </el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 充值记录 -->
            <div class="recharge-card">
              <h4 class="pane-title">充值记录</h4>
              <el-table :data="rechargeRecords" size="small">
                <el-table-column prop="time" label="时间" width="150">
                  <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
                </el-table-column>
                <el-table-column label="会员" width="120">
                  <template #default="{ row }">{{ row.name }}（{{ row.phone }}）</template>
                </el-table-column>
                <el-table-column label="充值(元)" width="90" align="right">
                  <template #default="{ row }"><span class="num">+{{ row.amount.toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="赠送(元)" width="90" align="right">
                  <template #default="{ row }"><span class="num gift">+{{ row.gift.toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column prop="method" label="支付方式" width="90" align="center" />
                <el-table-column prop="operator" label="操作人" width="90" align="center" />
                <template #empty>
                  <el-empty description="暂无充值记录" />
                </template>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== 积分记录 ==================== -->
        <el-tab-pane label="积分记录" name="points">
          <div class="pane-body">
            <div class="toolbar">
              <el-select v-model="pointTypeFilter" placeholder="全部类型" clearable class="filter-select" @change="pointPage = 1">
                <el-option v-for="t in pointTypes" :key="t" :label="t" :value="t" />
              </el-select>
              <span class="point-summary">
                筛选结果共 <b class="num">{{ filteredPointRecords.length }}</b> 条变动
              </span>
            </div>
            <el-table :data="filteredPointRecords" stripe>
              <el-table-column prop="time" label="时间" width="150">
                <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
              </el-table-column>
              <el-table-column label="会员" width="140">
                <template #default="{ row }">{{ row.name }}（{{ row.phone }}）</template>
              </el-table-column>
              <el-table-column label="类型" width="110" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="pointTypeTag(row.type)" effect="light">{{ row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="160" />
              <el-table-column label="变动值" width="110" align="right">
                <template #default="{ row }">
                  <span class="num" :class="row.change >= 0 ? 'change-plus' : 'change-minus'">
                    {{ row.change >= 0 ? '+' : '' }}{{ row.change }}
                  </span>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无积分变动记录" />
              </template>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- ==================== 会员分析 ==================== -->
        <el-tab-pane label="会员分析" name="analysis">
          <div class="pane-body">
            <!-- 统计卡片 -->
            <div class="stat-grid">
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="20"><User /></el-icon></div>
                <div>
                  <div class="stat-label">会员总数</div>
                  <div class="stat-value num">1,286</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--info)"><el-icon :size="20"><UserFilled /></el-icon></div>
                <div>
                  <div class="stat-label">今日新增</div>
                  <div class="stat-value num">12</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="20"><Wallet /></el-icon></div>
                <div>
                  <div class="stat-label">储值余额总额</div>
                  <div class="stat-value num">¥86,420.00</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--success)"><el-icon :size="20"><TrendCharts /></el-icon></div>
                <div>
                  <div class="stat-label">本月储值收入</div>
                  <div class="stat-value num">¥12,580.00</div>
                </div>
              </div>
            </div>

            <!-- 会员消费排行 -->
            <div class="rank-card">
              <div class="card-head">
                <h3>会员消费排行</h3>
                <span class="rank-tip">按累计消费金额排序（前 10 名）</span>
              </div>
              <el-table :data="topMembers" stripe>
                <el-table-column label="排名" width="80" align="center">
                  <template #default="{ row }">
                    <span class="rank-badge" :class="{ top: row.rank <= 3 }">{{ row.rank }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="会员" min-width="150">
                  <template #default="{ row }">{{ row.name }}（{{ row.phone }}）</template>
                </el-table-column>
                <el-table-column label="等级" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="levelTagType(row.level)" effect="light">{{ row.level }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="累计消费(元)" width="130" align="right">
                  <template #default="{ row }"><span class="num">{{ row.totalSpent.toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="本月消费(元)" width="130" align="right">
                  <template #default="{ row }"><span class="num">{{ row.monthSpent.toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="消费次数" width="100" align="right">
                  <template #default="{ row }"><span class="num">{{ row.orderCount }}</span></template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 新增 / 编辑会员弹窗 -->
    <el-dialog v-model="memberFormVisible" :title="memberForm.id ? '编辑会员' : '新增会员'" width="480px">
      <el-form ref="memberFormRef" :model="memberForm" :rules="memberRules" label-width="90px">
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="memberForm.phone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="memberForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="会员等级" prop="level">
          <el-select v-model="memberForm.level" style="width: 100%">
            <el-option label="普通" value="普通" />
            <el-option label="银卡" value="银卡" />
            <el-option label="金卡" value="金卡" />
          </el-select>
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="memberForm.gender">
            <el-radio value="男">男</el-radio>
            <el-radio value="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生日" prop="birthday">
          <el-date-picker v-model="memberForm.birthday" type="date" placeholder="选择生日" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="memberForm.remark" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="memberFormVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMember">保存</el-button>
      </template>
    </el-dialog>

    <!-- 会员明细弹窗 -->
    <el-dialog v-model="detailVisible" title="会员明细" width="520px">
      <template v-if="detailMember">
        <div class="detail-summary">
          <div class="ds-name">{{ detailMember.name }}<el-tag size="small" :type="levelTagType(detailMember.level)" effect="light" class="ds-tag">{{ detailMember.level }}</el-tag></div>
          <div class="ds-meta num">{{ detailMember.phone }} · 积分 {{ detailMember.points }} · 余额 ¥{{ detailMember.balance.toFixed(2) }} · 累计消费 ¥{{ detailMember.totalSpent.toFixed(2) }}</div>
        </div>
        <el-table :data="detailMember.records" size="small">
          <el-table-column prop="time" label="时间" width="150">
            <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
          </el-table-column>
          <el-table-column prop="content" label="内容" min-width="200" />
          <el-table-column label="变动" width="100" align="right">
            <template #default="{ row }">
              <span class="num" :class="row.change >= 0 ? 'change-plus' : 'change-minus'">
                {{ row.change >= 0 ? '+' : '' }}{{ row.change }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Wallet, User, UserFilled, TrendCharts } from '@element-plus/icons-vue'

// ---- 状态 ----
const activeTab = ref('profile')

// 会员等级对应标签颜色
const levelTagType = (level) => {
  if (level === '金卡') return 'danger'
  if (level === '银卡') return 'warning'
  return 'info'
}

// ---- 模拟数据：会员列表 ----
const members = ref([
  { id: 1, phone: '13800138001', name: '张伟', level: '金卡', points: 2680, balance: 860.5, totalSpent: 4280.6, regDate: '2025-06-12', gender: '男',
    records: [
      { time: '2026-11-04 18:32', content: '消费积分 +12', change: 12 },
      { time: '2026-11-02 09:15', content: '积分兑换抵扣 ¥5', change: -500 },
      { time: '2026-10-28 19:40', content: '储值充值得积分', change: 100 },
    ] },
  { id: 2, phone: '13900139002', name: '李娜', level: '银卡', points: 1280, balance: 320.0, totalSpent: 1980.2, regDate: '2025-08-03', gender: '女',
    records: [
      { time: '2026-11-03 17:20', content: '消费积分 +8', change: 8 },
      { time: '2026-10-30 11:05', content: '消费抵扣积分', change: -200 },
    ] },
  { id: 3, phone: '13700137003', name: '王强', level: '普通', points: 360, balance: 0, totalSpent: 620.0, regDate: '2026-01-15', gender: '男', records: [] },
  { id: 4, phone: '13600136004', name: '赵敏', level: '金卡', points: 3560, balance: 1250.0, totalSpent: 5620.8, regDate: '2025-05-20', gender: '女',
    records: [
      { time: '2026-11-04 20:10', content: '消费积分 +20', change: 20 },
      { time: '2026-11-01 10:00', content: '储值充值 1000 送 120 得积分', change: 120 },
    ] },
  { id: 5, phone: '13500135005', name: '孙丽', level: '银卡', points: 980, balance: 200.0, totalSpent: 1520.5, regDate: '2025-10-08', gender: '女', records: [] },
  { id: 6, phone: '13400134006', name: '周杰', level: '普通', points: 180, balance: 0, totalSpent: 320.0, regDate: '2026-03-22', gender: '男', records: [] },
  { id: 7, phone: '13300133007', name: '吴芳', level: '银卡', points: 1450, balance: 480.0, totalSpent: 2350.0, regDate: '2025-09-01', gender: '女', records: [] },
  { id: 8, phone: '13200132008', name: '郑浩', level: '普通', points: 90, balance: 0, totalSpent: 210.0, regDate: '2026-06-30', gender: '男', records: [] },
  { id: 9, phone: '13100131009', name: '陈静', level: '金卡', points: 4120, balance: 2100.0, totalSpent: 8890.0, regDate: '2025-04-18', gender: '女',
    records: [
      { time: '2026-11-05 08:40', content: '消费积分 +30', change: 30 },
      { time: '2026-11-03 15:25', content: '积分兑换赠品', change: -800 },
    ] },
  { id: 10, phone: '13000130010', name: '刘洋', level: '普通', points: 240, balance: 60.0, totalSpent: 480.0, regDate: '2026-07-12', gender: '男', records: [] },
])

// 会员总数（模拟：含未展示数据）
const memberTotal = ref(1286)

// ---- 会员档案页 ----
const memberSearch = ref('')
const memberLoading = ref(false)
const memberPage = ref(1)
const memberPageSize = ref(10)

// 按手机号 / 姓名过滤会员
const filteredMembers = computed(() => {
  const kw = memberSearch.value.trim()
  if (!kw) return members.value
  return members.value.filter((m) => m.phone.includes(kw) || m.name.includes(kw))
})

// 当前分页会员
const pagedMembers = computed(() => {
  const start = (memberPage.value - 1) * memberPageSize.value
  return filteredMembers.value.slice(start, start + memberPageSize.value)
})

// 新增 / 编辑会员
const memberFormVisible = ref(false)
const memberFormRef = ref(null)
// 会员表单模型
const memberForm = ref({ id: 0, phone: '', name: '', level: '普通', gender: '男', birthday: '', remark: '' })
const memberRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
}

// 打开新增会员弹窗
const openAddMember = () => {
  memberForm.value = { id: 0, phone: '', name: '', level: '普通', gender: '男', birthday: '', remark: '' }
  memberFormVisible.value = true
}

// 打开编辑会员弹窗
const openEditMember = (row) => {
  memberForm.value = { ...row }
  memberFormVisible.value = true
}

// 提交会员表单：模拟保存
const submitMember = () => {
  memberFormRef.value.validate((valid) => {
    if (!valid) return
    if (memberForm.value.id === 0) {
      members.value.unshift({
        ...memberForm.value,
        id: Date.now(),
        points: 0,
        balance: 0,
        totalSpent: 0,
        regDate: '2026-11-05',
        records: [],
      })
      memberTotal.value += 1
      ElMessage.success('会员已新增')
    } else {
      const idx = members.value.findIndex((m) => m.id === memberForm.value.id)
      if (idx > -1) members.value[idx] = { ...members.value[idx], ...memberForm.value }
      ElMessage.success('会员信息已更新')
    }
    memberFormVisible.value = false
  })
}

// 跳转到储值充值页签并预选该会员
const goRecharge = (row) => {
  rechargeMemberId.value = row.id
  activeTab.value = 'recharge'
}

// 查看会员明细
const detailVisible = ref(false)
const detailMember = ref(null)
const openDetail = (row) => {
  detailMember.value = row
  detailVisible.value = true
}

// ---- 储值充值页 ----
const rechargeMemberId = ref(null)
const rechargeAmount = ref(0)
const payMethod = ref('微信')

// 当前选中的充值会员对象
const rechargeMember = computed(() => members.value.find((m) => m.id === rechargeMemberId.value) || null)

// 充值会员切换：重置金额
const onSelectRechargeMember = () => {
  rechargeAmount.value = 0
}

// 赠送金额：按充值金额梯度计算
const giftAmount = computed(() => {
  const a = rechargeAmount.value
  if (a <= 0) return 0
  if (a >= 1000) return 120
  if (a >= 500) return 50
  if (a >= 200) return 15
  return 0
})

// 模拟充值记录
const rechargeRecords = ref([
  { time: '2026-11-04 19:20', name: '赵敏', phone: '13600136004', amount: 1000, gift: 120, method: '微信', operator: '店长 王' },
  { time: '2026-11-02 10:05', name: '陈静', phone: '13100131009', amount: 500, gift: 50, method: '支付宝', operator: '收银 李' },
  { time: '2026-10-28 16:40', name: '张伟', phone: '13800138001', amount: 200, gift: 15, method: '现金', operator: '店长 王' },
  { time: '2026-10-25 09:30', name: '李娜', phone: '13900139002', amount: 300, gift: 15, method: '微信', operator: '收银 李' },
])

// 确认充值：写入充值记录并更新会员余额
const submitRecharge = () => {
  const m = rechargeMember.value
  m.balance += rechargeAmount.value + giftAmount.value
  rechargeRecords.value.unshift({
    time: '2026-11-05 09:00',
    name: m.name,
    phone: m.phone,
    amount: rechargeAmount.value,
    gift: giftAmount.value,
    method: payMethod.value,
    operator: '店长 王',
  })
  ElMessage.success(`充值成功：到账 ¥${(rechargeAmount.value + giftAmount.value).toFixed(2)}（含赠送 ¥${giftAmount.value.toFixed(2)}）`)
  rechargeAmount.value = 0
}

// ---- 积分记录页 ----
const pointTypes = ['消费得', '充值得', '抵扣', '兑换', '失效']
const pointTypeFilter = ref('')

// 积分变动类型对应标签颜色
const pointTypeTag = (t) => {
  if (t === '消费得') return 'success'
  if (t === '充值得') return 'primary'
  if (t === '抵扣' || t === '失效') return 'info'
  return 'warning'
}

// 模拟积分变动流水
const pointRecords = ref([
  { time: '2026-11-05 08:40', name: '陈静', phone: '13100131009', type: '消费得', reason: '消费 ¥68.00，按 1 元 1 积分', change: 30 },
  { time: '2026-11-04 20:10', name: '赵敏', phone: '13600136004', type: '消费得', reason: '消费 ¥45.20', change: 20 },
  { time: '2026-11-04 18:32', name: '张伟', phone: '13800138001', type: '消费得', reason: '消费 ¥28.60', change: 12 },
  { time: '2026-11-03 15:25', name: '陈静', phone: '13100131009', type: '兑换', reason: '积分兑换：5 元优惠券', change: -800 },
  { time: '2026-11-02 09:15', name: '张伟', phone: '13800138001', type: '抵扣', reason: '积分抵扣 ¥5.00', change: -500 },
  { time: '2026-11-01 10:00', name: '赵敏', phone: '13600136004', type: '充值得', reason: '储值充值 ¥1000 赠送 120', change: 120 },
  { time: '2026-10-30 11:05', name: '李娜', phone: '13900139002', type: '抵扣', reason: '积分抵扣 ¥2.00', change: -200 },
  { time: '2026-10-28 16:40', name: '张伟', phone: '13800138001', type: '充值得', reason: '储值充值 ¥200', change: 20 },
  { time: '2026-10-25 09:30', name: '李娜', phone: '13900139002', type: '消费得', reason: '消费 ¥36.80', change: 15 },
  { time: '2026-10-20 14:00', name: '孙丽', phone: '13500135005', type: '失效', reason: '年度积分过期', change: -50 },
])

// 按类型筛选积分流水
const filteredPointRecords = computed(() => {
  if (!pointTypeFilter.value) return pointRecords.value
  return pointRecords.value.filter((r) => r.type === pointTypeFilter.value)
})

// ---- 会员分析页 ----
// 模拟消费排行（前 10）
const topMembers = ref([
  { rank: 1, name: '陈静', phone: '13100131009', level: '金卡', totalSpent: 8890.0, monthSpent: 1268.5, orderCount: 86 },
  { rank: 2, name: '赵敏', phone: '13600136004', level: '金卡', totalSpent: 5620.8, monthSpent: 986.2, orderCount: 64 },
  { rank: 3, name: '张伟', phone: '13800138001', level: '金卡', totalSpent: 4280.6, monthSpent: 820.0, orderCount: 52 },
  { rank: 4, name: '吴芳', phone: '13300133007', level: '银卡', totalSpent: 2350.0, monthSpent: 460.0, orderCount: 38 },
  { rank: 5, name: '李娜', phone: '13900139002', level: '银卡', totalSpent: 1980.2, monthSpent: 320.0, orderCount: 29 },
  { rank: 6, name: '孙丽', phone: '13500135005', level: '银卡', totalSpent: 1520.5, monthSpent: 280.5, orderCount: 24 },
  { rank: 7, name: '郑浩', phone: '13200132008', level: '普通', totalSpent: 620.0, monthSpent: 120.0, orderCount: 11 },
  { rank: 8, name: '王强', phone: '13700137003', level: '普通', totalSpent: 320.0, monthSpent: 0, orderCount: 8 },
])
</script>

<style scoped>
.members-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 页签卡片 */
.tabs-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 6px 18px 18px;
}
.pane-body {
  padding-top: 6px;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.search-input {
  width: 260px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}
.filter-select {
  width: 140px;
}
.point-summary {
  font-size: 13px;
  color: var(--neutral-500);
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* 表格数字样式 */
.num {
  font-family: var(--font-num);
  font-variant-numeric: tabular-nums;
}
.balance {
  color: var(--brand-deep);
  font-weight: 600;
}

/* 充值页 */
.recharge-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 16px;
  align-items: start;
}
.recharge-card {
  background: var(--neutral-50);
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  padding: 16px 18px;
}
.pane-title {
  font-size: 15px;
  color: var(--neutral-800);
  margin: 0 0 14px;
}
.member-info {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border: 1px solid var(--brand-soft);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-bottom: 14px;
}
.mi-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--neutral-800);
}
.mi-balance {
  font-size: 13px;
  color: var(--neutral-600);
}
.mi-balance b {
  color: var(--brand-deep);
}
.gift-amount {
  font-size: 18px;
  font-weight: 700;
  color: var(--accent);
}
.gift-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--neutral-400);
}
.gift {
  color: var(--accent);
  font-weight: 600;
}

/* 积分正负着色 */
.change-plus {
  color: var(--success);
  font-weight: 600;
}
.change-minus {
  color: var(--danger);
  font-weight: 600;
}

/* 分析页统计卡片 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: color-mix(in oklch, var(--c) 12%, white);
  color: var(--c);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-label {
  font-size: 13px;
  color: var(--neutral-500);
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--neutral-900);
  line-height: 1.3;
}

/* 排行卡片 */
.rank-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.card-head h3 {
  font-size: 15px;
  color: var(--neutral-800);
}
.rank-tip {
  font-size: 12px;
  color: var(--neutral-400);
}
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--neutral-100);
  color: var(--neutral-600);
  font-size: 12px;
  font-weight: 600;
}
.rank-badge.top {
  background: var(--brand);
  color: #fff;
}

/* 会员明细弹窗 */
.detail-summary {
  margin-bottom: 14px;
}
.ds-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-900);
  display: flex;
  align-items: center;
  gap: 8px;
}
.ds-tag {
  font-size: 12px;
}
.ds-meta {
  margin-top: 6px;
  font-size: 13px;
  color: var(--neutral-500);
}
</style>
