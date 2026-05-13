import { Bot, Loader2, UserRound } from 'lucide-react';
import { MarkdownLite } from '../../shared/components/MarkdownLite';

export function ChatMessages({ messages, loading }) {
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
