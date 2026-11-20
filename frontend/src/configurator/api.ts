// Table Configurator API. Separate from Model Vault's api.ts on purpose.
const BASE = '/api/configurator';
export type Param = { name: string; label: string; min: number; max: number; step: number };
export type State = { equations_file: string; params: Param[]; values: Record<string, number> };
export type ApplyResult = { saved: boolean; synced: boolean; message: string };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(BASE + path, init);
  } catch {
    throw Error('Cannot reach the backend. Is run_backend.bat running?');
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
