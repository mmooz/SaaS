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
                @keyup.enter="handleMemberSearch"
                @clear="handleMemberSearch"
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
            <el-table v-loading="memberLoading" :data="members" stripe>
              <el-table-column prop="mobile" label="手机号" width="130">
                <template #default="{ row }"><span class="num">{{ row.mobile }}</span></template>
              </el-table-column>
              <el-table-column prop="name" label="姓名" width="110" />
              <el-table-column label="等级" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="levelTagType(row.level)" effect="light">{{ levelText(row.level) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="points" label="积分" width="90" align="right">
                <template #default="{ row }"><span class="num">{{ row.points }}</span></template>
              </el-table-column>
              <el-table-column label="储值余额(元)" width="120" align="right">
                <template #default="{ row }"><span class="num balance">¥{{ Number(row.balance).toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column label="累计消费(元)" width="120" align="right">
                <template #default="{ row }"><span class="num">¥{{ Number(row.total_spent).toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column label="注册时间" width="110">
                <template #default="{ row }"><span class="num">{{ fmtTime(row.created_at, 10) }}</span></template>
              </el-table-column>
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

            <!-- 分页（后端总数） -->
            <div class="pagination-wrap">
              <el-pagination
                v-model:current-page="memberPage"
                v-model:page-size="memberPageSize"
                :total="memberTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, sizes, prev, pager, next, jumper"
                background
                @current-change="handleMemberPageChange"
                @size-change="handleMemberSearch"
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
                    <el-option v-for="m in memberOptions" :key="m.id" :label="`${m.name}（${m.mobile}）`" :value="m.id" />
                  </el-select>
                </el-form-item>
                <div v-if="currentRechargeMember" class="member-info">
                  <span class="mi-name">{{ currentRechargeMember.name }}</span>
                  <el-tag size="small" :type="levelTagType(currentRechargeMember.level)" effect="light">{{ levelText(currentRechargeMember.level) }}</el-tag>
                  <span class="mi-balance">当前余额 <b class="num">¥{{ Number(currentRechargeMember.balance).toFixed(2) }}</b></span>
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
                  <el-button type="primary" :loading="rechargeLoading" :disabled="!currentRechargeMember || rechargeAmount <= 0" @click="submitRecharge">
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
                <el-table-column label="到账(元)" width="90" align="right">
                  <template #default="{ row }"><span class="num">+{{ row.amount.toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="赠送积分" width="90" align="right">
                  <template #default="{ row }"><span class="num gift">+{{ row.bonusPoints }}</span></template>
                </el-table-column>
                <el-table-column prop="method" label="操作来源" width="110" align="center" />
                <el-table-column label="门店归属" width="160" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.storeAttributionNote" size="small" type="warning" effect="light">{{ row.storeAttributionNote }}</el-tag>
                    <span v-else class="num">可信</span>
                  </template>
                </el-table-column>
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
            <!-- Q24：历史门店归属标注说明 -->
            <div class="store-tip">
              标注「历史数据门店归属不可信」的流水，其门店归属仅供参考；可信起始时间由后台配置，不影响金额与积分。
            </div>
            <div class="toolbar">
              <el-select v-model="pointTypeFilter" placeholder="全部类型" clearable class="filter-select" @change="loadPointRecords">
                <el-option v-for="t in pointTypes" :key="t" :label="txTypeText(t)" :value="t" />
              </el-select>
              <span class="point-summary">
                筛选结果共 <b class="num">{{ filteredPointRecords.length }}</b> 条变动
              </span>
            </div>
            <el-table v-loading="pointLoading" :data="filteredPointRecords" stripe>
              <el-table-column prop="time" label="时间" width="150">
                <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
              </el-table-column>
              <el-table-column label="会员" width="140">
                <template #default="{ row }">{{ row.name }}（{{ row.mobile }}）</template>
              </el-table-column>
              <el-table-column label="类型" width="110" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="pointTypeTag(row.type)" effect="light">{{ row.typeText }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="reason" label="原因" min-width="160" />
              <el-table-column label="门店归属" width="160" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.storeAttributionNote" size="small" type="warning" effect="light">{{ row.storeAttributionNote }}</el-tag>
                  <span v-else class="num">可信</span>
                </template>
              </el-table-column>
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
            <div class="stat-grid" v-loading="statsLoading">
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--brand)"><el-icon :size="20"><User /></el-icon></div>
                <div>
                  <div class="stat-label">会员总数（全租户）</div>
                  <div class="stat-value num">{{ memberStats.total }}</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--info)"><el-icon :size="20"><UserFilled /></el-icon></div>
                <div>
                  <div class="stat-label">今日新增（全租户）</div>
                  <div class="stat-value num">{{ memberStats.new_today }}</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--accent)"><el-icon :size="20"><Wallet /></el-icon></div>
                <div>
                  <div class="stat-label">储值余额总额（全租户）</div>
                  <div class="stat-value num">¥{{ Number(memberStats.balance_total).toFixed(2) }}</div>
                </div>
              </div>
              <div class="stat-card">
                <div class="stat-icon" style="--c: var(--success)"><el-icon :size="20"><TrendCharts /></el-icon></div>
                <div>
                  <div class="stat-label">本月储值收入（全租户）</div>
                  <div class="stat-value num">¥{{ Number(memberStats.recharge_this_month).toFixed(2) }}</div>
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
                  <template #default="{ row }">{{ row.name }}（{{ row.mobile }}）</template>
                </el-table-column>
                <el-table-column label="等级" width="90" align="center">
                  <template #default="{ row }">
                    <el-tag size="small" :type="levelTagType(row.level)" effect="light">{{ levelText(row.level) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="累计消费(元)" width="130" align="right">
                  <template #default="{ row }"><span class="num">{{ Number(row.total_spent).toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="本月消费(元)" width="130" align="right">
                  <template #default="{ row }"><span class="num">{{ Number(row.month_spent).toFixed(2) }}</span></template>
                </el-table-column>
                <el-table-column label="消费次数" width="100" align="right">
                  <template #default="{ row }"><span class="num">{{ row.order_count }}</span></template>
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
        <el-form-item label="手机号" prop="mobile">
          <el-input v-model="memberForm.mobile" :disabled="memberForm.id > 0" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="memberForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="会员等级" prop="level">
          <el-select v-model="memberForm.level" style="width: 100%">
            <el-option label="普通" value="normal" />
            <el-option label="银卡" value="silver" />
            <el-option label="金卡" value="gold" />
          </el-select>
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
          <div class="ds-name">{{ detailMember.name }}<el-tag size="small" :type="levelTagType(detailMember.level)" effect="light" class="ds-tag">{{ levelText(detailMember.level) }}</el-tag></div>
          <div class="ds-meta num">{{ detailMember.mobile }} · 积分 {{ detailMember.points }} · 余额 ¥{{ Number(detailMember.balance).toFixed(2) }} · 累计消费 ¥{{ Number(detailMember.total_spent).toFixed(2) }}</div>
        </div>
        <el-table v-loading="detailLoading" :data="detailMember.records" size="small">
          <el-table-column prop="time" label="时间" width="150">
            <template #default="{ row }"><span class="num">{{ row.time }}</span></template>
          </el-table-column>
          <el-table-column prop="reason" label="内容" min-width="200" />
          <el-table-column label="门店归属" width="160" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.storeAttributionNote" size="small" type="warning" effect="light">{{ row.storeAttributionNote }}</el-tag>
              <span v-else class="num">可信</span>
            </template>
          </el-table-column>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Wallet, User, UserFilled, TrendCharts } from '@element-plus/icons-vue'
import {
  createMember,
  fetchMemberStats,
  fetchMemberTransactions,
  fetchMembers,
  rechargeMember,
  updateMember,
} from '../api'

// 当前页签：profile / recharge / points / analysis
const activeTab = ref('profile')

// 会员等级：后端值 → 中文文案
const LEVEL_TO_TEXT = { normal: '普通', silver: '银卡', gold: '金卡' }

/**
 * 会员等级转中文
 * @param {string} level 后端等级值
 * @returns {string} 中文等级
 */
const levelText = (level) => LEVEL_TO_TEXT[level] || level || '普通'

/**
 * 会员等级对应标签颜色
 * @param {string} level 后端等级值
 * @returns {string} el-tag 类型
 */
const levelTagType = (level) => {
  if (level === 'gold') return 'danger'
  if (level === 'silver') return 'warning'
  return 'info'
}

/**
 * 时间格式化（ISO → 指定长度字符串）
 * @param {string|null} value 时间
 * @param {number} len 截取长度：日期 10 / 精确到分 16
 * @returns {string} 展示时间
 */
function fmtTime(value, len = 16) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, len)
}

/* ---------------- 会员档案 ---------------- */

// 搜索关键字
const memberSearch = ref('')
// 列表加载态
const memberLoading = ref(false)
// 当前页码
const memberPage = ref(1)
// 每页条数
const memberPageSize = ref(10)
// 会员总数（后端返回）
const memberTotal = ref(0)
// 当前页会员列表（后端数据）
const members = ref([])
// 全量会员（供充值下拉使用）
const memberOptions = ref([])

/**
 * 加载会员分页数据
 * @returns {Promise<void>}
 */
async function loadMembers() {
  memberLoading.value = true
  try {
    const data = await fetchMembers({
      keyword: memberSearch.value,
      page: memberPage.value,
      pageSize: memberPageSize.value,
    })
    members.value = data.items || []
    memberTotal.value = data.total || 0
  } catch (err) {
    ElMessage.error(`会员加载失败：${err.message}`)
  } finally {
    memberLoading.value = false
  }
}

/**
 * 加载全量会员（供充值下拉使用）
 * @returns {Promise<void>}
 */
async function loadMemberOptions() {
  try {
    const data = await fetchMembers({ page: 1, pageSize: 200 })
    memberOptions.value = data.items || []
  } catch (err) {
    ElMessage.error(`会员选项加载失败：${err.message}`)
  }
}

/**
 * 搜索会员：重置到第一页后加载
 */
function handleMemberSearch() {
  memberPage.value = 1
  loadMembers()
}

/**
 * 翻页 / 变更每页条数后重新加载
 */
function handleMemberPageChange() {
  loadMembers()
}

// 新增 / 编辑会员弹窗状态
const memberFormVisible = ref(false)
const memberFormRef = ref(null)
// 会员表单模型（字段与后端保持一致）
const memberForm = ref({ id: 0, mobile: '', name: '', level: 'normal' })
// 表单校验规则
const memberRules = {
  mobile: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  level: [{ required: true, message: '请选择会员等级', trigger: 'change' }],
}

/**
 * 打开新增会员弹窗
 */
const openAddMember = () => {
  memberForm.value = { id: 0, mobile: '', name: '', level: 'normal' }
  memberFormVisible.value = true
}

/**
 * 打开编辑会员弹窗（手机号不可修改）
 * @param {object} row 会员行
 */
const openEditMember = (row) => {
  memberForm.value = { id: row.id, mobile: row.mobile, name: row.name, level: row.level || 'normal' }
  memberFormVisible.value = true
}

/**
 * 提交会员表单：新增走 POST，编辑走 PATCH
 */
const submitMember = () => {
  memberFormRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (memberForm.value.id === 0) {
        await createMember({
          mobile: memberForm.value.mobile,
          name: memberForm.value.name,
          level: memberForm.value.level,
        })
        ElMessage.success('会员已新增')
      } else {
        await updateMember(memberForm.value.id, {
          name: memberForm.value.name,
          level: memberForm.value.level,
        })
        ElMessage.success('会员信息已更新')
      }
      memberFormVisible.value = false
      loadMembers()
      loadMemberOptions()
    } catch (err) {
      ElMessage.error(`保存失败：${err.message}`)
    }
  })
}

/**
 * 跳转到储值充值页签并预选该会员
 * @param {object} row 会员行
 */
const goRecharge = (row) => {
  rechargeMemberId.value = row.id
  activeTab.value = 'recharge'
}

// 明细弹窗状态
const detailVisible = ref(false)
const detailMember = ref(null)
// 明细加载态
const detailLoading = ref(false)

/**
 * 查看会员明细（加载最近 10 条会员流水）
 * @param {object} row 会员行
 * @returns {Promise<void>}
 */
async function openDetail(row) {
  detailMember.value = { ...row, records: [] }
  detailVisible.value = true
  detailLoading.value = true
  try {
    const data = await fetchMemberTransactions({ memberId: row.id, pageSize: 10 })
    detailMember.value.records = (data.items || []).map(toRecordRow)
  } catch (err) {
    ElMessage.error(`明细加载失败：${err.message}`)
  } finally {
    detailLoading.value = false
  }
}

/* ---------------- 储值充值 ---------------- */

// 选中会员 ID
const rechargeMemberId = ref(null)
// 充值金额
const rechargeAmount = ref(0)
// 支付方式（后台仅作记录展示）
const payMethod = ref('微信')
// 充值记录列表
const rechargeRecords = ref([])
// 充值提交中
const rechargeLoading = ref(false)

// 当前选中的充值会员
const currentRechargeMember = computed(
  () => memberOptions.value.find((m) => m.id === rechargeMemberId.value) || null,
)

/**
 * 切换充值会员时重置金额
 */
const onSelectRechargeMember = () => {
  rechargeAmount.value = 0
}

// 赠送金额：按充值金额梯度计算（满 200 送 15 / 满 500 送 50 / 满 1000 送 120）
const giftAmount = computed(() => {
  const a = rechargeAmount.value
  if (a <= 0) return 0
  if (a >= 1000) return 120
  if (a >= 500) return 50
  if (a >= 200) return 15
  return 0
})

/**
 * 加载充值记录（会员流水中 type=recharge）
 * @returns {Promise<void>}
 */
async function loadRechargeRecords() {
  try {
    const data = await fetchMemberTransactions({ type: 'recharge', pageSize: 20 })
    rechargeRecords.value = (data.items || []).map((t) => ({
      id: t.id,
      time: fmtTime(t.created_at),
      name: t.member_name || '—',
      phone: t.mobile || '—',
      amount: Number(t.amount || 0),
      bonusPoints: Number(t.points || 0),
      method: t.operator_id ? `操作员 ${t.operator_id}` : '后台充值',
      // Q24：后端可选字段，缺省视为可信
      storeAttributionNote:
        t.store_attribution_reliable === false ? '历史数据门店归属不可信' : '',
    }))
  } catch (err) {
    ElMessage.error(`充值记录加载失败：${err.message}`)
  }
}

/**
 * 确认充值：调用后端充值接口（含赠送金额）
 * @returns {Promise<void>}
 */
async function submitRecharge() {
  const m = currentRechargeMember.value
  if (!m || rechargeAmount.value <= 0) return
  rechargeLoading.value = true
  try {
    await rechargeMember(m.id, { amount: rechargeAmount.value, giftAmount: giftAmount.value })
    ElMessage.success(
      `充值成功：到账 ¥${(rechargeAmount.value + giftAmount.value).toFixed(2)}（含赠送 ¥${giftAmount.value.toFixed(2)}）`,
    )
    rechargeAmount.value = 0
    loadMemberOptions()
    loadMembers()
    loadRechargeRecords()
    loadPointRecords()
    loadMemberStats()
  } catch (err) {
    ElMessage.error(`充值失败：${err.message}`)
  } finally {
    rechargeLoading.value = false
  }
}

/* ---------------- 积分记录 ---------------- */

// 流水类型：后端值 → 中文文案
const TYPE_TO_TEXT = { recharge: '充值', consume: '消费', points: '积分调整', refund: '退款' }
// 积分筛选类型（后端值）
const pointTypes = Object.keys(TYPE_TO_TEXT)
// 类型筛选值
const pointTypeFilter = ref('')
// 积分流水列表
const pointRecords = ref([])
// 积分流水加载态
const pointLoading = ref(false)

/**
 * 流水类型转中文
 * @param {string} type 后端类型
 * @returns {string} 中文类型
 */
const txTypeText = (type) => TYPE_TO_TEXT[type] || type

/**
 * 流水类型对应标签颜色
 * @param {string} type 后端类型
 * @returns {string} el-tag 类型
 */
const pointTypeTag = (type) => {
  if (type === 'consume') return 'success'
  if (type === 'recharge') return 'primary'
  return 'warning'
}

/**
 * 会员流水转列表行（积分记录与明细弹窗共用）
 * @param {object} t 后端流水
 * @returns {object} 展示行
 */
function toRecordRow(t) {
  const points = Number(t.points || 0)
  const amount = Number(t.amount || 0)
  // Q24：后端可选字段，缺省视为可信；历史流水标注门店归属仅供参考
  const storeAttributionNote =
    t.store_attribution_reliable === false ? '历史数据门店归属不可信' : ''
  return {
    id: t.id,
    time: fmtTime(t.created_at),
    name: t.member_name || '—',
    mobile: t.mobile || '—',
    type: t.type,
    typeText: txTypeText(t.type),
    reason: `金额 ¥${amount.toFixed(2)} · 积分 ${points >= 0 ? '+' : ''}${points}`,
    change: points,
    storeAttributionNote,
  }
}

/**
 * 加载积分流水（仅保留积分变动不为 0 的记录）
 * @returns {Promise<void>}
 */
async function loadPointRecords() {
  pointLoading.value = true
  try {
    const data = await fetchMemberTransactions({ type: pointTypeFilter.value, pageSize: 100 })
    pointRecords.value = (data.items || []).map(toRecordRow).filter((r) => r.change !== 0)
  } catch (err) {
    ElMessage.error(`积分流水加载失败：${err.message}`)
  } finally {
    pointLoading.value = false
  }
}

// 积分记录展示列表（类型筛选已由后端处理）
const filteredPointRecords = computed(() => pointRecords.value)

/* ---------------- 会员分析 ---------------- */

// 会员统计概览
const memberStats = ref({
  total: 0,
  new_today: 0,
  balance_total: 0,
  recharge_this_month: 0,
  top: [],
})
// 统计加载态
const statsLoading = ref(false)

// 消费排行（补充名次）
const topMembers = computed(() => (memberStats.value.top || []).map((m, i) => ({ ...m, rank: i + 1 })))

/**
 * 加载会员统计与消费排行
 * @returns {Promise<void>}
 */
async function loadMemberStats() {
  statsLoading.value = true
  try {
    memberStats.value = await fetchMemberStats()
  } catch (err) {
    ElMessage.error(`会员统计加载失败：${err.message}`)
  } finally {
    statsLoading.value = false
  }
}

// 页面挂载时加载各页签数据
onMounted(() => {
  loadMembers()
  loadMemberOptions()
  loadRechargeRecords()
  loadPointRecords()
  loadMemberStats()
})
</script>

<style scoped>
.members-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Q24：历史门店归属标注说明 */
.store-tip {
  color: var(--neutral-500);
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 10px;
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
