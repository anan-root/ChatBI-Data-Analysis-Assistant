import { useEffect, useState } from 'react';
import {
  batchCommitImportJobs,
  commitImportJob,
  fetchImportJobs,
  fetchWorkspaceReport,
  uploadImportFiles,
} from '../../shared/api/client';
import { EmptyState } from '../../shared/components/EmptyState';

export function ImportCleanView({ data, WorkspaceReport }) {
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
    fetchImportJobs()
      .then((result) => setJobList(result.jobs || []))
      .catch(() => setJobList([]));
  }, []);

  const handleUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length || uploading) return;
    setUploading(true);
    setStatusText(files.length > 1 ? `正在批量上传并清洗 ${files.length} 个文件...` : '正在上传并自动清洗...');

    try {
      const result = await uploadImportFiles(files);
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
      const result = await batchCommitImportJobs(pendingJobs.map((item) => item.jobId));
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
      const result = await commitImportJob(job.jobId, tableName);
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
      const result = await fetchWorkspaceReport(targetJob.jobId);
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
