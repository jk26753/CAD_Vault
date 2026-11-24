// Table Configurator API. Separate from Model Vault's api.ts on purpose.
const BASE = '/api/configurator';
// step: smallest allowed (typed) increment. slider_step: increment the slider moves in.
export type Param = {
  name: string; label: string; min: number; max: number; step: number; slider_step: number;
};
// An on/off option shown as a checkbox: `on` is written when checked, `off` when unchecked.
export type Option = { name: string; label: string; on: number; off: number };
export type State = {
  equations_file: string; params: Param[]; options: Option[]; values: Record<string, number>;
};
export type ApplyResult = { saved: boolean; synced: boolean; message: string };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(BASE + path, init);
  } catch {
    // fetch() only rejects on a network failure: the FastAPI server is not running or not reachable.
    throw Error('Cannot reach the CAD Vault backend (network request failed).');
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw Error(body.detail ?? `Request failed (${r.status})`);
  return body as T;
}

export const getState = () => call<State>('/state');

export const apply = (values: Record<string, number>) =>
  call<ApplyResult>('/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  });

export type ExportFormat = 'step' | 'packandgo';

// Ask the backend to export the rebuilt SolidWorks model, then save it via the browser's download.
// Returns the downloaded file name.
export async function exportModel(format: ExportFormat, name: string): Promise<string> {
  let r: Response;
  try {
    r = await fetch(BASE + '/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format, name }),
    });
  } catch {
    throw Error('Cannot reach the CAD Vault backend (network request failed).');
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw Error(body.detail ?? `Export failed (${r.status})`);
  }
  // File name chosen by the server (sanitised), from the Content-Disposition header.
  const cd = r.headers.get('Content-Disposition') ?? '';
  const m = /filename\*=utf-8''([^;]+)|filename="?([^";]+)"?/i.exec(cd);
  const file = m ? decodeURIComponent(m[1] ?? m[2]) : `${name}.${format === 'step' ? 'step' : 'zip'}`;
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement('a'), { href: url, download: file });
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return file;
}
