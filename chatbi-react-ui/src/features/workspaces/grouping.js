export const workspaceGroupModes = [
  { key: 'month', label: '按上传时间', hint: '适合周期复盘和月度项目归档' },
  { key: 'name', label: '按名称', hint: '适合按项目、渠道、活动名称检索' },
  { key: 'status', label: '按入库状态', hint: '区分已入库与待确认数据' },
  { key: 'manual', label: '手动分组', hint: '前端本地保存，可先快速调整' },
];

export const businessSpaceOrder = ['销售经营', '用户运营', '财务经营', '库存管理', '运营分析', '通用业务'];

export const businessSpaceMeta = {
  销售经营: { icon: '01', tone: 'sales' },
  用户运营: { icon: '02', tone: 'user' },
  财务经营: { icon: '03', tone: 'finance' },
  库存管理: { icon: '04', tone: 'inventory' },
  运营分析: { icon: '05', tone: 'operation' },
  通用业务: { icon: '06', tone: 'general' },
};

export function readManualWorkspaceGroups() {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(window.localStorage.getItem('chatbi_manual_workspace_groups') || '{}');
  } catch {
    return {};
  }
}

export function saveManualWorkspaceGroups(groups) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('chatbi_manual_workspace_groups', JSON.stringify(groups));
}

export function formatWorkspaceMonth(createdAt) {
  if (!createdAt) return '未记录上传时间';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return '未记录上传时间';
  return `${date.getFullYear()}年${String(date.getMonth() + 1).padStart(2, '0')}月上传`;
}

export function formatWorkspaceTime(createdAt) {
  if (!createdAt) return '未记录';
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return createdAt;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function inferNameGroup(workspace) {
  const rawName = (workspace.name || workspace.sourceFile || '未命名项目').replace(/\.[^.]+$/, '');
  const parts = rawName.split(/[_\-—\s]+/).filter(Boolean);
  const firstUsefulPart = parts.find((part) => part !== workspace.businessType && part.length >= 2);
  if (firstUsefulPart) return `${firstUsefulPart}项目组`;
  return `${rawName.slice(0, 10)}项目组`;
}

export function buildWorkspaceGroups(workspaces, mode, manualGroups) {
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
