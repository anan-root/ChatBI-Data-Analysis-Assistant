import React, { useState } from 'react';
import { fetchWorkspaceReport } from '../../shared/api/client';
import { EmptyState } from '../../shared/components/EmptyState';
import {
  buildWorkspaceGroups,
  businessSpaceMeta,
  businessSpaceOrder,
  formatWorkspaceTime,
  readManualWorkspaceGroups,
  saveManualWorkspaceGroups,
  workspaceGroupModes,
} from './grouping';

export function WorkspacesView({ data, onChatInWorkspace, WorkspaceReport, WorkspaceModulePanel }) {
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
      const result = await fetchWorkspaceReport(workspace.workspaceId);
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
            <div className="report-cover-actions">
              <button type="button" onClick={() => { setReportOpen((current) => !current); if (reportOpen) setActiveModule(null); }} disabled={loadingReport || Boolean(report?.error)}>
                {reportOpen ? '隐藏报告内容' : '展开报告内容'}
              </button>
              <button type="button" onClick={() => onChatInWorkspace?.(selectedWorkspace)} disabled={loadingReport || Boolean(report?.error)}>
                用此空间提问
              </button>
            </div>
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
