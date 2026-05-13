import { useState } from 'react';
import { EmptyState } from '../../shared/components/EmptyState';
import { EChart } from '../../shared/charts/EChart';

export function ReportView({ data }) {
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
          <EChart option={barOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{dimension} · {metric} 结构</h3>
          <p>回答：贡献是否过度集中，Top 维度占比是否健康。</p>
          <EChart option={pieOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{metric} 趋势</h3>
          <p>回答：核心指标在当前时间粒度下是否出现拐点或异常。</p>
          <EChart option={lineOption} style={{ height: 280 }} />
        </article>
        <article className="chart-card">
          <h3>{metric} × {scatterY || '指标'} 关系</h3>
          <p>回答：两个指标是否协同变化，是否存在离群点。</p>
          <EChart option={scatterOption} style={{ height: 280 }} />
        </article>
      </div>
    </section>
  );
}

export function WorkspaceReport({ report, loading }) {
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
              <EChart option={option} style={{ height: 280 }} />
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

export function WorkspaceModulePanel({ report, activeModule }) {
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
