import React, { Suspense, lazy, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ArrowUp,
  BarChart3,
  BriefcaseBusiness,
  CheckCircle2,
  ShieldCheck,
  ClipboardCheck,
  HardDriveUpload,
  PanelLeftClose,
  PanelLeftOpen,
  MessageSquareText,
  Network,
  Search,
} from 'lucide-react';
import { sendChatMessage } from './shared/api/client';
import { useBiData } from './shared/api/useBiData';
import { ChatMessages } from './features/chat/ChatMessages';
import { TemplateView } from './features/templates/TemplateView';
import './styles.css';

const lazyFeature = (loader, exportName) => lazy(() => loader().then((module) => ({ default: module[exportName] })));
const DashboardView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'DashboardView');
const AuditView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'AuditView');
const MetricsView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'MetricsView');
const SqlAnalysisView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'SqlAnalysisView');
const AnomaliesView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'AnomaliesView');
const UserGrowthView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'UserGrowthView');
const MonetizationView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'MonetizationView');
const RagView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'RagView');
const AiEvalView = lazyFeature(() => import('./features/bi/BiModuleViews'), 'AiEvalView');
const ImportCleanView = lazyFeature(() => import('./features/import/ImportCleanView'), 'ImportCleanView');
const ReportView = lazyFeature(() => import('./features/report/ReportViews'), 'ReportView');
const WorkspaceReport = lazyFeature(() => import('./features/report/ReportViews'), 'WorkspaceReport');
const WorkspaceModulePanel = lazyFeature(() => import('./features/report/ReportViews'), 'WorkspaceModulePanel');
const WorkspacesView = lazyFeature(() => import('./features/workspaces/WorkspacesView'), 'WorkspacesView');

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
  { key: 'audit', icon: <ShieldCheck size={16} />, label: '审计日志' },
  { key: 'aiEval', icon: <ClipboardCheck size={16} />, label: 'AI 评测' },
  { key: 'rag', icon: <Network size={16} />, label: 'RAG 知识库' },
  { key: 'quick', icon: <Search size={16} />, label: '快速查询' },
  { key: 'templates', icon: <BarChart3 size={16} />, label: '分析模板' },
];

const pageCopy = {
  chat: ['📊', '数据分析助手', '像写文档一样提问，让智能体完成查询、计算和分析。', 'Ask with data'],
  audit: ['🛡️', '审计日志', '追踪 SQL 放行、拦截、越权表引用和业务空间访问边界。', 'Audit trail'],
  aiEval: ['✅', 'AI 评测', '用固定样例验证 Text-to-SQL 安全规则、业务空间边界和字段白名单。', 'AI evaluation'],
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


function App() {
  const [activeView, setActiveView] = useState('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [input, setInput] = useState('查询奇多的价格是多少');
  const [loading, setLoading] = useState(false);
  const [chatWorkspace, setChatWorkspace] = useState(null);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好，我是 ChatBI 数据分析助手。可以帮你查商品价格、算销量、跑 Python、做图表和预测。' },
  ]);
  const sessionId = useRef(`web_${Date.now()}`);
  const { data: biData, loading: biLoading } = useBiData(activeView);

  const sendMessage = async (text = input, workspaceOverride = chatWorkspace) => {
    const content = text.trim();
    if (!content || loading) return;

    setActiveView('chat');
    if (workspaceOverride) setChatWorkspace(workspaceOverride);
    const userMessage = { role: 'user', content };
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const requestHistory = messages
        .filter((item) => item.role === 'user' || item.role === 'assistant')
        .map((item) => ({ role: item.role, content: item.content }));

      const result = await sendChatMessage({
        sessionId: sessionId.current,
        content,
        history: requestHistory,
        workspaceId: workspaceOverride?.workspaceId,
      });
      setMessages((current) => [...current, { role: 'assistant', content: result.message || '没有拿到返回内容。', trace: result.trace, evidence: result.evidence }]);
    } catch (error) {
      setMessages((current) => [...current, { role: 'assistant', content: `请求失败：${error.message}\n请确认后端服务已启动后再试。` }]);
    } finally {
      setLoading(false);
    }
  };

  const openWorkspaceChat = (workspace) => {
    setChatWorkspace(workspace);
    setActiveView('chat');
    setInput(`请基于「${workspace.name}」生成一份重点诊断和下一步建议`);
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
          {chatWorkspace && (
            <div className="chat-context-card">
              <span>Workspace Context</span>
              <strong>{chatWorkspace.name}</strong>
              <p>{chatWorkspace.businessType || '通用业务'} · 后续提问将限定在该业务空间内</p>
              <button type="button" onClick={() => setChatWorkspace(null)} disabled={loading}>退出空间语境</button>
            </div>
          )}
          <ChatMessages messages={messages} loading={loading} />
        </>
      );
    }
    if (activeView === 'workspaces') {
      return (
        <WorkspacesView
          data={biData.workspaces}
          onChatInWorkspace={openWorkspaceChat}
          WorkspaceReport={WorkspaceReport}
          WorkspaceModulePanel={WorkspaceModulePanel}
        />
      );
    }
    if (activeView === 'audit') return <AuditView data={biData.audit} loading={biLoading} />;
    if (activeView === 'aiEval') return <AiEvalView data={biData.aiEval} loading={biLoading} />;
    if (activeView === 'sql') return <SqlAnalysisView data={biData.sql} onRun={sendMessage} />;
    if (activeView === 'dashboard') return <DashboardView data={biData.dashboard} loading={biLoading} />;
    if (activeView === 'metrics') return <MetricsView data={biData.metrics} loading={biLoading} />;
    if (activeView === 'anomalies') return <AnomaliesView data={biData.anomalies} loading={biLoading} />;
    if (activeView === 'growth') return <UserGrowthView data={biData.growth} />;
    if (activeView === 'monetization') return <MonetizationView data={biData.monetization} />;
    if (activeView === 'report') return <ReportView data={biData.report} loading={biLoading} />;
    if (activeView === 'importClean') return <ImportCleanView data={biData.importClean} WorkspaceReport={WorkspaceReport} />;
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

        <div className="content-panel">
          <Suspense fallback={<div className="empty-state">正在加载模块...</div>}>
            {renderContent()}
          </Suspense>
        </div>

        <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
          <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="输入问题，例如：查询奇多的价格是多少" />
          <button type="submit" disabled={loading || !input.trim()} aria-label="发送"><ArrowUp size={20} /></button>
        </form>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
