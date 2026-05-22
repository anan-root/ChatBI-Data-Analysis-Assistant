import { Bot, ChevronDown, Database, Loader2, Route, UserRound } from 'lucide-react';
import { MarkdownLite } from '../../shared/components/MarkdownLite';

const intentLabel = {
  chat: '普通问答',
  data_query: '业务数据查询',
  python: 'Python 计算',
  unknown: '待识别',
};

function TracePanel({ trace }) {
  if (!trace || !Array.isArray(trace.steps) || trace.steps.length === 0) return null;
  return (
    <details className="agent-panel">
      <summary><Route size={14} /> 执行链路 <ChevronDown size={14} /></summary>
      <div className="agent-panel-body">
        <div className="trace-meta">
          <span>意图：{intentLabel[trace.intent] || trace.intent}</span>
          {trace.workspace?.workspaceName && <span>空间：{trace.workspace.workspaceName}</span>}
          <span>ID：{trace.traceId}</span>
        </div>
        <div className="trace-steps">
          {trace.steps.map((step, index) => (
            <article className={`trace-step ${step.status || 'ok'}`} key={`${step.stage}-${index}`}>
              <div>
                <strong>{step.stage}</strong>
                <span>{step.toolName || step.node || 'Agent'}</span>
                <em>{step.status || 'ok'}</em>
              </div>
              <p>{step.summary}</p>
              {step.sql && <code>{step.sql}</code>}
              {step.reason && step.status === 'blocked' && <small>{step.reason}</small>}
            </article>
          ))}
        </div>
      </div>
    </details>
  );
}

function EvidencePanel({ evidence }) {
  const hasEvidence = evidence && (
    evidence.workspaceName ||
    (evidence.fields || []).length > 0 ||
    (evidence.sql || []).length > 0 ||
    (evidence.knowledge || []).length > 0
  );
  if (!hasEvidence) return null;
  return (
    <details className="agent-panel evidence-panel">
      <summary><Database size={14} /> 回答依据 <ChevronDown size={14} /></summary>
      <div className="agent-panel-body">
        {evidence.workspaceName && <p className="evidence-line">业务空间：{evidence.workspaceName}</p>}
        {(evidence.fields || []).length > 0 && (
          <p className="evidence-line">字段：{evidence.fields.join('、')}</p>
        )}
        {(evidence.sql || []).map((item, index) => (
          <article className={`evidence-sql ${item.allowed ? 'ok' : 'blocked'}`} key={`${item.query}-${index}`}>
            <span>{item.allowed ? 'Allowed SQL' : 'Blocked SQL'}</span>
            <code>{item.query}</code>
            <small>{item.reason}</small>
          </article>
        ))}
        {(evidence.knowledge || []).length > 0 && (
          <div className="knowledge-hits">
            {evidence.knowledge.map((item) => (
              <article key={item.title}>
                <strong>{item.title}</strong>
                <p>{item.summary}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

export function ChatMessages({ messages, loading }) {
  return (
    <section className="messages" aria-label="对话内容">
      {messages.map((message, index) => (
        <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
          <div className="avatar">{message.role === 'user' ? <UserRound size={18} /> : <Bot size={18} />}</div>
          <div className="bubble">
            <MarkdownLite text={message.content} />
            {message.role === 'assistant' && (
              <>
                <TracePanel trace={message.trace} />
                <EvidencePanel evidence={message.evidence} />
              </>
            )}
          </div>
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
