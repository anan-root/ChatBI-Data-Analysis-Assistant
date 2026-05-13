const SVG_WIDTH = 720;
const SVG_HEIGHT = 260;
const PADDING = { top: 24, right: 28, bottom: 48, left: 54 };

function getSeries(option) {
  return Array.isArray(option?.series) ? option.series[0] || {} : {};
}

function getColor(option, index = 0) {
  const palette = option?.color?.length ? option.color : ['#6f8faf', '#88a77d', '#d8a657', '#b8898c'];
  return palette[index % palette.length];
}

function maxValue(values) {
  return Math.max(...values.map((item) => Number(item) || 0), 1);
}

function renderEmpty() {
  return (
    <div className="svg-chart empty-chart">
      <span>暂无可绘制数据</span>
    </div>
  );
}

function BarChartSvg({ option }) {
  const series = getSeries(option);
  const categories = option?.xAxis?.type === 'category'
    ? option.xAxis.data || []
    : option?.yAxis?.data || [];
  const values = (series.data || []).map((item) => Number(item) || 0);
  if (!categories.length || !values.length) return renderEmpty();

  const plotWidth = SVG_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = SVG_HEIGHT - PADDING.top - PADDING.bottom;
  const max = maxValue(values);
  const isHorizontal = option?.yAxis?.type === 'category';
  const barGap = 8;
  const barSize = isHorizontal
    ? Math.max(12, (plotHeight - barGap * (values.length - 1)) / values.length)
    : Math.max(10, (plotWidth - barGap * (values.length - 1)) / values.length);

  return (
    <svg className="svg-chart" viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img">
      <line x1={PADDING.left} y1={SVG_HEIGHT - PADDING.bottom} x2={SVG_WIDTH - PADDING.right} y2={SVG_HEIGHT - PADDING.bottom} />
      <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={SVG_HEIGHT - PADDING.bottom} />
      {values.map((value, index) => {
        const ratio = value / max;
        if (isHorizontal) {
          const y = PADDING.top + index * (barSize + barGap);
          const width = ratio * plotWidth;
          return (
            <g key={`${categories[index]}-${index}`}>
              <rect x={PADDING.left} y={y} width={width} height={barSize} rx="8" fill={getColor(option, index)} />
              <text x={PADDING.left - 8} y={y + barSize * 0.7} textAnchor="end">{String(categories[index]).slice(0, 8)}</text>
              <text x={PADDING.left + width + 6} y={y + barSize * 0.7}>{value}</text>
            </g>
          );
        }
        const x = PADDING.left + index * (barSize + barGap);
        const height = ratio * plotHeight;
        const y = SVG_HEIGHT - PADDING.bottom - height;
        return (
          <g key={`${categories[index]}-${index}`}>
            <rect x={x} y={y} width={barSize} height={height} rx="8" fill={getColor(option, index)} />
            <text x={x + barSize / 2} y={SVG_HEIGHT - 24} textAnchor="middle">{String(categories[index]).slice(0, 6)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function LineChartSvg({ option }) {
  const series = getSeries(option);
  const categories = option?.xAxis?.data || [];
  const values = (series.data || []).map((item) => Number(item) || 0);
  if (!categories.length || !values.length) return renderEmpty();

  const plotWidth = SVG_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = SVG_HEIGHT - PADDING.top - PADDING.bottom;
  const max = maxValue(values);
  const points = values.map((value, index) => {
    const x = PADDING.left + (plotWidth * index) / Math.max(values.length - 1, 1);
    const y = SVG_HEIGHT - PADDING.bottom - (value / max) * plotHeight;
    return [x, y];
  });
  const path = points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'} ${x} ${y}`).join(' ');

  return (
    <svg className="svg-chart" viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img">
      <line x1={PADDING.left} y1={SVG_HEIGHT - PADDING.bottom} x2={SVG_WIDTH - PADDING.right} y2={SVG_HEIGHT - PADDING.bottom} />
      <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={SVG_HEIGHT - PADDING.bottom} />
      <path d={path} fill="none" stroke={getColor(option)} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      {points.map(([x, y], index) => (
        <g key={`${categories[index]}-${index}`}>
          <circle cx={x} cy={y} r="5" fill={getColor(option, index)} />
          {index % Math.ceil(points.length / 6 || 1) === 0 && <text x={x} y={SVG_HEIGHT - 24} textAnchor="middle">{String(categories[index]).slice(0, 7)}</text>}
        </g>
      ))}
    </svg>
  );
}

function PieChartSvg({ option }) {
  const series = getSeries(option);
  const data = (series.data || []).map((item) => ({ name: item.name, value: Number(item.value) || 0 })).filter((item) => item.value > 0);
  if (!data.length) return renderEmpty();

  const total = data.reduce((sum, item) => sum + item.value, 0);
  const centerX = 190;
  const centerY = 130;
  const radius = 88;
  let startAngle = -Math.PI / 2;
  const slices = data.map((item, index) => {
    const angle = (item.value / total) * Math.PI * 2;
    const endAngle = startAngle + angle;
    const x1 = centerX + radius * Math.cos(startAngle);
    const y1 = centerY + radius * Math.sin(startAngle);
    const x2 = centerX + radius * Math.cos(endAngle);
    const y2 = centerY + radius * Math.sin(endAngle);
    const largeArc = angle > Math.PI ? 1 : 0;
    const path = `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    startAngle = endAngle;
    return { ...item, path, color: getColor(option, index), percent: Math.round((item.value / total) * 100) };
  });

  return (
    <svg className="svg-chart" viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img">
      {slices.map((slice) => <path key={slice.name} d={slice.path} fill={slice.color} />)}
      <circle cx={centerX} cy={centerY} r="46" fill="#fbfaf7" />
      {slices.slice(0, 6).map((slice, index) => (
        <g key={`${slice.name}-legend`}>
          <rect x="360" y={54 + index * 30} width="12" height="12" rx="3" fill={slice.color} />
          <text x="382" y={65 + index * 30}>{String(slice.name).slice(0, 14)} · {slice.percent}%</text>
        </g>
      ))}
    </svg>
  );
}

function ScatterChartSvg({ option }) {
  const series = getSeries(option);
  const data = (series.data || []).map((item) => [Number(item[0]) || 0, Number(item[1]) || 0]);
  if (!data.length) return renderEmpty();

  const plotWidth = SVG_WIDTH - PADDING.left - PADDING.right;
  const plotHeight = SVG_HEIGHT - PADDING.top - PADDING.bottom;
  const maxX = maxValue(data.map(([x]) => x));
  const maxY = maxValue(data.map(([, y]) => y));

  return (
    <svg className="svg-chart" viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img">
      <line x1={PADDING.left} y1={SVG_HEIGHT - PADDING.bottom} x2={SVG_WIDTH - PADDING.right} y2={SVG_HEIGHT - PADDING.bottom} />
      <line x1={PADDING.left} y1={PADDING.top} x2={PADDING.left} y2={SVG_HEIGHT - PADDING.bottom} />
      <text x={SVG_WIDTH - PADDING.right} y={SVG_HEIGHT - 18} textAnchor="end">{option?.xAxis?.name}</text>
      <text x={PADDING.left + 4} y={PADDING.top - 8}>{option?.yAxis?.name}</text>
      {data.map(([xValue, yValue], index) => {
        const x = PADDING.left + (xValue / maxX) * plotWidth;
        const y = SVG_HEIGHT - PADDING.bottom - (yValue / maxY) * plotHeight;
        return <circle key={`${xValue}-${yValue}-${index}`} cx={x} cy={y} r="6" fill={getColor(option, index)} opacity="0.78" />;
      })}
    </svg>
  );
}

export function EChart({ option, style }) {
  const type = getSeries(option).type;
  const content = {
    bar: <BarChartSvg option={option} />,
    line: <LineChartSvg option={option} />,
    pie: <PieChartSvg option={option} />,
    scatter: <ScatterChartSvg option={option} />,
  }[type] || renderEmpty();

  return (
    <div className="svg-chart-frame" style={style}>
      {content}
    </div>
  );
}
