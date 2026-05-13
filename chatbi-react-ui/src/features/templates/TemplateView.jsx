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

export function TemplateView({ activeView, loading, onApply, onRun }) {
  const templateList = activeView === 'quick' ? quickQueries : analysisTemplates;
  return (
    <section className="template-grid" aria-label={activeView === 'quick' ? '快速查询' : '分析模板'}>
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
