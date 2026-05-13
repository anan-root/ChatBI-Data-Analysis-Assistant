import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import ReactECharts from 'echarts-for-react';
import {
  Activity,
  ArrowUp,
  BarChart3,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  Coins,
  DatabaseZap,
  FileText,
  Gauge,
  HardDriveUpload,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  Loader2,
  MessageSquareText,
  Network,
  Search,
  UsersRound,
  UserRound,
} from 'lucide-react';
import './styles.css';

const API_URL = '/api/chatbi_service';

const suggestions = [
  '查询奇多的价格是多少',
  '运动类商品有多少个',
  '请用python计算123456789*2598等于多少',
  '查询保鲜袋历史12个月销量',
];

const navItems = [
  { key: 'workspaces', icon: <BriefcaseBusiness size={16} />, label: '业务空间' },
  { key: 'importClean', icon: <HardDriveUpload size={16} />, label: '批量导入' },
  { key: 'chat', icon: <MessageSquareText size={16} />, label: '数据问答' },
  { key: 'rag', icon: <Network size={16} />, label: 'RAG 知识库' },
  { key: 'quick', icon: <Search size={16} />, label: '快速查询' },
  { key: 'templates', icon: <BarChart3 size={16} />, label: '分析模板' },
];

const quickQueries = [
  { title: '商品价格', description: '快速查询单个商品的售价', prompt: '查询奇多的价格是多少' },
  { title: '品类数量', description: '统计某类商品数量', prompt: '运动类商品有多少个' },
  { title: '销量明细', description: '查看商品 12 个月销量', prompt: '查询保鲜袋历史12个月销量' },
  { title: '价格对比', description: '比较不同商品或品类价格', prompt: '运动用品平均价格与食品平均价格哪个高' },
];

const analysisTemplates = [
  { title: '销量趋势分析', description: '查询商品月销量并总结趋势变化', prompt: '查询奇多历史12个月销量，并总结销量趋势' },
  { title: '图表生成', description: '生成某商品月度销量图表', prompt: '查询保鲜袋历史12个月销量，并绘制一张月度销量折线图' },
  { title: '销量预测', description: '基于历史销量预测下一期', prompt: '查询保鲜袋历史12个月销量，预测下个月销量' },
  { title: '用户画像', description: '按用户信息和活跃数据做画像', prompt: '分析一下王一珂的用户画像' },
];

const pageCopy = {
  chat: ['📊', '数据分析助手', '像写文档一样提问，让智能体完成查询、计算和分析。', 'Ask with data'],
  workspaces: ['🏢', '业务空间', '先选择业务空间，再进入该空间的报告、看板、指标体系、异常监控和导出入库。', 'Business spaces'],
  sql: ['🧮', 'SQL 分析', '沉淀自然语言查数、聚合统计、对比分析和环比模板。', 'Query studio'],
  dashboard: ['📌', 'BI 看板', '核心指标、月度趋势和商品排行集中展示。', 'BI dashboard'],
  metrics: ['🧭', '指标体系', '沉淀业务口径，统一指标定义、来源和应用场景。', 'Metric system'],
  anomalies: ['⚠️', '异常分析', '识别核心指标波动，辅助定位业务异常月份。', 'Anomaly review'],
  growth: ['🌱', '用户增长', '围绕活跃、分层和运营动作评估用户增长机会。', 'Growth lab'],
  monetization: ['💰', '变现成本', '估算收入贡献，预留成本、ROI 和毛利分析口径。', 'ROI desk'],
  report: ['📝', '分析报告', '自动输出“现象、原因、异常、建议”的结构化报告。', 'Insight report'],
  importClean: ['🧹', '批量导入', '多文件上传后自动清洗、识别业务类型，并支持一键批量入库形成业务空间。', 'Data intake'],
  rag: ['🧠', 'RAG 知识库', '企业知识库增强能力，默认不参与问答链路，可按需启用。', 'Knowledge base'],
  quick: ['🔎', '快速查询', '常用问题一键填入或直接执行，适合先验证字段和结果。', 'Quick query'],
  templates: ['📈', '分析模板', '把重复的数据分析流程做成模板，点击即可发起任务。', 'Analysis templates'],
};

function MarkdownLite({ text }) {
  const html = useMemo(() => {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br />');
  }, [text]);

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function useBiData(activeView) {
  const [data, setData] = useState({
    dashboard: null,
    metrics: null,
    anomalies: null,
    report: null,
    sql: null,
    importClean: null,
    growth: null,
    monetization: null,
    rag: null,
    workspaces: null,
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const endpointMap = {
      dashboard: '/api/bi/dashboard',
      metrics: '/api/bi/metrics',
      anomalies: '/api/bi/anomalies',
      report: '/api/bi/report',
      sql: '/api/bi/sql-analysis',
      importClean: '/api/bi/import-clean',
      growth: '/api/bi/user-growth',
      monetization: '/api/bi/monetization',
      rag: '/api/bi/rag',
      workspaces: '/api/bi/workspaces',
    };
    const endpoint = endpointMap[activeView];
    if (!endpoint) return;
    if (data[activeView]) return;

    setLoading(true);
    fetch(endpoint)
      .then((response) => {
        if (!response.ok) throw new Error(`加载失败：${response.status}`);
        return response.json();
      })
      .then((json) => setData((current) => ({ ...current, [activeView]: json })))
      .catch((error) => setData((current) => ({ ...current, [activeView]: { error: error.message } })))
      .finally(() => setLoading(false));
  }, [activeView, data]);

  return { data, loading };
}

function DashboardView({ data }) {
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
          <ReactECharts option={lineOption} style={{ height: 260 }} />
        </article>
        <article className="chart-card">
          <h3>Top 商品销量</h3>
          <ReactECharts option={barOption} style={{ height: 260 }} />
        </article>
      </div>
    </section>
  );
}

function MetricsView({ data }) {
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

function SqlAnalysisView({ data, onRun }) {
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

function AnomaliesView({ data }) {
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

function ReportView({ data }) {
  if (!data) return <EmptyState text="正在生成分析报告..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="report-card">
      {data.sections.map((section, index) => (
        <article key={section.title}>
          <span>{String(index + 1).padStart(2, '0')}</span>
          <div>
            <h3>{section.title}</h3>
            <p>{section.content}</p>
          </div>
        </article>
      ))}
    </section>
  );
}

function InteractiveCharts({ config, palette }) {
  const [metric, setMetric] = useState(config?.defaultMetric || config?.metrics?.[0] || '');
  const [dimension, setDimension] = useState(config?.defaultDimension || config?.dimensions?.[0] || '');
  const [dateColumn, setDateColumn] = useState(config?.defaultDateColumn || config?.dateColumns?.[0] || '');
  const [timeGrain, setTimeGrain] = useState(config?.timeGrains?.[0]?.key || 'month');
  const [scatterY, setScatterY] = useState((config?.metrics || []).find((item) => item !== metric) || '');

  if (!config || (!config.metrics?.length && !config.dimensions?.length)) return null;

  const barKey = `${metric}||${dimension}`;
  const lineKey = `${metric}||${dateColumn}||${timeGrain}`;
  const scatterKey = `${metric}||${scatterY}`;
  const barData = config.datasets?.bars?.[barKey] || { x: [], y: [] };
  const pieData = config.datasets?.pies?.[barKey] || { data: [] };
  const lineData = config.datasets?.lines?.[lineKey] || { x: [], y: [] };
  const scatterData = config.datasets?.scatters?.[scatterKey] || config.datasets?.scatters?.[`${scatterY}||${metric}`] || { data: [], xName: metric, yName: scatterY };

  const barOption = {
    color: palette,
    grid: { left: 70, right: 20, top: 28, bottom: 70 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: barData.x, axisLabel: { rotate: 28 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', barMaxWidth: 34, data: barData.y }],
  };
  const pieOption = {
    color: palette,
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['42%', '70%'], data: (pieData.data || []).map((item) => ({ name: item.name, value: item.value })) }],
  };
  const lineOption = {
    color: palette,
    grid: { left: 54, right: 20, top: 28, bottom: 36 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: lineData.x },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, symbolSize: 7, areaStyle: { opacity: 0.1 }, data: lineData.y }],
  };
  const scatterOption = {
    color: palette,
    grid: { left: 60, right: 24, top: 30, bottom: 42 },
    tooltip: { trigger: 'item' },
    xAxis: { type: 'value', name: scatterData.xName || metric },
    yAxis: { type: 'value', name: scatterData.yName || scatterY },
    series: [{ type: 'scatter', symbolSize: 8, data: scatterData.data || [] }],
  };

  return (
    <section className="interactive-board">
      <div className="section-title">
        <span>Interactive Charts</span>
        <strong>交互式分析视图</strong>
        <p>切换指标、维度和时间粒度，快速验证不同业务假设。</p>
      </div>
      <div className="chart-controls">
        <label>
          指标
          <select value={metric} onChange={(event) => {
            const nextMetric = event.target.value;
            setMetric(nextMetric);
            if (scatterY === nextMetric) setScatterY((config.metrics || []).find((item) => item !== nextMetric) || '');
          }}>
            {(config.metrics || []).map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <label>
          维度
          <select value={dimension} onChange={(event) => setDimension(event.target.value)}>
            {(config.dimensions || []).map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <label>
          时间字段
          <select value={dateColumn} onChange={(event) => setDateColumn(event.target.value)} disabled={!config.dateColumns?.length}>
            {(config.dateColumns || []).map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
        <label>
          时间粒度
          <select value={timeGrain} onChange={(event) => setTimeGrain(event.target.value)} disabled={!config.dateColumns?.length}>
            {(config.timeGrains || []).map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}
          </select>
        </label>
        <label>
          散点 Y 轴
          <select value={scatterY} onChange={(event) => setScatterY(event.target.value)}>
            {(config.metrics || []).filter((item) => item !== metric).map((item) => <option value={item} key={item}>{item}</option>)}
          </select>
        </label>
      </div>
      <div className="chart-grid workspace-charts">
        <article className="chart-card">
          <h3>{dimension} · {metric} 排行</h3>
          <p>回答：哪个维度贡献最高，长尾是否明显。</p>
          <ReactECharts option={barOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{dimension} · {metric} 结构</h3>
          <p>回答：贡献是否过度集中，Top 维度占比是否健康。</p>
          <ReactECharts option={pieOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{metric} 趋势</h3>
          <p>回答：核心指标在当前时间粒度下是否出现拐点或异常。</p>
          <ReactECharts option={lineOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{metric} × {scatterY || '指标'} 关系</h3>
          <p>回答：两个指标是否协同变化，是否存在离群点。</p>
          <ReactECharts option={scatterOption} style={{ height: 280 }} />
        </article>
      </div>
    </section>
  );
}

function WorkspaceReport({ report, loading }) {
  if (loading) return <EmptyState text="正在生成该业务空间的独立报告..." />;
  if (!report) return null;
  if (report.error) return <EmptyState text={report.error} />;

  const chartPalette = ['#6f8faf', '#88a77d', '#d8a657', '#b8898c', '#8f83b8', '#74a6a1'];

  const chartOptions = (report.charts || []).map((chart) => {
    if (chart.type === 'bar') {
      return {
        chart,
        option: {
          color: chartPalette,
          grid: { left: 70, right: 20, top: 28, bottom: 70 },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: chart.x, axisLabel: { rotate: 28 } },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', barMaxWidth: 34, data: chart.y }],
        },
      };
    }
    if (chart.type === 'pie') {
      return {
        chart,
        option: {
          color: chartPalette,
          tooltip: { trigger: 'item' },
          series: [{ type: 'pie', radius: ['42%', '70%'], data: chart.data.map((item) => ({ name: item.name, value: item.value })) }],
        },
      };
    }
    if (chart.type === 'line') {
      return {
        chart,
        option: {
          color: chartPalette,
          grid: { left: 54, right: 20, top: 28, bottom: 36 },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: chart.x },
          yAxis: { type: 'value' },
          series: [{ type: 'line', smooth: true, symbolSize: 7, areaStyle: { opacity: 0.1 }, data: chart.y }],
        },
      };
    }
    return {
      chart,
      option: {
        color: chartPalette,
        grid: { left: 54, right: 20, top: 28, bottom: 40 },
        tooltip: { trigger: 'item' },
        xAxis: { type: 'value', name: chart.xName },
        yAxis: { type: 'value', name: chart.yName },
        series: [{ type: 'scatter', symbolSize: 8, data: chart.data }],
      },
    };
  });

  return (
    <section className="module-stack">
      {report.executiveSummary && (
        <section className="executive-summary">
          <div className="summary-heading">
            <span>重点结论</span>
            <strong>{report.workspaceName}</strong>
            <p>先看结论，再看图表和模块细节。</p>
          </div>
          <div className="highlight-grid">
            {report.executiveSummary.highlights.map((item) => (
              <article className={`highlight-card ${item.tone}`} key={`${item.label}-${item.title}`}>
                <span>{item.label}</span>
                <strong>{item.title}</strong>
                <p>{item.value}</p>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
          <div className="action-list">
            {report.executiveSummary.actions.map((action) => <p key={action}>{action}</p>)}
          </div>
        </section>
      )}
      {report.analysisPlan && (
        <section className="analysis-plan">
          <div>
            <span>AI 前期判断</span>
            <strong>{report.analysisPlan.framework?.title || report.analysisPlan.name}</strong>
            <p>{report.analysisPlan.focus}</p>
            <small>{report.analysisPlan.inputSummary}</small>
          </div>
          <div className="plan-tags">
            <span>置信度：{report.analysisPlan.confidence}</span>
            {report.analysisPlan.selectedModules.map((module) => <code key={module}>{module}</code>)}
          </div>
        </section>
      )}
      {(report.dataProfile || report.qualityScore || report.recommendedPaths?.length > 0) && (
        <section className="profile-board">
          <div className="section-title">
            <span>Data Readiness</span>
            <strong>数据画像、质量评分与推荐路径</strong>
            <p>{report.dataProfile?.profileSummary}</p>
          </div>
          <div className="profile-grid">
            {report.qualityScore && (
              <article className={`quality-card grade-${report.qualityScore.grade}`}>
                <span>质量评分</span>
                <strong>{report.qualityScore.score}<small>/100</small></strong>
                <p>{report.qualityScore.grade} · {report.qualityScore.summary}</p>
                <em>{report.qualityScore.cleaningSummary}</em>
              </article>
            )}
            {report.dataProfile && (
              <article className="profile-card">
                <span>字段画像</span>
                <div>
                  <b>{report.dataProfile.metricCount}</b><small>指标</small>
                  <b>{report.dataProfile.dimensionCount}</b><small>维度</small>
                  <b>{report.dataProfile.timeCount}</b><small>时间</small>
                </div>
                <p>缺失率 {report.dataProfile.missingRate}% · 重复率 {report.dataProfile.duplicateRate}%</p>
              </article>
            )}
            {report.analysisPlan?.framework && (
              <article className="profile-card">
                <span>方案库命中</span>
                <strong>{report.analysisPlan.framework.title}</strong>
                <p>{report.analysisPlan.framework.goal}</p>
              </article>
            )}
          </div>
          {report.qualityScore?.penalties?.length > 0 && (
            <div className="quality-issues">
              {report.qualityScore.penalties.map((item) => (
                <span key={item.item}>{item.item} -{item.penalty}：{item.detail}</span>
              ))}
            </div>
          )}
          {report.recommendedPaths?.length > 0 && (
            <div className="path-timeline">
              {report.recommendedPaths.map((item) => (
                <article key={`${item.order}-${item.name}`}>
                  <code>{item.order}</code>
                  <strong>{item.name}</strong>
                  <span>{item.readiness}</span>
                  <p>{item.reason}</p>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
      {report.methodology?.length > 0 && (
        <section className="methodology-panel">
          <div className="section-title">
            <span>Methodology</span>
            <strong>专属业务方法论</strong>
            <p>不再只做通用统计，而是按业务类型选择漏斗、分层、区域效率、产品结构、ROI、留存、复购等分析路径。</p>
          </div>
          <div className="method-grid">
            {report.methodology.map((item) => (
              <article className={`method-card fit-${item.fit}`} key={item.name}>
                <div>
                  <span>{item.fit}</span>
                  <strong>{item.name}</strong>
                </div>
                <p>{item.question}</p>
                <small>需要字段：{item.requiredFields?.filter(Boolean).join(' / ')}</small>
                <em>{item.output}</em>
              </article>
            ))}
          </div>
        </section>
      )}
      {report.diagnosticStory?.length > 0 && (
        <section className="diagnostic-story">
          <div className="section-title">
            <span>Diagnostic Flow</span>
            <strong>问题诊断型报告</strong>
            <p>按“现象 → 对比 → 异常 → 归因假设 → 行动建议”的顺序组织结论。</p>
          </div>
          <div className="story-steps">
            {report.diagnosticStory.map((item) => (
              <article key={item.stage}>
                <span>{item.stage}</span>
                <strong>{item.title}</strong>
                <p>{item.content}</p>
              </article>
            ))}
          </div>
        </section>
      )}
      <div className="metric-cards">
        {report.summaryCards.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}<small>{card.unit}</small></strong>
            <p>{card.note}</p>
          </article>
        ))}
      </div>
      {chartOptions.length > 0 && (
        <div className="chart-grid workspace-charts">
          {chartOptions.map(({ chart, option }) => (
            <article className="chart-card" key={chart.title}>
              <h3>{chart.title}</h3>
              <p>{chart.description}</p>
              <div className="chart-intent">
                <span>业务问题</span>
                <strong>{chart.businessQuestion}</strong>
                <p>{chart.whyThisChart}</p>
                <small>{chart.interpretationGuide}</small>
              </div>
              <ReactECharts option={option} style={{ height: 280 }} />
            </article>
          ))}
        </div>
      )}
      <InteractiveCharts config={report.interactiveCharts} palette={chartPalette} />
      {(report.driverAnalysis?.length > 0 || report.benchmarkSummary?.length > 0) && (
        <section className="diagnosis-grid">
          {report.driverAnalysis?.length > 0 && (
            <article className="diagnosis-card">
              <span>Attribution</span>
              <strong>归因诊断</strong>
              {report.driverAnalysis.map((item) => (
                <div className="diagnosis-item" key={`${item.dimension}-${item.driver}`}>
                  <b>{item.dimension} · {item.driver}</b>
                  <p>{item.diagnosis}</p>
                  <small>{item.hypothesis}</small>
                </div>
              ))}
            </article>
          )}
          {report.benchmarkSummary?.length > 0 && (
            <article className="diagnosis-card">
              <span>Benchmark</span>
              <strong>对比基准</strong>
              {report.benchmarkSummary.map((item) => (
                <div className="diagnosis-item" key={item.name}>
                  <b>{item.name}：{item.value}</b>
                  <p>{item.baseline}</p>
                  <small>{item.diagnosis}</small>
                </div>
              ))}
            </article>
          )}
        </section>
      )}
      {(report.anomalyDiagnosis?.length > 0 || report.significanceTests?.length > 0 || report.priorityActions?.length > 0) && (
        <section className="strategy-board">
          <div className="section-title">
            <span>Decision Layer</span>
            <strong>诊断深度与策略优先级</strong>
            <p>把异常、原因假设、显著性和行动建议放在同一层，方便企业例会直接讨论。</p>
          </div>
          <div className="strategy-columns">
            <article>
              <span>异常原因假设</span>
              {(report.anomalyDiagnosis || []).map((item) => (
                <div key={`${item.period}-${item.severity}`}>
                  <strong>{item.period} · {item.severity}</strong>
                  <p>{item.finding}</p>
                  <small>{item.possibleCauses?.join(' / ')}</small>
                </div>
              ))}
            </article>
            <article>
              <span>显著性与可信度</span>
              {(report.significanceTests || []).map((item) => (
                <div key={item.name}>
                  <strong>{item.name}</strong>
                  <p>{item.result}</p>
                  <small>{item.method} · 可信度 {item.confidence}</small>
                </div>
              ))}
            </article>
            <article>
              <span>行动优先级</span>
              {(report.priorityActions || []).map((item) => (
                <div className="priority-item" key={`${item.priority}-${item.title}`}>
                  <code>{item.priority}</code>
                  <strong>{item.title}</strong>
                  <p>{item.rationale}</p>
                  <small>{item.nextStep}</small>
                </div>
              ))}
            </article>
          </div>
        </section>
      )}
      <section className="report-card">
        {report.sections.map((section, index) => (
          <article key={section.title}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h3>{section.title}</h3>
              <p>{section.content}</p>
            </div>
          </article>
        ))}
      </section>
      <section className="table-card">
        <div className="table-head three">
          <span>指标名称</span>
          <span>口径</span>
          <span>当前值</span>
        </div>
        {(report.metricCatalog || []).map((item) => (
          <div className="table-row three" key={item.name}>
            <strong>{item.name}</strong>
            <code>{item.formula}</code>
            <p>{item.value}</p>
          </div>
        ))}
      </section>
      {report.topCategories?.length > 0 && (
        <section className="table-card">
          <div className="table-head three">
            <span>贡献排行</span>
            <span>数值</span>
            <span>说明</span>
          </div>
          {report.topCategories.map((item) => (
            <div className="table-row three" key={item.name}>
              <strong>{item.name}</strong>
              <span>{item.value}</span>
              <p>核心维度贡献</p>
            </div>
          ))}
        </section>
      )}
      {report.monitorItems?.length > 0 && (
        <section className="table-card">
          <div className="table-head">
            <span>周期</span>
            <span>指标值</span>
            <span>环比/偏离</span>
            <span>监控建议</span>
          </div>
          {report.monitorItems.map((item) => (
            <div className="table-row" key={item.period}>
              <strong>{item.period}</strong>
              <span>{item.value}</span>
              <code>{item.mom}% / {item.deviation}%</code>
              <p>{item.suggestion}</p>
            </div>
          ))}
        </section>
      )}
      <div className="template-grid compact">
        {(report.growthSuggestions || []).map((item) => (
          <article className="template-card" key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.content}</p>
          </article>
        ))}
        {(report.monetizationSuggestions || []).map((item) => (
          <article className="template-card" key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.content}</p>
          </article>
        ))}
      </div>
      {report.sqlTemplates?.length > 0 && (
        <section className="table-card">
          <div className="table-head three">
            <span>SQL 模板</span>
            <span>语句</span>
            <span>用途</span>
          </div>
          {report.sqlTemplates.map((item) => (
            <div className="table-row three" key={item.name}>
              <strong>{item.name}</strong>
              <code>{item.sql}</code>
              <p>业务空间专属查询</p>
            </div>
          ))}
        </section>
      )}
      {report.cleaningQuality && (
        <article className="insight-card">
          <span>数据清洗质量</span>
          <strong>去重 {report.cleaningQuality.removedDuplicateRows} 行</strong>
          <p>缺失值处理 {report.cleaningQuality.fillActions?.length || 0} 个字段，类型转换 {report.cleaningQuality.typeChanges?.length || 0} 个字段。</p>
        </article>
      )}
      <a className="text-link report-download" href={`/api/bi/workspaces/${report.jobId}/export-report`}>下载该业务报告</a>
    </section>
  );
}

function WorkspaceModulePanel({ report, activeModule }) {
  if (!report) return null;
  if (activeModule === 'overview') {
    return (
      <section className="module-stack compact-stack">
        <section className="profile-board">
          <div className="section-title">
            <span>Overview</span>
            <strong>{report.workspaceName}</strong>
            <p>{report.dataProfile?.profileSummary}</p>
          </div>
          <div className="profile-grid">
            <article className={`quality-card grade-${report.qualityScore?.grade}`}>
              <span>质量评分</span>
              <strong>{report.qualityScore?.score}<small>/100</small></strong>
              <p>{report.qualityScore?.grade} · {report.qualityScore?.summary}</p>
            </article>
            <article className="profile-card">
              <span>方案库</span>
              <strong>{report.analysisPlan?.framework?.title || report.analysisPlan?.name}</strong>
              <p>{report.analysisPlan?.framework?.goal}</p>
            </article>
            <article className="profile-card">
              <span>字段结构</span>
              <div>
                <b>{report.dataProfile?.metricCount}</b><small>指标</small>
                <b>{report.dataProfile?.dimensionCount}</b><small>维度</small>
                <b>{report.dataProfile?.timeCount}</b><small>时间</small>
              </div>
              <p>缺失率 {report.dataProfile?.missingRate}% · 重复率 {report.dataProfile?.duplicateRate}%</p>
            </article>
          </div>
          <div className="path-timeline">
            {(report.recommendedPaths || []).map((item) => (
              <article key={`${item.order}-${item.name}`}>
                <code>{item.order}</code>
                <strong>{item.name}</strong>
                <span>{item.readiness}</span>
                <p>{item.reason}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    );
  }
  if (activeModule === 'dashboard') {
    return (
      <section className="module-stack compact-stack">
        <div className="metric-cards">
          {(report.summaryCards || []).map((card) => (
            <article className="metric-card" key={card.label}>
              <span>{card.label}</span>
              <strong>{card.value}<small>{card.unit}</small></strong>
              <p>{card.note}</p>
            </article>
          ))}
        </div>
        <InteractiveCharts config={report.interactiveCharts} palette={['#6f8faf', '#88a77d', '#d8a657', '#b8898c', '#8f83b8', '#74a6a1']} />
      </section>
    );
  }
  if (activeModule === 'metrics') {
    return (
      <section className="module-stack compact-stack">
        <section className="table-card">
          <div className="table-head three">
            <span>指标名称</span>
            <span>口径</span>
            <span>当前值</span>
          </div>
          {(report.metricCatalog || []).map((item) => (
            <div className="table-row three" key={item.name}>
              <strong>{item.name}</strong>
              <code>{item.formula}</code>
              <p>{item.value}</p>
            </div>
          ))}
        </section>
        <section className="table-card">
          <div className="table-head three">
            <span>SQL 模板</span>
            <span>语句</span>
            <span>用途</span>
          </div>
          {(report.sqlTemplates || []).map((item) => (
            <div className="table-row three" key={item.name}>
              <strong>{item.name}</strong>
              <code>{item.sql}</code>
              <p>该业务空间专属查询</p>
            </div>
          ))}
        </section>
      </section>
    );
  }
  if (activeModule === 'anomaly') {
    return (
      <section className="module-stack compact-stack">
        <section className="strategy-board">
          <div className="section-title">
            <span>Anomaly</span>
            <strong>异常监控与原因假设</strong>
            <p>按时间趋势识别波动周期，并给出下一步检查方向。</p>
          </div>
          <div className="strategy-columns">
            {(report.anomalyDiagnosis || []).map((item) => (
              <article key={`${item.period}-${item.severity}`}>
                <span>{item.period} · {item.severity}</span>
                <strong>{item.finding}</strong>
                <p>{item.possibleCauses?.join(' / ')}</p>
                <small>{item.nextCheck}</small>
              </article>
            ))}
          </div>
        </section>
      </section>
    );
  }
  if (activeModule === 'growth') {
    return (
      <section className="template-grid compact">
        {(report.growthSuggestions || []).map((item) => (
          <article className="template-card" key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.content}</p>
          </article>
        ))}
        {(report.driverAnalysis || []).map((item) => (
          <article className="template-card" key={`${item.dimension}-${item.driver}`}>
            <strong>{item.dimension} · {item.driver}</strong>
            <p>{item.diagnosis}</p>
          </article>
        ))}
      </section>
    );
  }
  if (activeModule === 'finance') {
    return (
      <section className="template-grid compact">
        {(report.monetizationSuggestions || []).map((item) => (
          <article className="template-card" key={item.title}>
            <strong>{item.title}</strong>
            <p>{item.content}</p>
          </article>
        ))}
        {(report.priorityActions || []).filter((item) => /ROI|成本|预算|收入|费用|利润/.test(item.title + item.rationale)).map((item) => (
          <article className="template-card" key={`${item.priority}-${item.title}`}>
            <strong>{item.priority} · {item.title}</strong>
            <p>{item.nextStep}</p>
          </article>
        ))}
      </section>
    );
  }
  if (activeModule === 'inventory') {
    return (
      <section className="template-grid compact">
        {(report.methodology || []).filter((item) => /库存|周转|缺货|滞销|SKU/.test(item.name + item.question)).map((item) => (
          <article className="template-card" key={item.name}>
            <strong>{item.name}</strong>
            <p>{item.question}</p>
            <code>{item.output}</code>
          </article>
        ))}
      </section>
    );
  }
  if (activeModule === 'export') {
    return (
      <section className="module-stack compact-stack">
        <article className="insight-card">
          <span>数据清洗质量</span>
          <strong>去重 {report.cleaningQuality?.removedDuplicateRows} 行</strong>
          <p>缺失值处理 {report.cleaningQuality?.fillActions?.length || 0} 个字段，类型转换 {report.cleaningQuality?.typeChanges?.length || 0} 个字段。</p>
        </article>
        <a className="text-link report-download" href={`/api/bi/workspaces/${report.jobId}/export-report`}>下载该业务报告</a>
      </section>
    );
  }
  return <WorkspaceReport report={report} loading={false} />;
}

const workspaceGroupModes = [
  { key: 'month', label: '按上传时间', hint: '适合周期复盘和月度项目归档' },
  { key: 'name', label: '按名称', hint: '适合按项目、渠道、活动名称检索' },
  { key: 'status', label: '按入库状态', hint: '区分已入库与待确认数据' },
  { key: 'manual', label: '手动分组', hint: '前端本地保存，可先快速调整' },
];

const businessSpaceOrder = ['销售经营', '用户运营', '财务经营', '库存管理', '运营分析', '通用业务'];
const businessSpaceMeta = {
  销售经营: { icon: '01', tone: 'sales' },
  用户运营: { icon: '02', tone: 'user' },
  财务经营: { icon: '03', tone: 'finance' },
  库存管理: { icon: '04', tone: 'inventory' },
  运营分析: { icon: '05', tone: 'operation' },
  通用业务: { icon: '06', tone: 'general' },
};

function readManualWorkspaceGroups() {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(window.localStorage.getItem('chatbi_manual_workspace_groups') || '{}');
  } catch {
    return {};
  }
}

function saveManualWorkspaceGroups(groups) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('chatbi_manual_workspace_groups', JSON.stringify(groups));
}

function formatWorkspaceMonth(createdAt) {
  if (!createdAt) return '未记录上传时间';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return '未记录上传时间';
  return `${date.getFullYear()}年${String(date.getMonth() + 1).padStart(2, '0')}月上传`;
}

function formatWorkspaceTime(createdAt) {
  if (!createdAt) return '未记录';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return createdAt;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function inferNameGroup(workspace) {
  const rawName = (workspace.name || workspace.sourceFile || '未命名项目').replace(/\.[^.]+$/, '');
  const parts = rawName.split(/[_\-—\s]+/).filter(Boolean);
  const firstUsefulPart = parts.find((part) => part !== workspace.businessType && part.length >= 2);
  if (firstUsefulPart) return `${firstUsefulPart}项目组`;
  return `${rawName.slice(0, 10)}项目组`;
}

function buildWorkspaceGroups(workspaces, mode, manualGroups) {
  const bucket = new Map();
  [...workspaces]
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .forEach((workspace) => {
      let label = formatWorkspaceMonth(workspace.createdAt);
      if (mode === 'name') label = inferNameGroup(workspace);
      if (mode === 'status') label = workspace.imported ? '已入库数据' : '待入库数据';
      if (mode === 'manual') label = manualGroups[workspace.workspaceId] || '未分组项目';

      if (!bucket.has(label)) {
        bucket.set(label, {
          key: `${mode}:${label}`,
          label,
          workspaces: [],
          importedCount: 0,
          latestAt: null,
        });
      }
      const group = bucket.get(label);
      group.workspaces.push(workspace);
      group.importedCount += workspace.imported ? 1 : 0;
      if (!group.latestAt || new Date(workspace.createdAt || 0) > new Date(group.latestAt || 0)) {
        group.latestAt = workspace.createdAt;
      }
    });

  return Array.from(bucket.values()).map((group) => ({
    ...group,
    count: group.workspaces.length,
  }));
}

function WorkspacesView({ data }) {
  const [level, setLevel] = useState('spaces');
  const [selectedBusinessType, setSelectedBusinessType] = useState(null);
  const [selectedGroupKey, setSelectedGroupKey] = useState(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [report, setReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [activeModule, setActiveModule] = useState(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [groupMode, setGroupMode] = useState('month');
  const [manualGroups, setManualGroups] = useState(readManualWorkspaceGroups);
  const [manualEditorOpen, setManualEditorOpen] = useState(false);

  if (!data) return <EmptyState text="正在加载业务空间..." />;
  if (data.error) return <EmptyState text={data.error} />;

  const workspaces = data.workspaces || [];
  const groupedBusinessSpaces = data.groups?.length
    ? data.groups
    : businessSpaceOrder
        .map((businessType) => {
          const items = workspaces.filter((workspace) => workspace.businessType === businessType);
          return items.length ? { businessType, count: items.length, workspaces: items } : null;
        })
        .filter(Boolean);
  const businessSpaces = groupedBusinessSpaces
    .slice()
    .sort((a, b) => businessSpaceOrder.indexOf(a.businessType) - businessSpaceOrder.indexOf(b.businessType));
  const selectedSpace = businessSpaces.find((item) => item.businessType === selectedBusinessType);
  const selectedSpaceWorkspaces = selectedSpace?.workspaces || workspaces.filter((item) => item.businessType === selectedBusinessType);
  const projectGroups = buildWorkspaceGroups(selectedSpaceWorkspaces, groupMode, manualGroups);
  const selectedGroup = projectGroups.find((item) => item.key === selectedGroupKey);

  const updateManualGroup = (workspaceId, value) => {
    setManualGroups((current) => {
      const next = { ...current, [workspaceId]: value || '未分组项目' };
      saveManualWorkspaceGroups(next);
      return next;
    });
  };

  const resetReport = () => {
    setSelectedWorkspace(null);
    setReport(null);
    setActiveModule(null);
    setReportOpen(false);
    setLoadingReport(false);
  };

  const goSpaces = () => {
    setLevel('spaces');
    setSelectedBusinessType(null);
    setSelectedGroupKey(null);
    setManualEditorOpen(false);
    resetReport();
  };

  const goGroups = () => {
    setLevel('groups');
    setSelectedGroupKey(null);
    resetReport();
  };

  const goFiles = () => {
    setLevel('files');
    resetReport();
  };

  const openBusinessSpace = (businessType) => {
    setSelectedBusinessType(businessType);
    setSelectedGroupKey(null);
    setManualEditorOpen(false);
    resetReport();
    setLevel('groups');
  };

  const openProjectGroup = (group) => {
    setSelectedGroupKey(group.key);
    resetReport();
    setLevel('files');
  };

  const openReport = async (workspace) => {
    setSelectedWorkspace(workspace);
    setLevel('report');
    setLoadingReport(true);
    setReport(null);
    setActiveModule(null);
    setReportOpen(false);
    try {
      const response = await fetch(`/api/bi/workspaces/${workspace.workspaceId}/report`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '报告生成失败');
      setReport(result);
    } catch (error) {
      setReport({ error: error.message });
    } finally {
      setLoadingReport(false);
    }
  };

  const breadcrumbItems = [
    { label: '业务空间', onClick: goSpaces, active: level === 'spaces' },
    selectedBusinessType && { label: selectedBusinessType, onClick: goGroups, active: level === 'groups' },
    selectedGroup && { label: selectedGroup.label, onClick: goFiles, active: level === 'files' },
    selectedWorkspace && { label: selectedWorkspace.name, active: level === 'report' },
  ].filter(Boolean);

  return (
    <section className="module-stack workspace-flow">
      {level !== 'spaces' && (
        <nav className="workspace-breadcrumb" aria-label="业务空间路径">
          {breadcrumbItems.map((item, index) => (
            <React.Fragment key={`${item.label}-${index}`}>
              <button className={item.active ? 'active' : ''} type="button" onClick={item.onClick} disabled={!item.onClick}>
                {item.label}
              </button>
              {index < breadcrumbItems.length - 1 && <span>/</span>}
            </React.Fragment>
          ))}
        </nav>
      )}

      {level === 'spaces' && (
        <section className="workspace-group workspace-index-panel">
          {businessSpaces.length === 0 && <EmptyState text="还没有业务空间。先在批量导入模块上传文件。" />}
          <div className="workspace-grid space-entry-grid">
            {businessSpaces.map((space) => {
              const meta = businessSpaceMeta[space.businessType] || businessSpaceMeta.通用业务;
              return (
                <button className={`workspace-card space-entry-card tone-${meta.tone}`} key={space.businessType} type="button" onClick={() => openBusinessSpace(space.businessType)}>
                  <i>{meta.icon}</i>
                  <strong>{space.businessType}</strong>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {level === 'groups' && selectedBusinessType && (
        <section className="workspace-group">
          <div className="workspace-level-head">
            <div className="section-title">
              <span>{selectedSpaceWorkspaces.length} 个文件空间</span>
              <strong>{selectedBusinessType}</strong>
              <p>先按业务规则归成项目组，再进入项目组检索文件与报告。</p>
            </div>
            <div className="workspace-group-controls">
              {workspaceGroupModes.map((mode) => (
                <button className={groupMode === mode.key ? 'active' : ''} type="button" key={mode.key} onClick={() => { setGroupMode(mode.key); setSelectedGroupKey(null); }}>
                  <strong>{mode.label}</strong>
                  <span>{mode.hint}</span>
                </button>
              ))}
            </div>
          </div>

          {groupMode === 'manual' && (
            <div className="manual-group-panel">
              <button className="link-button" type="button" onClick={() => setManualEditorOpen((current) => !current)}>
                {manualEditorOpen ? '收起手动调整' : '管理手动分组'}
              </button>
              {manualEditorOpen && (
                <div className="manual-group-editor">
                  {selectedSpaceWorkspaces.map((workspace) => (
                    <label key={workspace.workspaceId}>
                      <span>{workspace.name}</span>
                      <input value={manualGroups[workspace.workspaceId] || ''} onChange={(event) => updateManualGroup(workspace.workspaceId, event.target.value)} placeholder="输入项目组名称" />
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="workspace-grid project-group-grid">
            {projectGroups.map((group) => (
              <button className="workspace-card project-group-card" key={group.key} type="button" onClick={() => openProjectGroup(group)}>
                <span>Project Group</span>
                <strong>{group.label}</strong>
                <p>{group.count} 个文件 · {group.importedCount} 个已入库 · 最近 {formatWorkspaceTime(group.latestAt)}</p>
              </button>
            ))}
          </div>
        </section>
      )}

      {level === 'files' && selectedGroup && (
        <section className="workspace-group">
          <div className="section-title">
            <span>{selectedGroup.count} 个文件</span>
            <strong>{selectedGroup.label}</strong>
            <p>项目组内只展示文件和对应报告入口，点击报告后再进入独立封面。</p>
          </div>
          <div className="workspace-file-list">
            {selectedGroup.workspaces.map((workspace) => (
              <article className="workspace-file-card" key={workspace.workspaceId}>
                <div>
                  <span>{workspace.imported ? '已入库' : '待入库'}</span>
                  <strong>{workspace.name}</strong>
                  <p>{workspace.sourceFile}</p>
                </div>
                <code>{workspace.rows} 行 / {workspace.columns} 字段 / {workspace.moduleCount} 个可用模块</code>
                <button type="button" onClick={() => openReport(workspace)}>查看报告</button>
              </article>
            ))}
          </div>
        </section>
      )}

      {level === 'report' && selectedWorkspace && (
        <section className="workspace-detail report-shell">
          <article className="report-cover">
            <span>Report</span>
            <strong>{report?.workspaceName || selectedWorkspace.name}</strong>
            <button type="button" onClick={() => { setReportOpen((current) => !current); if (reportOpen) setActiveModule(null); }} disabled={loadingReport || Boolean(report?.error)}>
              {reportOpen ? '隐藏报告内容' : '展开报告内容'}
            </button>
          </article>
          {loadingReport && <EmptyState text="正在生成该文件的独立报告..." />}
          {report?.error && <EmptyState text={report.error} />}
          {report && !report.error && reportOpen && (
            <>
              <div className="workspace-tabs">
                {(report.workspaceModules || []).map((module) => (
                  <button className={activeModule === module.key ? 'active' : ''} type="button" key={module.key} onClick={() => setActiveModule(module.key)}>
                    <strong>{module.label}</strong>
                    <span>{module.description}</span>
                  </button>
                ))}
              </div>
              {!activeModule && <EmptyState text="报告内容已折叠。请选择一个模块查看细节。" />}
              {activeModule && (activeModule === 'report' ? <WorkspaceReport report={report} loading={false} /> : <WorkspaceModulePanel report={report} activeModule={activeModule} />)}
            </>
          )}
        </section>
      )}
    </section>
  );
}

function ImportCleanView({ data }) {
  const [job, setJob] = useState(null);
  const [jobList, setJobList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [batchCommitting, setBatchCommitting] = useState(false);
  const [tableName, setTableName] = useState('');
  const [statusText, setStatusText] = useState('');
  const [workspaceReport, setWorkspaceReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    fetch('/api/bi/import-clean/jobs')
      .then((response) => response.ok ? response.json() : { jobs: [] })
      .then((result) => setJobList(result.jobs || []))
      .catch(() => setJobList([]));
  }, []);

  const handleUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length || uploading) return;
    setUploading(true);
    setStatusText(files.length > 1 ? `正在批量上传并清洗 ${files.length} 个文件...` : '正在上传并自动清洗...');
    const formData = new FormData();
    files.forEach((file) => formData.append(files.length > 1 ? 'files' : 'file', file));

    try {
      const response = await fetch(files.length > 1 ? '/api/bi/import-clean/upload-batch' : '/api/bi/import-clean/upload', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '上传清洗失败');
      if (files.length > 1) {
        const jobs = (result.results || []).filter((item) => item.ok && item.job).map((item) => item.job);
        if (jobs.length > 0) {
          setJob(jobs[0]);
          setTableName(jobs[0].suggestedTableName || '');
          setJobList((current) => [...jobs, ...current.filter((item) => !jobs.some((nextJob) => nextJob.jobId === item.jobId))].slice(0, 30));
        }
        setStatusText(`批量清洗完成：成功 ${result.success} 个，失败 ${result.failed} 个。`);
      } else {
        setJob(result);
        setTableName(result.suggestedTableName || '');
        setJobList((current) => [result, ...current.filter((item) => item.jobId !== result.jobId)].slice(0, 20));
        setStatusText(`清洗完成：${result.rowsBefore} 行 → ${result.rowsAfter} 行`);
      }
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const handleBatchCommit = async () => {
    const pendingJobs = jobList.filter((item) => !item.imported);
    if (!pendingJobs.length || batchCommitting) return;
    setBatchCommitting(true);
    setStatusText(`正在批量入库 ${pendingJobs.length} 个业务空间...`);
    try {
      const response = await fetch('/api/bi/import-clean/jobs/batch-commit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: pendingJobs.map((item) => item.jobId) }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '批量入库失败');
      const tableByJobId = Object.fromEntries((result.results || []).filter((item) => item.ok).map((item) => [item.jobId, item.dbTable]));
      setJobList((current) => current.map((item) => tableByJobId[item.jobId] ? { ...item, imported: true, dbTable: tableByJobId[item.jobId] } : item));
      if (job && tableByJobId[job.jobId]) setJob({ ...job, imported: true, dbTable: tableByJobId[job.jobId] });
      setStatusText(`批量入库完成：成功 ${result.success} 个，失败 ${result.failed} 个。`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setBatchCommitting(false);
    }
  };

  const handleCommit = async () => {
    if (!job || committing) return;
    setCommitting(true);
    setStatusText('正在确认入库...');
    try {
      const response = await fetch(`/api/bi/import-clean/jobs/${job.jobId}/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_name: tableName }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '确认入库失败');
      const nextJob = { ...job, imported: true, dbTable: result.dbTable };
      setJob(nextJob);
      setJobList((current) => current.map((item) => item.jobId === job.jobId ? nextJob : item));
      setStatusText(`已入库：${result.dbTable}（${result.rows} 行）`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setCommitting(false);
    }
  };

  const handleWorkspaceReport = async (targetJob = job) => {
    if (!targetJob) return;
    setReportLoading(true);
    setWorkspaceReport(null);
    try {
      const response = await fetch(`/api/bi/workspaces/${targetJob.jobId}/report`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '报告生成失败');
      setWorkspaceReport(result);
      setStatusText(`已生成业务空间报告：${result.workspaceName}`);
    } catch (error) {
      setWorkspaceReport({ error: error.message });
      setStatusText(error.message);
    } finally {
      setReportLoading(false);
    }
  };

  if (!data) return <EmptyState text="正在加载导入导出模块..." />;
  if (data.error) return <EmptyState text={data.error} />;

  return (
    <section className="module-stack">
      <article className="insight-card">
        <span>模块状态</span>
        <strong>{data.status === 'planned' ? '可规划接入' : data.status}</strong>
        <p>已接入 CSV 上传、自动清洗、清洗文件下载和确认入库；Excel 解析依赖见 README。</p>
      </article>
      <section className="upload-panel">
        <div>
          <span>批量文件导入</span>
          <strong>上传后自动清洗并生成业务空间</strong>
          <p>支持一次选择多个 CSV / XLSX / XLS，系统自动识别业务类型，并按不同业务空间存放。</p>
        </div>
        <label className="upload-button">
          {uploading ? '处理中...' : '选择文件'}
          <input type="file" accept=".csv,.xlsx,.xls" multiple onChange={handleUpload} disabled={uploading} />
        </label>
      </section>
      {statusText && <div className="status-line">{statusText}</div>}
      {job && (
        <section className="import-result">
          <div className="import-summary">
            <article>
              <span>原始行数</span>
              <strong>{job.rowsBefore}</strong>
            </article>
            <article>
              <span>清洗后行数</span>
              <strong>{job.rowsAfter}</strong>
            </article>
            <article>
              <span>去重行数</span>
              <strong>{job.removedDuplicateRows}</strong>
            </article>
            <article>
              <span>字段数</span>
              <strong>{job.columnsAfter}</strong>
            </article>
          </div>
          <div className="import-actions">
            <input value={tableName} onChange={(event) => setTableName(event.target.value)} placeholder="入库表名" />
            <button type="button" onClick={handleCommit} disabled={committing || job.imported}>{job.imported ? '已入库' : '确认入库'}</button>
            <button type="button" onClick={handleBatchCommit} disabled={batchCommitting || jobList.every((item) => item.imported)}>{batchCommitting ? '批量入库中...' : '批量入库'}</button>
            <button type="button" onClick={() => handleWorkspaceReport(job)} disabled={reportLoading}>生成独立报告</button>
            <a href={job.downloadUrl}>下载清洗文件</a>
          </div>
          <section className="table-card">
            <div className="table-head three">
              <span>字段</span>
              <span>类型</span>
              <span>缺失处理</span>
            </div>
            {job.columns.slice(0, 8).map((column) => (
              <div className="table-row three" key={column.name}>
                <strong>{column.name}</strong>
                <span>{column.dtype}</span>
                <p>{column.missingBefore} → {column.missingAfter}</p>
              </div>
            ))}
          </section>
        </section>
      )}
      <WorkspaceReport report={workspaceReport} loading={reportLoading} />
      <div className="flow-list">
        {data.workflow.map((step, index) => (
          <div className="flow-item" key={step}>
            <span>{index + 1}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>
      <div className="template-grid compact">
        {data.cleaningRules.map((rule) => (
          <article className="template-card" key={rule.rule}>
            <strong>{rule.rule}</strong>
            <p>{rule.description}</p>
          </article>
        ))}
      </div>
      <section className="table-card">
        {data.exportOptions.map((option) => (
          <div className="table-row three" key={option.label}>
            <strong>{option.label}</strong>
            <p>{option.description}</p>
            <a className="text-link" href={option.url}>下载</a>
          </div>
        ))}
      </section>
      {jobList.length > 0 && (
        <section className="table-card">
          <div className="table-head three">
            <span>最近任务</span>
            <span>业务空间/清洗结果</span>
            <span>状态</span>
          </div>
          {jobList.slice(0, 5).map((item) => (
            <div className="table-row three" key={item.jobId}>
              <strong>{item.originalFilename}</strong>
              <span>{item.businessType} · {item.rowsBefore} → {item.rowsAfter} 行</span>
              <button type="button" className="link-button" onClick={() => { setJob(item); setTableName(item.suggestedTableName || ''); handleWorkspaceReport(item); }}>{item.imported ? '已入库/看报告' : '看报告'}</button>
            </div>
          ))}
        </section>
      )}
    </section>
  );
}

function UserGrowthView({ data }) {
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

function MonetizationView({ data }) {
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

function RagView({ data }) {
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

function TemplateView({ activeView, loading, onApply, onRun }) {
  const templateList = activeView === 'quick' ? quickQueries : analysisTemplates;
  return (
    <section className="template-grid" aria-label={pageCopy[activeView][1]}>
      {templateList.map((template) => (
        <article className="template-card" key={template.title}>
          <div>
            <strong>{template.title}</strong>
            <p>{template.description}</p>
            <code>{template.prompt}</code>
          </div>
          <div className="template-actions">
            <button type="button" onClick={() => onApply(template.prompt)}>填入输入框</button>
            <button type="button" className="primary" onClick={() => onRun(template.prompt)} disabled={loading}>立即执行</button>
          </div>
        </article>
      ))}
    </section>
  );
}

function EmptyState({ text }) {
  return <div className="empty-state">{text}</div>;
}

function App() {
  const [activeView, setActiveView] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [input, setInput] = useState('查询奇多的价格是多少');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好，我是 ChatBI 数据分析助手。可以帮你查商品价格、算销量、跑 Python、做图表和预测。' },
  ]);
  const sessionId = useRef(`web_${Date.now()}`);
  const { data: biData, loading: biLoading } = useBiData(activeView);

  const sendMessage = async (text = input) => {
    const content = text.trim();
    if (!content || loading) return;

    setActiveView('chat');
    const userMessage = { role: 'user', content };
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const requestHistory = messages
        .filter((item) => item.role === 'user' || item.role === 'assistant')
        .map((item) => ({ role: item.role, content: item.content }));

      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: sessionId.current, message: content, history: requestHistory }),
      });

      if (!response.ok) throw new Error(`接口请求失败：${response.status}`);
      const result = await response.json();
      setMessages((current) => [...current, { role: 'assistant', content: result.message || '没有拿到返回内容。' }]);
    } catch (error) {
      setMessages((current) => [...current, { role: 'assistant', content: `请求失败：${error.message}\n请确认后端服务已启动后再试。` }]);
    } finally {
      setLoading(false);
    }
  };

  const [icon, title, description, eyebrow] = pageCopy[activeView];

  const renderContent = () => {
    if (activeView === 'chat') {
      return (
        <>
          <div className="suggestions">
            {suggestions.map((item) => (
              <button key={item} type="button" onClick={() => sendMessage(item)} disabled={loading}>{item}</button>
            ))}
          </div>
          <ChatMessages messages={messages} loading={loading} />
        </>
      );
    }
    if (activeView === 'workspaces') return <WorkspacesView data={biData.workspaces} />;
    if (activeView === 'sql') return <SqlAnalysisView data={biData.sql} onRun={sendMessage} />;
    if (activeView === 'dashboard') return <DashboardView data={biData.dashboard} loading={biLoading} />;
    if (activeView === 'metrics') return <MetricsView data={biData.metrics} loading={biLoading} />;
    if (activeView === 'anomalies') return <AnomaliesView data={biData.anomalies} loading={biLoading} />;
    if (activeView === 'growth') return <UserGrowthView data={biData.growth} />;
    if (activeView === 'monetization') return <MonetizationView data={biData.monetization} />;
    if (activeView === 'report') return <ReportView data={biData.report} loading={biLoading} />;
    if (activeView === 'importClean') return <ImportCleanView data={biData.importClean} />;
    if (activeView === 'rag') return <RagView data={biData.rag} />;
    return <TemplateView activeView={activeView} loading={loading} onApply={setInput} onRun={sendMessage} />;
  };

  return (
    <main className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="workspace-mark">BI</div>
          <div className="workspace-copy">
            <strong>ChatBI</strong>
            <span>Data Studio</span>
          </div>
          <button className="sidebar-toggle" type="button" onClick={() => setSidebarCollapsed((current) => !current)} aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'} title={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}>
            {sidebarCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <button className={activeView === item.key ? 'active' : ''} key={item.key} type="button" onClick={() => setActiveView(item.key)} title={item.label}>
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>今日建议</span>
          <p>先用 BI 看板观察趋势，再进入数据问答追问原因。</p>
        </div>
      </aside>

      <section className="workspace">
        <header className="page-header">
          <div>
            <div className="page-icon">{icon}</div>
            <span className="page-eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <div className="status-pill"><CheckCircle2 size={15} /> 服务已连接</div>
        </header>

        <div className="content-panel">{renderContent()}</div>

        <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
          <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="输入问题，例如：查询奇多的价格是多少" />
          <button type="submit" disabled={loading || !input.trim()} aria-label="发送"><ArrowUp size={20} /></button>
        </form>
      </section>
    </main>
  );
}

function ChatMessages({ messages, loading }) {
  return (
    <section className="messages" aria-label="对话内容">
      {messages.map((message, index) => (
        <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
          <div className="avatar">{message.role === 'user' ? <UserRound size={18} /> : <Bot size={18} />}</div>
          <div className="bubble"><MarkdownLite text={message.content} /></div>
        </div>
      ))}
      {loading && (
        <div className="message-row assistant">
          <div className="avatar"><Bot size={18} /></div>
          <div className="bubble loading"><Loader2 size={18} className="spin" /> 正在调用智能体分析...</div>
        </div>
      )}
    </section>
  );
}

createRoot(document.getElementById('root')).render(<App />);
