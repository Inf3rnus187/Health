import { api, getAccessToken } from './client';
import type { ImportJob } from './types';

export function listImportJobs(): Promise<ImportJob[]> {
  return api<ImportJob[]>('/imports');
}

export function resetImported(): Promise<{ detail: string }> {
  return api<{ detail: string }>('/imports/reset', { method: 'POST' });
}

export function uploadExport(
  file: File,
  onProgress: (pct: number) => void,
): Promise<ImportJob> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/v1/imports/apple-health');
    const token = getAccessToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }
    xhr.upload.onprogress = (event) => _report(event, onProgress);
    xhr.onload = () => _settle(xhr, resolve, reject);
    xhr.onerror = () => reject(new Error('Échec du téléversement'));
    const form = new FormData();
    form.append('file', file);
    xhr.send(form);
  });
}

function _report(
  event: ProgressEvent,
  onProgress: (pct: number) => void,
): void {
  if (event.lengthComputable) {
    onProgress(Math.round((event.loaded / event.total) * 100));
  }
}

function _settle(
  xhr: XMLHttpRequest,
  resolve: (job: ImportJob) => void,
  reject: (error: Error) => void,
): void {
  if (xhr.status >= 200 && xhr.status < 300) {
    resolve(JSON.parse(xhr.responseText) as ImportJob);
  } else {
    reject(new Error(`Erreur ${xhr.status}`));
  }
}
