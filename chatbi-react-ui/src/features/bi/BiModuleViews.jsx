import { EChart } from '../../shared/charts/EChart';
import { EmptyState } from '../../shared/components/EmptyState';
import { fetchAuditEvents } from '../../shared/api/client';
import { useEffect, useState } from 'react';

export function AuditView({ data }) {
  const [auditData, setAuditData] = useState(data);
  const [filters, setFilters] = useState({ allowed: '', workspaceId: '', source: '', adminToken: '' });
  const [loadingAudit, setLoadingAudit] = useState(false);
  const currentData = auditData || data || { enabled: true, events: [], total: 0, allowedCount: 0, blockedCount: 0, workspaceEventCount: 0 };

  useEffect(() => {
    setAuditData(data);
  }, [data]);

  const summaryCards = [
    { label: '审计事件', value: currentData.total || 0, unit: '条', note: currentData.enabled ? '审计开关已启用' : '审计开关已关闭' },
    { label: '放行查询', value: currentData.allowedCount || 0, unit: '条', note: '通过安全网关或空间范围校验' },
    { label: '拦截查询', value: currentData.blockedCount || 0, unit: '条', note: '危险 SQL、越权表或未入库查询' },
    { label: '空间相关', value: currentData.workspaceEventCount || 0, unit: '条', note: '带 workspace_id 的企业空间访问' },
  ];
  const sources = Array.from(new Set((currentData.events || []).map((event) => event.source).filter(Boolean)));

  const applyAuditFilters = async () => {
    setLoadingAudit(true);
    try {
      const result = await fetchAuditEvents(filters);
      setAuditData(result);
    } catch (error) {
      setAuditData({ error: error.message });
    } finally {
      setLoadingAudit(false);
    }
  };

  return (
    <section className="module-stack">
      <div className="metric-cards">
        {summaryCards.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}<small>{card.unit}</small></strong>
            <p>{card.note}</p>
          </article>
        ))}
      </div>
      <article className="insight-card">
        <span>Audit Trail</span>
        <strong>SQL Access Governance</strong>
        <p>{currentData.error || '这里展示最近的 SQL 放行与拦截记录，便于回溯 Agent 是否跨业务空间查表、是否触发危险 SQL 或慢查询限制。'}</p>
      </article>
      <section className="audit-filter-card">
        <label>
          <span>结果</span>
          <select value={filters.allowed} onChange={(event) => setFilters((current) => ({ ...current, allowed: event.target.value }))}>
            <option value="">全部</option>
            <option value="true">Allowed</option>
            <option value="false">Blocked</option>
          </select>
        </label>
        <label>
          <span>业务空间 ID</span>
          <input value={filters.workspaceId} onChange={(event) => setFilters((current) => ({ ...current, workspaceId: event.target.value }))} placeholder="job_xxx，可留空" />
        </label>
        <label>
          <span>来源</span>
          <input list="audit-sources" value={filters.source} onChange={(event) => setFilters((current) => ({ ...current, source: event.target.value }))} placeholder="workspace_sql_scope" />
          <datalist id="audit-sources">
            {sources.map((source) => <option key={source} value={source} />)}
          </datalist>
        </label>
        <label>
          <span>管理员令牌</span>
          <input type="password" value={filters.adminToken} onChange={(event) => setFilters((current) => ({ ...current, adminToken: event.target.value }))} placeholder="如后端配置则必填" />
        </label>
        <button type="button" onClick={applyAuditFilters} disabled={loadingAudit}>{loadingAudit ? '筛选中...' : '应用筛选'}</button>
      </section>
      <section className="table-card audit-table">
        <div className="table-head audit-row">
          <span>时间</span>
          <span>结果</span>
          <span>来源</span>
          <span>业务空间</span>
          <span>原因 / SQL 预览</span>
        </div>
        {(currentData.events || []).length === 0 && (
          <div className="table-row single">
            <p>暂无审计事件。执行一次空间内数据问答或 SQL 查询后会自动写入。</p>
          </div>
        )}
        {(currentData.events || []).map((event, index) => (
          <div className="table-row audit-row" key={`${event.timestamp}-${event.queryHash}-${index}`}>
            <span>{event.timestamp || '-'}</span>
            <strong className={event.allowed ? 'audit-allowed' : 'audit-blocked'}>{event.allowed ? 'Allowed' : 'Blocked'}</strong>
            <code>{event.source || '-'}</code>
            <span>{event.workspaceName || event.workspaceId || '全局'}</span>
            <p>
              <b>{event.reason || '无说明'}</b>
              <code>{event.queryPreview || '-'}</code>
            </p>
          </div>
        ))}
      </section>
    </section>
  );
}

export function DashboardView({ data }) {
  if (!data) return <EmptyState text="正在加载看板数据..." />;
  if (data.error) return <EmptyState text={data.error} />;

  const lineOption = {
    grid: { left: 36, right: 20, top: 28, bottom: 30 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.monthlySales.map((item) => item.month) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'line',
        smooth: true,
        symbolSize: 7,
        data: data.monthlySales.map((item) => item.sales),
        areaStyle: { opacity: 0.08 },
      },
    ],
  };

  const barOption = {
    grid: { left: 90, right: 20, top: 20, bottom: 24 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.topProducts.slice(0, 8).map((item) => item.product).reverse() },
    series: [{ type: 'bar', data: data.topProducts.slice(0, 8).map((item) => item.totalSales).reverse() }],
  };

  return (
    <section className="module-stack">
      <div className="metric-cards">
        {data.summaryCards.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}<small>{card.unit}</small></strong>
            <p>{card.note}</p>
          </article>
        ))}
      </div>
      <div className="chart-grid">
        <article className="chart-card">
          <h3>月度销量趋势</h3>
          <EChart option={lineOption} style={{ height: 260 }} />
        </article>
        <article className="chart-card">
          <h3>Top 商品销量</h3>
          <EChart option={barOption} style={{ height: 260 }} />
        </article>
      </div>
    </section>
  );
}

export function MetricsView({ data }) {
  if (!data) return <EmptyState text="正在加载指标体系..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="table-card">
      <div className="table-head">
        <span>指标名称</span>
        <span>口径公式</span>
        <span>数据来源</span>
        <span>应用场景</span>
      </div>
      {data.metrics.map((metric) => (
        <div className="table-row" key={metric.name}>
          <strong>{metric.name}</strong>
          <code>{metric.formula}</code>
          <span>{metric.source}</span>
          <p>{metric.scene}</p>
        </div>
      ))}
    </section>
  );
}

export function SqlAnalysisView({ data, onRun }) {
  if (!data) return <EmptyState text="正在加载 SQL 分析能力..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <div className="template-grid compact">
        {data.capabilities.map((item) => (
          <article className="template-card" key={item.title}>
            <div>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
              <code>{item.example}</code>
            </div>
            <div className="template-actions">
              <button type="button" className="primary" onClick={() => onRun(item.example)}>发起分析</button>
            </div>
          </article>
        ))}
      </div>
      <section className="table-card">
        <div className="table-head three">
          <span>模板</span>
          <span>SQL 示例</span>
          <span>说明</span>
        </div>
        {data.sqlTemplates.map((item) => (
          <div className="table-row three" key={item.name}>
            <strong>{item.name}</strong>
            <code>{item.sql}</code>
            <p>可作为自然语言查数生成 SQL 的参考口径。</p>
          </div>
        ))}
      </section>
    </section>
  );
}

export function AnomaliesView({ data }) {
  if (!data) return <EmptyState text="正在加载异常分析..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <article className="insight-card">
        <span>销量基准线</span>
        <strong>{data.baseline}</strong>
        <p>基于 12 个月销量均值，结合环比和偏离度识别异常。</p>
      </article>
      <div className="anomaly-list">
        {data.items.map((item) => (
          <article className={`anomaly-item ${item.severity}`} key={item.month}>
            <div>
              <strong>{item.month}</strong>
              <span>{item.sales} 件</span>
            </div>
            <div>
              <span>环比 {item.mom}%</span>
              <span>偏离均值 {item.deviation}%</span>
            </div>
            <p>{item.insight}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function UserGrowthView({ data }) {
  if (!data) return <EmptyState text="正在加载用户增长分析..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <div className="metric-cards">
        {data.summary.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}<small>{card.unit}</small></strong>
            <p>用户增长基础指标</p>
          </article>
        ))}
      </div>
      <div className="template-grid compact">
        {data.segments.map((segment) => (
          <article className="template-card" key={segment.name}>
            <strong>{segment.name}</strong>
            <p>{segment.condition}</p>
            <code>{segment.action}</code>
          </article>
        ))}
      </div>
    </section>
  );
}

export function MonetizationView({ data }) {
  if (!data) return <EmptyState text="正在加载变现成本分析..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <div className="metric-cards three-cards">
        {data.summary.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}<small>{card.unit}</small></strong>
            <p>变现分析核心口径</p>
          </article>
        ))}
      </div>
      <section className="table-card">
        <div className="table-head three">
          <span>商品</span>
          <span>销量</span>
          <span>估算收入</span>
        </div>
        {data.topRevenueProducts.map((item) => (
          <div className="table-row three" key={item.product}>
            <strong>{item.product}</strong>
            <span>{item.totalSales} 件</span>
            <p>{item.estimatedRevenue} 元</p>
          </div>
        ))}
      </section>
      <article className="insight-card">
        <span>成本口径说明</span>
        <p>{data.costNote}</p>
      </article>
    </section>
  );
}

export function RagView({ data }) {
  if (!data) return <EmptyState text="正在加载 RAG 知识库说明..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <article className="insight-card">
        <span>默认状态</span>
        <strong>{data.enabled ? '已启用' : '未启用'}</strong>
        <p>{data.positioning}</p>
      </article>
      <div className="template-grid compact">
        {data.scenarios.map((scenario) => (
          <article className="template-card" key={scenario}>
            <strong>{scenario.split('：')[0]}</strong>
            <p>{scenario}</p>
          </article>
        ))}
      </div>
      <section className="table-card">
        {data.suggestedStack.map((item) => (
          <div className="table-row single" key={item}>
            <p>{item}</p>
          </div>
        ))}
      </section>
    </section>
  );
}
