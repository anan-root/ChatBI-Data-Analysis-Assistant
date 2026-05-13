export const API_URL = '/api/chatbi_service';

export async function requestJson(endpoint, options = {}) {
  const response = await fetch(endpoint, options);
  const contentType = response.headers.get('content-type') || '';
  const body = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null ? body.detail : body;
    throw new Error(detail || `接口请求失败：${response.status}`);
  }
  return body;
}

export function getBiEndpoint(activeView) {
  const endpointMap = {
    audit: '/api/bi/audit',
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
  return endpointMap[activeView];
}

export function fetchBiData(activeView) {
  return requestJson(getBiEndpoint(activeView));
}

export function fetchAuditEvents({ limit = 200, allowed = '', workspaceId = '', source = '', adminToken = '' } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (allowed !== '') params.set('allowed', allowed);
  if (workspaceId) params.set('workspace_id', workspaceId);
  if (source) params.set('source', source);
  const headers = adminToken ? { 'X-ChatBI-Admin-Token': adminToken } : undefined;
  return requestJson(`/api/bi/audit?${params.toString()}`, { headers });
}

export function sendChatMessage({ sessionId, content, history, workspaceId }) {
  return requestJson(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: sessionId,
      message: content,
      history,
      workspace_id: workspaceId || null,
    }),
  });
}

export function fetchWorkspaceReport(workspaceId) {
  return requestJson(`/api/bi/workspaces/${workspaceId}/report`);
}

export function fetchImportJobs() {
  return requestJson('/api/bi/import-clean/jobs');
}

export function uploadImportFiles(files) {
  const formData = new FormData();
  files.forEach((file) => formData.append(files.length > 1 ? 'files' : 'file', file));
  return requestJson(files.length > 1 ? '/api/bi/import-clean/upload-batch' : '/api/bi/import-clean/upload', {
    method: 'POST',
    body: formData,
  });
}

export function commitImportJob(jobId, tableName) {
  return requestJson(`/api/bi/import-clean/jobs/${jobId}/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ table_name: tableName }),
  });
}

export function batchCommitImportJobs(jobIds) {
  return requestJson('/api/bi/import-clean/jobs/batch-commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_ids: jobIds }),
  });
}
