<template>
  <div class="portfolio-page">
    <!-- ====== 加载态 ====== -->
    <template v-if="pageState === 'loading'">
      <div class="page-content">
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            <span class="text-base font-semibold">我的持仓</span>
          </div>
          <div class="flex items-center gap-3">
            <span class="btn-plain btn-sm disabled" style="opacity:0.5">刷新</span>
            <span class="btn-primary btn-sm disabled" style="opacity:0.5">组合分析</span>
          </div>
        </div>
        <!-- 骨架卡片 -->
        <div class="stat-grid">
          <div v-for="i in 4" :key="i" class="stat-card">
            <div class="skeleton" style="width:60px;height:14px;margin-bottom:12px" />
            <div class="skeleton" style="width:140px;height:28px;margin-bottom:8px" />
            <div class="skeleton" style="width:80px;height:12px" />
          </div>
        </div>
        <!-- 骨架图表 -->
        <div class="chart-grid">
          <div class="card"><div class="card-header"><div class="skeleton" style="width:80px;height:16px" /></div><div class="card-body" style="display:flex;justify-content:center;min-height:200px"><div class="skeleton" style="width:160px;height:160px;border-radius:50%" /></div></div>
          <div class="card"><div class="card-header"><div class="skeleton" style="width:80px;height:16px" /></div><div class="card-body" style="min-height:200px"><div style="display:flex;flex-direction:column;gap:16px"><div class="skeleton" style="width:100%;height:20px" v-for="i in 5" :key="i" /></div></div></div>
        </div>
        <!-- 骨架表格 -->
        <div class="card"><div class="card-header"><div class="skeleton" style="width:100px;height:16px" /></div><div class="card-body" style="padding:0"><div style="padding:16px 20px 0"><div class="skeleton" style="width:200px;height:28px" /></div><div style="padding:16px 20px"><div class="skeleton" style="width:100%;height:28px;margin-bottom:12px" v-for="i in 4" :key="i" /></div></div></div>
      </div>
    </template>

    <!-- ====== 错误态 ====== -->
    <template v-else-if="pageState === 'error'">
      <div class="page-content">
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            <span class="text-base font-semibold">我的持仓</span>
          </div>
          <div class="flex items-center gap-3">
            <button class="btn btn-plain btn-sm" @click="refreshAll">重试</button>
          </div>
        </div>
        <div class="card"><div class="card-body">
          <div class="error-state">
            <svg viewBox="0 0 24 24" fill="#f56c6c" style="width:64px;height:64px;margin-bottom:16px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="none"/><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
            <div style="font-size:16px;font-weight:600;color:#303133;margin-bottom:8px">数据加载失败</div>
            <div style="font-size:14px;color:#909399;margin-bottom:20px">{{ errorMessage }}</div>
            <button class="btn btn-primary" @click="refreshAll">重新加载</button>
          </div>
        </div></div>
      </div>
    </template>

    <!-- ====== 空态 ====== -->
    <template v-else-if="pageState === 'empty'">
      <div class="page-content">
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            <span class="text-base font-semibold">我的持仓</span>
          </div>
        </div>
        <div class="stat-grid">
          <div v-for="(lbl, i) in ['总投入','可用现金','总资产（人民币）','总盈亏']" :key="i" class="stat-card" style="opacity:0.5">
            <div class="label">{{ lbl }}</div>
            <div class="value">{{ i < 3 ? '¥0.00' : '--' }}</div>
          </div>
        </div>
        <div class="card"><div class="card-body">
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="#c0c4cc" style="width:120px;height:120px;margin-bottom:16px;opacity:0.3"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            <div class="empty-title">还没有持仓数据</div>
            <div class="empty-desc">通过 Claude Code CLI 录入你的第一笔持仓，<br>系统会自动获取最新价格并计算盈亏。</div>
            <button class="btn btn-primary" style="margin-top:12px" @click="openAddDialog">添加第一笔持仓</button>
          </div>
        </div></div>
      </div>
    </template>

    <!-- ====== 理想态 ====== -->
    <template v-else>
      <div class="page-content">
        <!-- 页面标题行 -->
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5" style="color:var(--primary)" viewBox="0 0 24 24" fill="currentColor"><path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>
            <span class="text-base font-semibold">我的持仓</span>
            <span class="update-time ml-3">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>
              更新于 {{ lastUpdate }}
            </span>
          </div>
          <div class="flex items-center gap-3">
            <button class="btn btn-plain btn-sm" @click="refreshAll">刷新</button>
            <button class="btn btn-primary btn-sm" @click="openAddDialog">添加持仓</button>
            <button class="btn btn-primary btn-sm" :disabled="!summary?.positions?.length" @click="requestAdvice">
              {{ adviceGenerating ? adviceStep : '组合分析' }}
            </button>
            <button class="btn btn-plain btn-sm" @click="showAccountDialog = true">设置账户</button>
          </div>
        </div>

        <!-- 账户总览：4 个统计卡片 -->
        <div class="stat-grid">
          <div class="stat-card">
            <div class="label">总投入</div>
            <div class="value">{{ fmtMoney(summary?.total_invested) }}</div>
            <div class="sub">累计投入本金</div>
          </div>
          <div class="stat-card">
            <div class="label">可用现金</div>
            <div class="value">{{ fmtMoney(summary?.available_cash) }}</div>
            <div class="sub"><span style="color:var(--text-secondary)">含汇率折算</span></div>
          </div>
          <div class="stat-card">
            <div class="label">总资产（人民币）</div>
            <div class="value" style="font-size:28px">{{ fmtMoney(summary?.total_assets) }}</div>
            <div class="sub">持仓市值 {{ fmtMoney(summary?.total_market_value_cny) }}</div>
          </div>
          <div class="stat-card">
            <div class="label">总盈亏</div>
            <div class="value" :style="{ color: pnlColor(summary?.total_pnl) }">{{ fmtSignedMoney(summary?.total_pnl) }}</div>
            <div class="sub">
              <span :style="{ color: pnlColor(summary?.total_pnl), fontWeight: 600 }">
                {{ summary?.total_pnl_pct != null ? (summary!.total_pnl_pct >= 0 ? '+' : '') + summary!.total_pnl_pct.toFixed(2) + '%' : '--' }}
              </span>
              <span style="color:var(--text-secondary);margin-left:4px">较投入</span>
            </div>
          </div>
        </div>

        <!-- 组合总览：仓位分布 + 盈亏贡献 -->
        <div class="chart-grid" v-if="summary?.positions?.length">
          <!-- 仓位分布 -->
          <div class="card">
            <div class="card-header">
              仓位分布
              <span style="font-size:12px;color:var(--text-secondary);font-weight:400">按市值占比</span>
            </div>
            <div class="card-body" style="display:flex;align-items:flex-start;gap:32px">
              <div class="pie-chart-css" :style="{ background: pieGradient }" />
              <div class="pie-legend" style="flex:1">
                <div v-for="item in topPositions" :key="item.code" class="pie-legend-item">
                  <div class="pie-legend-dot" :style="{ background: pieColors[item.code] }" />
                  <span class="pie-legend-label">{{ item.name || item.code }}</span>
                  <span class="pie-legend-value">{{ item.weight.toFixed(1) }}%</span>
                </div>
                <div v-if="otherCount > 0" class="pie-legend-item">
                  <div class="pie-legend-dot" style="background:var(--text-secondary)" />
                  <span class="pie-legend-label">其他 ({{ otherCount }}只)</span>
                  <span class="pie-legend-value">{{ otherWeight.toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 盈亏贡献 -->
          <div class="card">
            <div class="card-header">
              盈亏贡献
              <span style="font-size:12px;color:var(--text-secondary);font-weight:400">各持仓对总盈亏的贡献</span>
            </div>
            <div class="card-body">
              <div v-for="pos in sortedByPnl" :key="pos.code" class="contrib-bar">
                <div class="name">{{ pos.name || pos.code }}</div>
                <div class="bar-wrap">
                  <div class="bar-fill" :class="(pos.pnl_cny || 0) >= 0 ? 'positive' : 'negative'"
                    :style="{ width: pnlBarWidth(pos.pnl_cny) + '%', left: (pos.pnl_cny || 0) >= 0 ? '50%' : 'auto', right: (pos.pnl_cny || 0) < 0 ? '50%' : 'auto' }" />
                </div>
                <div class="pnl-value" :style="{ color: pnlColor(pos.pnl_cny) }">
                  {{ fmtSignedMoney(pos.pnl_cny) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 持仓列表 -->
        <div class="card mb-5">
          <div class="card-header">
            <div class="flex items-center gap-2">
              持仓明细
              <span style="font-size:12px;color:var(--text-secondary);font-weight:400">({{ summary?.positions?.length || 0 }} 只)</span>
            </div>
          </div>
          <div class="card-body" style="padding:0">
            <!-- 市场筛选 -->
            <div class="filter-tabs" style="padding:16px 20px 0">
              <div v-for="f in marketFilters" :key="f.key"
                class="filter-tab" :class="{ active: marketFilter === f.key }"
                @click="marketFilter = f.key">
                {{ f.label }} ({{ f.count }})
              </div>
            </div>

            <table class="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>市场</th>
                  <th>分类</th>
                  <th style="text-align:right">数量</th>
                  <th style="text-align:right">均价</th>
                  <th style="text-align:right">最新价</th>
                  <th style="text-align:right">市值 (CNY)</th>
                  <th style="text-align:right">仓位占比</th>
                  <th style="text-align:right">盈亏</th>
                  <th style="text-align:right">盈亏率</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in filteredPositions" :key="pos.code">
                  <td>
                    <a class="stock-link" @click="viewStockDetail(pos.code, pos.instrument_type)">{{ pos.code }}</a>
                  </td>
                  <td>{{ pos.name || pos.code }}</td>
                  <td>
                    <span class="tag" :class="marketTagClass(pos.market)">{{ marketLabel(pos.market) }}</span>
                  </td>
                  <td>
                    <span class="tag" :style="instTagStyle(pos.instrument_type)">{{ instrumentTypeLabel[pos.instrument_type || 'other'] || pos.instrument_type || '未分类' }}</span>
                  </td>
                  <td style="text-align:right">{{ pos.quantity }}</td>
                  <td style="text-align:right">{{ fmtPrice(pos.avg_cost) }}</td>
                  <td style="text-align:right">{{ fmtPrice(pos.last_price) }}</td>
                  <td style="text-align:right">{{ fmtMoney(pos.market_value_cny) }}</td>
                  <td style="text-align:right">
                    <div class="flex items-center justify-end gap-2">
                      <div class="progress-bar" style="width:60px">
                        <div class="progress-fill" :style="{ width: (pos.weight || 0) + '%', background: 'var(--primary)' }" />
                      </div>
                      <span>{{ (pos.weight || 0).toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td style="text-align:right" :style="{ color: pnlColor(pos.pnl_cny), fontWeight: 500 }">
                    {{ fmtSignedMoney(pos.pnl_cny) }}
                  </td>
                  <td style="text-align:right" :style="{ color: pnlColor(pos.pnl_cny), fontWeight: 500 }">
                    <template v-if="pos.pnl_pct != null">{{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%</template>
                    <template v-else>--</template>
                  </td>
                  <td>
                    <button class="btn-text-success" @click="goAnalysis(pos.code, pos.instrument_type)">分析</button>
                    <button class="btn-text" @click="editPosition(pos)">编辑</button>
                    <button class="btn-text-danger" @click="removePosition(pos.code)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 交易记录（折叠） -->
        <div class="card" v-if="positions?.length">
          <div class="card-header" style="cursor:pointer" @click="historyOpen = !historyOpen">
            <div class="flex items-center gap-2">
              交易记录
              <span style="font-size:12px;color:var(--text-secondary);font-weight:400">(最近 5 条)</span>
            </div>
            <svg class="w-4 h-4 transition-transform" :style="{ transform: historyOpen ? 'rotate(180deg)' : 'rotate(0deg)' }" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
          </div>
          <div v-show="historyOpen">
            <table class="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th style="text-align:right">均价</th>
                  <th style="text-align:right">数量</th>
                  <th>买入日期</th>
                  <th>分类</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in positions?.slice(0, 5)" :key="pos.code">
                  <td>{{ pos.code }}</td>
                  <td>{{ pos.name || pos.code }}</td>
                  <td style="text-align:right">{{ fmtPrice(pos.avg_cost) }}</td>
                  <td style="text-align:right">{{ pos.quantity }}</td>
                  <td style="color:var(--text-secondary)">{{ pos.buy_date || '--' }}</td>
                  <td>{{ instrumentTypeLabel[pos.instrument_type || 'other'] || pos.instrument_type || '--' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- ====== 弹窗（所有状态共用） ====== -->
    <!-- 添加持仓 -->
    <el-dialog v-model="addDialog" title="添加持仓" width="480px">
      <el-form label-width="90px">
        <el-form-item label="代码">
          <el-input v-model="addForm.code" placeholder="A股: 600519 | 港股: 0700 | 美股: AAPL" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="addForm.quantity" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="买入均价">
          <el-input-number v-model="addForm.avg_cost" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="买入日期">
          <el-date-picker v-model="addForm.buy_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="addForm.notes" placeholder="可选" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="addForm.instrument_type" style="width:100%">
            <el-option v-for="opt in instrumentTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 编辑持仓 -->
    <el-dialog v-model="editDialog" title="编辑持仓" width="480px">
      <el-form label-width="90px">
        <el-form-item label="代码">
          <el-input :model-value="editForm.code" disabled />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="editForm.quantity" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="均价">
          <el-input-number v-model="editForm.avg_cost" :min="0.01" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.instrument_type" style="width:100%">
            <el-option v-for="opt in instrumentTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 设置账户 -->
    <el-dialog v-model="showAccountDialog" title="设置账户" width="400px">
      <el-form label-width="90px">
        <el-form-item label="总投入">
          <el-input-number v-model="accountForm.total_invested" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="可用现金">
          <el-input-number v-model="accountForm.available_cash" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAccountDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAccount">保存</el-button>
      </template>
    </el-dialog>

    <!-- 组合建议抽屉 -->
    <el-drawer v-model="adviceDrawer" title="组合建议" size="55%" direction="rtl">
      <template v-if="currentAdvice">
        <div v-if="currentAdvice.status === 'COMPLETED'">
          <h4 style="margin:0 0 12px">操作建议</h4>
          <div class="decision-card-stream">
            <DecisionCard
              v-for="item in sortedPrescription"
              :key="item.code"
              :item="item"
            />
          </div>
          <div v-if="!(currentAdvice.prescription || []).length" style="color:#909399;font-size:13px;padding:12px 0">
            暂无操作建议
          </div>
          <h4 style="margin:20px 0 8px">CIO 裁决</h4>
          <div class="advice-text" v-html="renderMd(currentAdvice.cio_verdict)" />
          <el-collapse style="margin-top:16px">
            <el-collapse-item v-if="currentAdvice.macro_judge_verdict" title="市场扫描 · L1 行业方向" name="market_intel">
              <div class="advice-text" v-html="renderMd(currentAdvice.macro_judge_verdict)" />
            </el-collapse-item>
            <el-collapse-item v-if="currentAdvice.stock_judge_verdict" title="候选标的 · L2 标的筛选" name="stock_candidates">
              <div class="advice-text" v-html="renderMd(currentAdvice.stock_judge_verdict)" />
            </el-collapse-item>
            <el-collapse-item title="持仓分析师评估" name="analyst">
              <div class="advice-text" v-html="renderMd(currentAdvice.analyst_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="策略师评估" name="strategist">
              <div class="advice-text" v-html="renderMd(currentAdvice.strategist_assessment)" />
            </el-collapse-item>
            <el-collapse-item title="侦察兵评估" name="scout">
              <div class="advice-text" v-html="renderMd(currentAdvice.scout_assessment)" />
            </el-collapse-item>
            <el-collapse-item v-if="currentAdvice.risk_director_review" title="风险审查 · L4 终端审查" name="risk_review">
              <div class="advice-text" v-html="renderMd(currentAdvice.risk_director_review)" />
            </el-collapse-item>
            <el-collapse-item title="辩论记录 · L3 组合辩论" name="debate">
              <div class="advice-text" v-html="renderMd(currentAdvice.debate_history)" />
            </el-collapse-item>
            <el-collapse-item v-if="currentAdvice.market_debate_history" title="辩论记录 · L1 行业辩论" name="market_debate">
              <div class="advice-text" v-html="renderMd(currentAdvice.market_debate_history)" />
            </el-collapse-item>
            <el-collapse-item v-if="currentAdvice.stock_debate_history" title="辩论记录 · L2 标的辩论" name="stock_debate">
              <div class="advice-text" v-html="renderMd(currentAdvice.stock_debate_history)" />
            </el-collapse-item>
          </el-collapse>
          <div class="advice-meta">生成于 {{ currentAdvice.completed_at?.slice(0, 19).replace('T', ' ') }} · 耗时 {{ currentAdvice.elapsed_seconds }}s</div>
        </div>
        <div v-else-if="currentAdvice.status === 'FAILED'" class="advice-error">
          <el-result icon="error" title="生成失败" :sub-title="currentAdvice.error || '未知错误'" />
        </div>
        <div v-else class="advice-loading">
          <el-result icon="info" title="正在生成" :sub-title="currentAdvice.current_step || '请稍候...'" />
        </div>
      </template>
      <el-empty v-else description="暂无组合建议" />
      <template v-if="adviceHistory.length > 1">
        <el-divider />
        <h4>历史建议</h4>
        <el-select v-model="selectedAdviceId" placeholder="选择历史记录" style="width:100%" @change="loadAdvice">
          <el-option v-for="h in adviceHistory" :key="h.advice_id"
            :label="(h.created_at?.slice(0, 19).replace('T', ' ') || '') + ' — ' + h.status"
            :value="h.advice_id" />
        </el-select>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { portfolioApi, type PortfolioSummary, type PortfolioAdvice, type PortfolioPositionItem, type AdviceItem } from '@/api/paper'
import DecisionCard from '@/components/Analysis/DecisionCard.vue'

const router = useRouter()

// ---- state ----
const summary = ref<PortfolioSummary | null>(null)
const positions = ref<PortfolioPositionItem[]>([])
const pageState = ref<'loading' | 'empty' | 'error' | 'ideal'>('loading')
const errorMessage = ref('')
const lastUpdate = ref('--')

const addDialog = ref(false)
const addForm = ref({ code: '', quantity: 100, avg_cost: 0, buy_date: '', notes: '', instrument_type: 'stock' })

const editDialog = ref(false)
const editForm = ref({ code: '', quantity: 0, avg_cost: 0, notes: '', instrument_type: 'stock' })

const showAccountDialog = ref(false)
const accountForm = ref({ total_invested: 0, available_cash: 0 })

const marketFilter = ref('all')
const historyOpen = ref(false)

const adviceDrawer = ref(false)
const adviceGenerating = ref(false)
const adviceStep = ref('')
const currentAdvice = ref<PortfolioAdvice | null>(null)
const adviceHistory = ref<PortfolioAdvice[]>([])
const selectedAdviceId = ref('')
let advicePollTimer: ReturnType<typeof setInterval> | null = null

// ---- colors ----
const PIE_COLORS = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb', '#36cfc9', '#ffc53d']

// ---- computed ----
const topPositions = computed(() => {
  if (!summary.value?.positions) return []
  return summary.value.positions.slice(0, 5)
})

const otherCount = computed(() => {
  if (!summary.value?.positions) return 0
  return Math.max(0, summary.value.positions.length - 5)
})

const otherWeight = computed(() => {
  if (!summary.value?.positions) return 0
  return summary.value.positions.slice(5).reduce((s, p) => s + (p.weight || 0), 0)
})

const pieColors = computed(() => {
  const map: Record<string, string> = {}
  topPositions.value.forEach((p, i) => { map[p.code] = PIE_COLORS[i % PIE_COLORS.length] })
  return map
})

const pieGradient = computed(() => {
  const all = summary.value?.positions || []
  if (!all.length) return 'none'
  // Normalize to sum → 360deg regardless of whether weights include cash
  const totalWeight = all.reduce((s, p) => s + (p.weight || 0), 0)
  if (totalWeight <= 0) return 'none'
  let accum = 0
  const segments: string[] = []
  all.forEach((p, i) => {
    const deg = ((p.weight || 0) / totalWeight) * 360
    const start = accum
    const end = i === all.length - 1 ? 360 : accum + deg
    segments.push(`${PIE_COLORS[i % PIE_COLORS.length]} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`)
    accum = end
  })
  return `conic-gradient(${segments.join(',')})`
})

const sortedByPnl = computed(() => {
  if (!summary.value?.positions) return []
  return [...summary.value.positions].sort((a, b) => Math.abs(b.pnl_cny || 0) - Math.abs(a.pnl_cny || 0))
})

const marketFilters = computed(() => {
  const all = summary.value?.positions || []
  return [
    { key: 'all', label: '全部', count: all.length },
    { key: 'CN', label: 'A股', count: all.filter(p => p.market === 'CN').length },
    { key: 'HK', label: '港股', count: all.filter(p => p.market === 'HK').length },
    { key: 'US', label: '美股', count: all.filter(p => p.market === 'US').length },
    { key: 'fund', label: '基金', count: all.filter(p => p.instrument_type === 'fund').length },
  ]
})

const filteredPositions = computed(() => {
  const all = summary.value?.positions || []
  if (marketFilter.value === 'all') return all
  if (marketFilter.value === 'fund') return all.filter(p => p.instrument_type === 'fund')
  return all.filter(p => p.market === marketFilter.value)
})

const sortedPrescription = computed(() => {
  const items = (currentAdvice.value?.prescription || []) as AdviceItem[]
  const order: Record<string, number> = { urgent: 0, important: 1, optional: 2 }
  return [...items].sort((a, b) => (order[a.priority || 'optional'] ?? 2) - (order[b.priority || 'optional'] ?? 2))
})

// ---- helpers ----
function fmtMoney(n: number | null | undefined) {
  if (n == null) return '--'
  return `¥${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtSignedMoney(n: number | null | undefined) {
  if (n == null) return '--'
  const sign = n >= 0 ? '+' : ''
  return `${sign}¥${Math.abs(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPrice(n: number | null | undefined) {
  if (n == null) return '--'
  return Number(n).toFixed(2)
}

function pnlColor(n: number | null | undefined) {
  if (n == null || n === 0) return '#909399'
  return n > 0 ? '#F56C6C' : '#67C23A'
}

function pnlBarWidth(pnl: number | null | undefined) {
  if (!pnl || !summary.value?.positions?.length) return 0
  // 50 = half-bar width (positive bars go right, negative go left from center)
  const maxPnl = Math.max(...summary.value.positions.map(p => Math.abs(p.pnl_cny || 0)), 1)
  return Math.min(50, (Math.abs(pnl) / maxPnl) * 50)
}

function marketTagClass(m: string) {
  return m === 'CN' ? 'tag-cn' : m === 'HK' ? 'tag-hk' : 'tag-us'
}

function marketLabel(m: string) {
  return m === 'CN' ? 'A股' : m === 'HK' ? '港股' : m === 'US' ? '美股' : m
}

function instTagStyle(t: string | undefined) {
  const colors: Record<string, string> = {
    stock: 'background:#f0f9eb;color:#67c23a;border:1px solid #e1f3d8',
    etf: 'background:#ecf5ff;color:#409eff;border:1px solid #d9ecff',
    fund: 'background:#fdf6ec;color:#e6a23c;border:1px solid #faecd8',
    bond: 'background:#f4f4f5;color:#909399;border:1px solid #e9e9eb',
    other: 'background:#fef0f0;color:#f56c6c;border:1px solid #fde2e2',
  }
  return colors[t || ''] || colors['other']
}

function detectInstrumentType(code: string): string {
  if (!code) return 'stock'
  const c = code.trim().toUpperCase()
  const cnEtfPrefixes = ['159', '510', '511', '512', '513', '515', '516', '517', '518', '588', '560', '561', '562', '563']
  for (const prefix of cnEtfPrefixes) {
    if (c.startsWith(prefix)) return 'etf'
  }
  return 'stock'
}

const instrumentTypeOptions = [
  { label: '股票', value: 'stock' },
  { label: 'ETF', value: 'etf' },
  { label: '基金', value: 'fund' },
  { label: '债券', value: 'bond' },
  { label: '其他', value: 'other' },
]

const instrumentTypeLabel: Record<string, string> = {
  stock: '股票', etf: 'ETF', fund: '基金', bond: '债券', other: '其他',
}

// ---- data fetching ----
async function fetchSummary() {
  try {
    const res = await portfolioApi.getSummary()
    if (res.success) {
      summary.value = res.data
      accountForm.value = {
        total_invested: res.data.total_invested || 0,
        available_cash: res.data.available_cash || 0,
      }
      if (res.data.positions?.length) {
        pageState.value = 'ideal'
      } else {
        pageState.value = 'empty'
      }
      const now = new Date()
      lastUpdate.value = now.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', month: 'numeric', day: 'numeric' })
    }
  } catch (e: any) {
    errorMessage.value = e?.message || '无法获取持仓数据，请检查网络连接后重试。'
    pageState.value = 'error'
  }
}

async function fetchPositions() {
  try {
    const res = await portfolioApi.getPositions()
    if (res.success) {
      positions.value = res.data.items || []
    }
  } catch { /* ignore */ }
}

// ---- actions ----
async function refreshAll() {
  pageState.value = 'loading'
  await fetchSummary()
  await fetchPositions()
}

function openAddDialog() {
  addForm.value = { code: '', quantity: 100, avg_cost: 0, buy_date: '', notes: '', instrument_type: 'stock' }
  addDialog.value = true
}

watch(() => addForm.value.code, (newCode) => {
  addForm.value.instrument_type = detectInstrumentType(newCode)
})

async function submitAdd() {
  if (!addForm.value.code || !addForm.value.avg_cost) {
    ElMessage.warning('请填写代码和买入均价')
    return
  }
  try {
    const res = await portfolioApi.addPosition({
      code: addForm.value.code,
      quantity: addForm.value.quantity,
      avg_cost: addForm.value.avg_cost,
      buy_date: addForm.value.buy_date || undefined,
      notes: addForm.value.notes || undefined,
      instrument_type: addForm.value.instrument_type,
    })
    if (res.success) {
      ElMessage.success('持仓已添加')
      addDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '添加失败')
  }
}

function editPosition(row: any) {
  editForm.value = {
    code: row.code,
    quantity: row.quantity,
    avg_cost: row.avg_cost,
    notes: row.notes || '',
    instrument_type: row.instrument_type || 'stock',
  }
  editDialog.value = true
}

async function submitEdit() {
  try {
    const res = await portfolioApi.updatePosition(editForm.value.code, {
      quantity: editForm.value.quantity,
      avg_cost: editForm.value.avg_cost,
      notes: editForm.value.notes || undefined,
      instrument_type: editForm.value.instrument_type,
    })
    if (res.success) {
      ElMessage.success('持仓已更新')
      editDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  }
}

async function removePosition(code: string) {
  try {
    await ElMessageBox.confirm(`确认删除持仓 ${code}？`, '删除确认', { type: 'warning' })
    const res = await portfolioApi.deletePosition(code)
    if (res.success) {
      ElMessage.success('持仓已删除')
      await refreshAll()
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

async function submitAccount() {
  try {
    const res = await portfolioApi.updateAccount({
      total_invested: accountForm.value.total_invested,
      available_cash: accountForm.value.available_cash,
    })
    if (res.success) {
      ElMessage.success('账户已更新')
      showAccountDialog.value = false
      await refreshAll()
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '更新失败')
  }
}

function viewStockDetail(code: string, instrumentType?: string) {
  if (instrumentType === 'fund') {
    router.push({ name: 'FundDetail', params: { code } })
  } else {
    router.push({ name: 'StockDetail', params: { code } })
  }
}

function goAnalysis(code: string, instrumentType?: string) {
  router.push({
    name: 'SingleAnalysis',
    query: {
      stock: code,
      instrument_type: instrumentType || 'stock'
    }
  })
}

// ---- advice ----
async function requestAdvice() {
  try {
    adviceGenerating.value = true
    adviceStep.value = '提交中...'
    const res = await portfolioApi.generateAdvice()
    if (res.success && res.data?.advice_id) {
      adviceStep.value = '准备数据'
      selectedAdviceId.value = res.data.advice_id
      pollAdviceStatus(res.data.advice_id)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '触发组合建议失败')
    adviceGenerating.value = false
  }
}

function pollAdviceStatus(adviceId: string) {
  if (advicePollTimer) clearInterval(advicePollTimer)
  advicePollTimer = setInterval(async () => {
    try {
      const res = await portfolioApi.getAdvice(adviceId)
      if (!res.success) return
      const adv = res.data
      if (adv.status === 'COMPLETED' || adv.status === 'FAILED') {
        if (advicePollTimer) { clearInterval(advicePollTimer); advicePollTimer = null }
        adviceGenerating.value = false
        currentAdvice.value = adv
        adviceDrawer.value = true
        await fetchAdviceHistory()
        if (adv.status === 'COMPLETED') ElMessage.success('组合建议已生成')
        else ElMessage.error('组合建议生成失败')
      } else {
        adviceStep.value = adv.current_step || '分析中...'
      }
    } catch { /* ignore */ }
  }, 3000)
}

async function loadAdvice(adviceId: string) {
  try {
    const res = await portfolioApi.getAdvice(adviceId)
    if (res.success) currentAdvice.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.message || '加载建议失败')
  }
}

async function fetchAdviceHistory() {
  try {
    const res = await portfolioApi.getAdviceHistory(1, 20)
    if (res.success) adviceHistory.value = res.data.items || []
  } catch { /* ignore */ }
}

function renderMd(text: string | undefined): string {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onMounted(() => { refreshAll() })
onUnmounted(() => { if (advicePollTimer) clearInterval(advicePollTimer) })
</script>

<style scoped>
/* ===== Design Tokens — MUST use .portfolio-page scope, not :root (scoped CSS compiles :root[data-v-xxx] which never matches) ===== */
.portfolio-page {
  --primary: #409eff;
  --primary-light: #ecf5ff;
  --success: #67c23a;
  --warning: #e6a23c;
  --danger: #f56c6c;
  --text-primary: #303133;
  --text-regular: #606266;
  --text-secondary: #909399;
  --border-light: #e4e7ed;
  --border-lighter: #ebeef5;
  --fill-light: #f5f7fa;
  --bg-page: #f2f3f5;
  --stock-up: #f56c6c;
  --stock-down: #67c23a;
  background: var(--bg-page);
  min-height: 100vh;
}

/* ===== Layout ===== */
.page-content { max-width: 1400px; margin: 0 auto; padding: 24px; }

/* ===== Flex helpers ===== */
.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.justify-end { justify-content: flex-end; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.mb-5 { margin-bottom: 20px; }
.ml-3 { margin-left: 12px; }
.w-4 { width: 16px; }
.w-5 { width: 20px; }
.h-4 { height: 16px; }
.h-5 { height: 20px; }
.text-base { font-size: 14px; }
.font-semibold { font-weight: 600; }

/* ===== Card ===== */
.card { background: #fff; border-radius: 8px; border: 1px solid #ebeef5; transition: box-shadow 0.3s; }
.card:hover { box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1); }
.card-header { padding: 14px 20px; border-bottom: 1px solid #ebeef5; font-weight: 600; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }
.card-body { padding: 20px; }

/* ===== Stat Cards ===== */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.stat-card { background: #fff; border-radius: 8px; border: 1px solid #ebeef5; padding: 20px; transition: box-shadow 0.3s; }
.stat-card .label { font-size: 13px; color: #909399; margin-bottom: 8px; }
.stat-card .value { font-size: 24px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-card .sub { font-size: 12px; color: #909399; margin-top: 4px; }
.stat-card:hover { border-color: #409eff; background: linear-gradient(135deg, #ecf5ff 0%, #fff 100%); box-shadow: 0 2px 12px 0 rgba(64,158,255,0.15); }
.stat-card:hover .value { color: #409eff; }

/* ===== Charts ===== */
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.pie-chart-css { width: 200px; height: 200px; border-radius: 50%; flex-shrink: 0; }
.pie-legend-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
.pie-legend-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.pie-legend-label { flex: 1; color: #606266; font-size: 13px; }
.pie-legend-value { font-weight: 600; color: #303133; font-size: 13px; }

.contrib-bar { display: flex; align-items: center; gap: 12px; padding: 8px 0; }
.contrib-bar .name { width: 80px; font-size: 13px; color: #606266; text-align: right; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.contrib-bar .bar-wrap { flex: 1; height: 20px; background: #f5f7fa; border-radius: 4px; position: relative; overflow: hidden; }
.contrib-bar .bar-fill { height: 100%; border-radius: 2px; position: absolute; top: 0; }
.contrib-bar .bar-fill.positive { background: #f56c6c; left: 50%; }
.contrib-bar .bar-fill.negative { background: #67c23a; right: 50%; }
.contrib-bar .pnl-value { width: 90px; font-size: 13px; font-weight: 500; text-align: right; flex-shrink: 0; }

/* ===== Filter Tabs ===== */
.filter-tabs { display: flex; gap: 8px; }
.filter-tab { padding: 6px 16px; border-radius: 4px; font-size: 13px; cursor: pointer; background: #f5f7fa; color: #606266; border: 1px solid transparent; transition: all 0.2s; user-select: none; }
.filter-tab:hover { color: #409eff; background: #ecf5ff; }
.filter-tab.active { color: #409eff; background: #ecf5ff; border-color: #b3d8ff; }

/* ===== Table ===== */
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { background: #fafafa; color: #909399; font-weight: 600; text-align: left; padding: 10px 12px; border-bottom: 1px solid #ebeef5; font-size: 12px; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #ebeef5; color: #303133; vertical-align: middle; }
.data-table tbody tr:hover { background: #f5f7fa; }
.data-table tbody tr:last-child td { border-bottom: none; }

/* ===== Tags ===== */
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; line-height: 1.5; font-weight: 400; }
.tag-cn { background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8; }
.tag-hk { background: #fdf6ec; color: #e6a23c; border: 1px solid #faecd8; }
.tag-us { background: #f4f4f5; color: #909399; border: 1px solid #e9e9eb; }
.tag-fund { background: #f0f2ff; color: #6f7ff7; border: 1px solid #d6d9fb; }

/* ===== Stock Link ===== */
.stock-link { color: #409eff; cursor: pointer; text-decoration: none; font-weight: 500; }
.stock-link:hover { color: #66b1ff; }

/* ===== Buttons ===== */
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 4px; font-size: 14px; cursor: pointer; border: 1px solid; transition: all 0.2s; font-weight: 400; line-height: 1; white-space: nowrap; }
.btn-primary { background: #409eff; color: #fff; border-color: #409eff; }
.btn-primary:hover { background: #66b1ff; border-color: #66b1ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-plain { background: #fff; border-color: #dcdfe6; color: #606266; }
.btn-plain:hover { color: #409eff; border-color: #c6e2ff; background: #ecf5ff; }
.btn-sm { padding: 5px 12px; font-size: 12px; }
.btn-text { background: none; border: none; color: #409eff; padding: 4px 8px; font-size: 13px; cursor: pointer; }
.btn-text:hover { color: #66b1ff; }
.btn-text-success { background: none; border: none; color: #67c23a; padding: 4px 8px; font-size: 13px; cursor: pointer; }
.btn-text-success:hover { color: #85ce61; }
.btn-text-danger { background: none; border: none; color: #f56c6c; padding: 4px 8px; font-size: 13px; cursor: pointer; }
.btn-text-danger:hover { color: #f89898; }

/* ===== Progress Bar ===== */
.progress-bar { height: 8px; background: #ebeef5; border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }

/* ===== Update Time ===== */
.update-time { font-size: 12px; color: #a8abb2; display: flex; align-items: center; gap: 4px; }

/* ===== Skeleton ===== */
@keyframes skeleton-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 0.8; } }
.skeleton { background: #e4e7ed; border-radius: 4px; animation: skeleton-pulse 1.5s ease-in-out infinite; }

/* ===== Empty State ===== */
.empty-state { text-align: center; padding: 60px 20px; }
.empty-title { font-size: 16px; font-weight: 600; color: #303133; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #909399; margin-bottom: 20px; line-height: 1.6; }

/* ===== Error State ===== */
.error-state { text-align: center; padding: 40px 20px; }

/* ===== Transition ===== */
.transition-transform { transition: transform 0.3s; }

/* ===== Advice ===== */
.advice-text { font-size: 13px; line-height: 1.7; color: #303133; word-break: break-word; }
.advice-meta { margin-top: 16px; font-size: 12px; color: #909399; text-align: right; }
.advice-error, .advice-loading { text-align: center; padding: 40px 0; }
</style>
