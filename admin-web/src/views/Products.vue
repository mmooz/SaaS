<template>
  <div class="products-page">
    <!-- 顶部工具栏：搜索 / 筛选 / 操作按钮 -->
    <div class="toolbar-card">
      <div class="toolbar-left">
        <el-input
          v-model="searchText"
          placeholder="搜索商品名 / 条码 / 拼音码"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="filterCategory" placeholder="全部分类" clearable class="filter-select" @change="handleSearch">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-select v-model="filterPricing" placeholder="全部计价方式" clearable class="filter-select" @change="handleSearch">
          <el-option label="称重" value="称重" />
          <el-option label="按件" value="按件" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="openAdd">
          <el-icon><Plus /></el-icon>新增商品
        </el-button>
        <el-button @click="batchVisible = true">
          <el-icon><Operation /></el-icon>批量改价
        </el-button>
        <el-button @click="importVisible = true">
          <el-icon><Upload /></el-icon>Excel 导入
        </el-button>
        <el-button @click="exportVisible = true">
          <el-icon><Download /></el-icon>导出
        </el-button>
      </div>
    </div>

    <!-- 商品列表 -->
    <div class="table-card">
      <el-table v-loading="loading" :data="pagedProducts" stripe>
        <el-table-column prop="barcode" label="条码" width="140">
          <template #default="{ row }"><span class="num">{{ row.barcode }}</span></template>
        </el-table-column>
        <el-table-column label="名称" min-width="160">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="p-name">{{ row.name }}</span>
              <span class="p-pinyin">{{ row.pinyin }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="计价方式" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.pricing === '称重' ? 'primary' : 'info'" effect="light">
              {{ row.pricing }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="单价(元)" width="100" align="right">
          <template #default="{ row }"><span class="num price">¥{{ row.price.toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column label="会员价(元)" width="100" align="right">
          <template #default="{ row }"><span class="num">{{ row.memberPrice.toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column label="进价(元)" width="90" align="right">
          <template #default="{ row }"><span class="num">{{ row.cost.toFixed(2) }}</span></template>
        </el-table-column>
        <el-table-column label="本店库存" width="100" align="right">
          <template #default="{ row }">
            <span class="num">{{ row.stock }}<span class="unit">{{ row.unit }}</span></span>
          </template>
        </el-table-column>
        <el-table-column label="保质期" width="90" align="center">
          <template #default="{ row }"><span class="num">{{ row.shelfLife }}天</span></template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleStatus(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无商品数据" />
        </template>
      </el-table>

      <!-- 分页（服务端总数） -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>
    </div>

    <!-- 新增 / 编辑商品弹窗 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑商品' : '新增商品'" width="640px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="商品条码" prop="barcode">
              <el-input v-model="form.barcode" placeholder="扫描或手动输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="商品名称" prop="name">
              <el-input v-model="form.name" placeholder="如：上海青" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="拼音码" prop="pinyin">
              <el-input v-model="form.pinyin" placeholder="如：shanghaiqing" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属分类" prop="category">
              <el-select v-model="form.category" placeholder="选择分类" style="width: 100%">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计价方式" prop="pricing">
              <el-radio-group v-model="form.pricing">
                <el-radio value="称重">称重</el-radio>
                <el-radio value="按件">按件</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计量单位" prop="unit">
              <el-select v-model="form.unit" style="width: 100%">
                <el-option v-for="u in units" :key="u" :label="u" :value="u" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="零售价" prop="price">
              <el-input-number v-model="form.price" :min="0" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="会员价" prop="memberPrice">
              <el-input-number v-model="form.memberPrice" :min="0" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="进价" prop="cost">
              <el-input-number v-model="form.cost" :min="0" :precision="2" :step="0.1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="保质期(天)" prop="shelfLife">
              <el-input-number v-model="form.shelfLife" :min="0" :max="999" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="本店库存" prop="stock">
              <el-input-number v-model="form.stock" :min="0" :precision="1" :step="0.5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="本店安全库存" prop="safetyStock">
              <el-input-number v-model="form.safetyStock" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="标签打印" prop="labelPrint">
              <el-switch v-model="form.labelPrint" active-text="收银时打印标签" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量改价弹窗 -->
    <el-dialog v-model="batchVisible" title="批量改价" width="520px">
      <el-form label-width="96px">
        <el-form-item label="改价方式">
          <el-radio-group v-model="batch.scope">
            <el-radio value="category">按分类</el-radio>
            <el-radio value="product">按商品</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="batch.scope === 'category'" label="选择分类">
          <el-select v-model="batch.category" placeholder="选择要改价的分类" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="选择商品">
          <el-select v-model="batch.products" multiple filterable placeholder="选择商品（可多选）" style="width: 100%">
            <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="调整方式">
          <el-radio-group v-model="batch.method">
            <el-radio value="percent">比例（%）</el-radio>
            <el-radio value="fixed">固定值（元）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="调整幅度">
          <el-input-number v-model="batch.amount" :min="0" :precision="batch.method === 'percent' ? 1 : 2" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBatch">确认改价</el-button>
      </template>
    </el-dialog>

    <!-- Excel 导入弹窗 -->
    <el-dialog v-model="importVisible" title="Excel 导入商品" width="480px">
      <div class="import-tip">
        <p>支持 .xlsx 文件，单次最多导入 1000 条商品。</p>
        <p>导入模板包含：条码、名称、拼音码、分类、计价方式、单位、零售价等字段。</p>
      </div>
      <el-upload
        v-model:file-list="importFiles"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xlsm"
        class="import-upload"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击选择文件</em></div>
        <template #tip>
          <div class="el-upload__tip">请先下载<a class="tpl-link" @click.prevent="downloadTemplate">导入模板</a>，按模板格式填写后再上传。</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 导出弹窗 -->
    <el-dialog v-model="exportVisible" title="导出商品数据" width="440px">
      <el-form label-width="96px">
        <el-form-item label="导出范围">
          <el-radio-group v-model="exportScope">
            <el-radio value="all">全部商品</el-radio>
            <el-radio value="filter">当前筛选结果</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="文件格式">
          <el-radio-group v-model="exportFormat">
            <el-radio value="xlsx">Excel (.xlsx)</el-radio>
            <el-radio value="csv">CSV (.csv)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确认导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Operation, Upload, Download, UploadFilled } from '@element-plus/icons-vue'
import {
  batchAdjustPrice,
  createProduct,
  deleteProduct,
  fetchCategoryTree,
  fetchProducts,
  importProducts,
  productExportUrl,
  productTemplateUrl,
  updateProduct,
} from '../api'

// ---- 分类与单位 ----
// 分类名称列表（筛选与表单下拉使用）
const categories = ref([])
// 分类名称 -> 分类 ID（提交后端时转换）
const categoryMap = ref({})
const units = ['kg', 'g', '个', '袋']

// ---- 商品列表（服务端数据） ----
const products = ref([])

/**
 * 把后端商品转换为页面展示模型
 * @param {object} p 后端商品
 * @returns {object} 页面行数据
 */
const toRow = (p) => ({
  id: p.id,
  barcode: p.barcode,
  name: p.name,
  pinyin: p.pinyin || '',
  category: p.category_name || '',
  categoryId: p.category_id,
  pricing: p.pricing_mode === 'weigh' ? '称重' : '按件',
  unit: p.unit,
  price: Number(p.price) || 0,
  memberPrice: Number(p.member_price) || 0,
  cost: Number(p.cost_price) || 0,
  stock: Number(p.stock) || 0,
  shelfLife: Number(p.shelf_life_days) || 0,
  safetyStock: Number(p.safety_stock) || 0,
  labelPrint: !!p.label_enabled,
  enabled: !!p.enabled,
})

// ---- 筛选 / 分页状态 ----
const searchText = ref('')
const filterCategory = ref('')
const filterPricing = ref('')
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 当前分页数据（服务端已分页）
const pagedProducts = computed(() => products.value)

/**
 * 加载分类树并生成名称映射
 * @returns {Promise<void>}
 */
const loadCategories = async () => {
  try {
    const tree = await fetchCategoryTree()
    const names = []
    const map = {}
    const walk = (nodes) => {
      (nodes || []).forEach((node) => {
        names.push(node.name)
        map[node.name] = node.id
        walk(node.children)
      })
    }
    walk(tree)
    categories.value = names
    categoryMap.value = map
  } catch (err) {
    ElMessage.error(`分类加载失败：${err.message}`)
  }
}

/**
 * 按当前筛选条件加载商品（服务端分页）
 * @returns {Promise<void>}
 */
const loadProducts = async () => {
  loading.value = true
  try {
    const data = await fetchProducts({
      keyword: searchText.value.trim() || undefined,
      categoryId: categoryMap.value[filterCategory.value] || undefined,
      pricingMode: filterPricing.value === '称重'
        ? 'weigh'
        : filterPricing.value === '按件'
          ? 'count'
          : undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    products.value = (data.items || []).map(toRow)
    total.value = data.total || 0
  } catch (err) {
    ElMessage.error(`商品加载失败：${err.message}`)
  } finally {
    loading.value = false
  }
}

// 搜索动作（回到第一页后查询）
const handleSearch = () => {
  page.value = 1
  loadProducts()
}

// 切换状态：调用后端更新启停
const toggleStatus = async (row) => {
  try {
    await updateProduct(row.id, { enabled: row.enabled })
    ElMessage.success(`「${row.name}」已${row.enabled ? '启用' : '停用'}`)
  } catch (err) {
    row.enabled = !row.enabled
    ElMessage.error(`状态更新失败：${err.message}`)
  }
}

// ---- 新增 / 编辑商品 ----
const formVisible = ref(false)
const formRef = ref(null)
// 商品表单模型（新增时使用默认值）
const form = ref({
  id: 0, barcode: '', name: '', pinyin: '', category: '', pricing: '称重', unit: 'kg',
  price: 0, memberPrice: 0, cost: 0, shelfLife: 30, stock: 0, safetyStock: 0, labelPrint: true,
  enabled: true,
})

// 表单校验规则
const formRules = {
  barcode: [{ required: true, message: '请输入商品条码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  pinyin: [{ required: true, message: '请输入拼音码', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  pricing: [{ required: true, message: '请选择计价方式', trigger: 'change' }],
  unit: [{ required: true, message: '请选择计量单位', trigger: 'change' }],
  price: [{ required: true, message: '请输入零售价', trigger: 'blur' }],
}

// 打开新增弹窗：重置表单为默认值
const openAdd = () => {
  form.value = {
    id: 0, barcode: '', name: '', pinyin: '', category: '', pricing: '称重', unit: 'kg',
    price: 0, memberPrice: 0, cost: 0, shelfLife: 30, stock: 0, safetyStock: 0, labelPrint: true,
    enabled: true,
  }
  formVisible.value = true
}

// 打开编辑弹窗：拷贝行数据到表单
const openEdit = (row) => {
  form.value = { ...row }
  formVisible.value = true
}

/**
 * 表单转后端请求字段
 * @param {object} f 表单数据
 * @returns {object} 后端商品字段
 */
const toPayload = (f) => ({
  barcode: f.barcode,
  name: f.name,
  pinyin: f.pinyin,
  category_id: categoryMap.value[f.category] ?? null,
  pricing_mode: f.pricing === '称重' ? 'weigh' : 'count',
  unit: f.unit,
  price: f.price,
  member_price: f.memberPrice,
  cost_price: f.cost,
  shelf_life_days: f.shelfLife,
  stock: f.stock,
  safety_stock: f.safetyStock,
  label_enabled: f.labelPrint,
  enabled: f.enabled !== false,
})

// 提交表单：新增或更新商品
const submitForm = () => {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    const isEdit = form.value.id !== 0
    try {
      if (isEdit) {
        await updateProduct(form.value.id, toPayload(form.value))
        ElMessage.success('商品已更新')
      } else {
        await createProduct(toPayload(form.value))
        ElMessage.success('商品已新增')
      }
      formVisible.value = false
      await loadProducts()
    } catch (err) {
      ElMessage.error(`保存失败：${err.message}`)
    }
  })
}

// 删除商品：二次确认后调用后端
const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除商品「${row.name}」吗？删除后不可恢复。`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await deleteProduct(row.id)
        ElMessage.success('删除成功')
        await loadProducts()
      } catch (err) {
        ElMessage.error(`删除失败：${err.message}`)
      }
    })
    .catch(() => {})
}

// ---- 批量改价 ----
const batchVisible = ref(false)
// 批量改价表单模型
const batch = ref({
  scope: 'category', category: '', products: [], method: 'percent', amount: 5,
})

// 确认批量改价：调用后端按分类/商品调整价格
const submitBatch = async () => {
  try {
    const data = await batchAdjustPrice({
      mode: batch.value.scope === 'category' ? 'category' : 'product',
      categoryId: categoryMap.value[batch.value.category] ?? null,
      productIds: batch.value.products,
      adjustType: batch.value.method,
      value: batch.value.amount,
    })
    ElMessage.success(data.message || '批量改价完成')
    batchVisible.value = false
    await loadProducts()
  } catch (err) {
    ElMessage.error(`改价失败：${err.message}`)
  }
}

// ---- 导入 / 导出 ----
const importVisible = ref(false)
const exportVisible = ref(false)
const exportScope = ref('filter')
const exportFormat = ref('xlsx')
const importFiles = ref([])
const importing = ref(false)

// 下载商品导入模板
const downloadTemplate = () => {
  window.open(productTemplateUrl(), '_blank')
}

// 执行 Excel 导入
const doImport = async () => {
  if (!importFiles.value.length) {
    ElMessage.warning('请先选择 .xlsx 文件')
    return
  }
  importing.value = true
  try {
    const result = await importProducts(importFiles.value[0].raw)
    ElMessage.success(`导入完成：新增 ${result.created ?? 0} 条，更新 ${result.updated ?? 0} 条，失败 ${result.failed ?? 0} 条`)
    importVisible.value = false
    importFiles.value = []
    await loadProducts()
  } catch (err) {
    ElMessage.error(`导入失败：${err.message}`)
  } finally {
    importing.value = false
  }
}

// 导出商品数据（后端导出全部商品为 Excel）
const confirmExport = () => {
  window.open(productExportUrl(), '_blank')
  exportVisible.value = false
}

// 分页参数变化时重新查询
watch([page, pageSize], () => loadProducts())

onMounted(async () => {
  await loadCategories()
  await loadProducts()
})
</script>

<style scoped>
.products-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 工具栏卡片 */
.toolbar-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.search-input {
  width: 260px;
}
.filter-select {
  width: 140px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 表格卡片 */
.table-card {
  background: #fff;
  border: 1px solid var(--neutral-200);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 6px 18px 16px;
}
.name-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}
.p-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--neutral-800);
}
.p-pinyin {
  font-size: 11px;
  color: var(--neutral-400);
}
.price {
  color: var(--brand-deep);
  font-weight: 600;
}
.unit {
  font-size: 12px;
  color: var(--neutral-400);
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* 导入弹窗 */
.import-tip {
  font-size: 13px;
  color: var(--neutral-600);
  margin-bottom: 12px;
}
.import-tip p {
  margin: 4px 0;
}
.import-upload {
  width: 100%;
}
.upload-icon {
  font-size: 32px;
  color: var(--neutral-300);
  margin-bottom: 6px;
}
.tpl-link {
  color: var(--brand);
  cursor: pointer;
}
</style>
