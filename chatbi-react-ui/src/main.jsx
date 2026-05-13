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
  { key: 'chat', icon: <MessageSquareText size={16} />, label: '数据问答' },
  { key: 'workspaces', icon: <BriefcaseBusiness size={16} />, label: '业务空间' },
  { key: 'sql', icon: <DatabaseZap size={16} />, label: 'SQL 分析' },
  { key: 'dashboard', icon: <LayoutDashboard size={16} />, label: 'BI 看板' },
  { key: 'metrics', icon: <Gauge size={16} />, label: '指标体系' },
  { key: 'anomalies', icon: <Activity size={16} />, label: '异常分析' },
  { key: 'growth', icon: <UsersRound size={16} />, label: '用户增长' },
  { key: 'monetization', icon: <Coins size={16} />, label: '变现成本' },
  { key: 'report', icon: <FileText size={16} />, label: '分析报告' },
  { key: 'importClean', icon: <HardDriveUpload size={16} />, label: '导入导出' },
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
  chat: ['📊', '数据分析助手', '像写文档一样提问，让智能体完成查询、计算和分析。'],
  workspaces: ['🏢', '业务空间', '按上传数据隔离业务上下文，每个表都有独立报告和分析口径。'],
  sql: ['🧮', 'SQL 分析', '沉淀自然语言查数、聚合统计、对比分析和环比模板。'],
  dashboard: ['📌', 'BI 看板', '核心指标、月度趋势和商品排行集中展示。'],
  metrics: ['🧭', '指标体系', '沉淀业务口径，统一指标定义、来源和应用场景。'],
  anomalies: ['⚠️', '异常分析', '识别核心指标波动，辅助定位业务异常月份。'],
  growth: ['🌱', '用户增长', '围绕活跃、分层和运营动作评估用户增长机会。'],
  monetization: ['💰', '变现成本', '估算收入贡献，预留成本、ROI 和毛利分析口径。'],
  report: ['📝', '分析报告', '自动输出“现象、原因、异常、建议”的结构化报告。'],
  importClean: ['🧹', '导入导出', '企业数据导入后自动清洗，并支持导出清洗结果、字段映射和分析报告。'],
  rag: ['🧠', 'RAG 知识库', '企业知识库增强能力，默认不参与问答链路，可按需启用。'],
  quick: ['🔎', '快速查询', '常用问题一键填入或直接执行，适合先验证字段和结果。'],
  templates: ['📈', '分析模板', '把重复的数据分析流程做成模板，点击即可发起任务。'],
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
            <strong>{report.analysisPlan.name}</strong>
            <p>{report.analysisPlan.focus}</p>
            <small>{report.analysisPlan.inputSummary}</small>
          </div>
          <div className="plan-tags">
            <span>置信度：{report.analysisPlan.confidence}</span>
            {report.analysisPlan.selectedModules.map((module) => <code key={module}>{module}</code>)}
          </div>
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

function WorkspacesView({ data }) {
  const [selectedWorkspace, setSelectedWorkspace] = useState(null);
  const [report, setReport] = useState(null);
  const [loadingReport, setLoadingReport] = useState(false);

  if (!data) return <EmptyState text="正在加载业务空间..." />;
  if (data.error) return <EmptyState text={data.error} />;

  const openReport = async (workspace) => {
    setSelectedWorkspace(workspace);
    setLoadingReport(true);
    setReport(null);
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

  return (
    <section className="module-stack">
      <div className="workspace-grid">
        {data.workspaces.map((workspace) => (
          <article className="workspace-card" key={workspace.workspaceId}>
            <span>{workspace.businessType}</span>
            <strong>{workspace.name}</strong>
            <p>{workspace.sourceFile}</p>
            <div>
              <code>{workspace.rows} 行 / {workspace.columns} 字段</code>
              <button type="button" onClick={() => openReport(workspace)}>查看报告</button>
            </div>
          </article>
        ))}
      </div>
      {data.workspaces.length === 0 && <EmptyState text="还没有业务空间。先在导入导出模块上传一个文件。" />}
      {selectedWorkspace && (
        <article className="insight-card">
          <span>当前业务空间</span>
          <strong>{selectedWorkspace.name}</strong>
          <p>报告基于该上传表单独生成，不会混用默认电商样例数据。</p>
        </article>
      )}
      <WorkspaceReport report={report} loading={loadingReport} />
    </section>
  );
}

function ImportCleanView({ data }) {
  const [job, setJob] = useState(null);
  const [jobList, setJobList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [committing, setCommitting] = useState(false);
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
    const file = event.target.files?.[0];
    if (!file || uploading) return;
    setUploading(true);
    setStatusText('正在上传并自动清洗...');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/bi/import-clean/upload', {
        method: 'POST',
        body: formData,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || '上传清洗失败');
      setJob(result);
      setTableName(result.suggestedTableName || '');
      setJobList((current) => [result, ...current.filter((item) => item.jobId !== result.jobId)].slice(0, 20));
      setStatusText(`清洗完成：${result.rowsBefore} 行 → ${result.rowsAfter} 行`);
    } catch (error) {
      setStatusText(error.message);
    } finally {
      setUploading(false);
      event.target.value = '';
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
          <span>文件导入</span>
          <strong>上传后自动清洗</strong>
          <p>支持 CSV / XLSX / XLS，自动去重、修正类型、处理缺失值，并生成清洗预览。</p>
        </div>
        <label className="upload-button">
          {uploading ? '处理中...' : '选择文件'}
          <input type="file" accept=".csv,.xlsx,.xls" onChange={handleUpload} disabled={uploading} />
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
            <span>清洗结果</span>
            <span>状态</span>
          </div>
          {jobList.slice(0, 5).map((item) => (
            <div className="table-row three" key={item.jobId}>
              <strong>{item.originalFilename}</strong>
              <span>{item.rowsBefore} → {item.rowsAfter} 行</span>
              <button type="button" className="link-button" onClick={() => { setJob(item); setTableName(item.suggestedTableName || ''); handleWorkspaceReport(item); }}>看报告</button>
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

  const [icon, title, description] = pageCopy[activeView];

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
    <main className="app-shell">
      <aside className="sidebar">
        <div className="workspace-mark">BI</div>
        <div className="workspace-copy">
          <strong>ChatBI</strong>
          <span>数据分析助手</span>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <button className={activeView === item.key ? 'active' : ''} key={item.key} type="button" onClick={() => setActiveView(item.key)}>
              {item.icon}
              {item.label}
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
