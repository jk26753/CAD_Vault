import { useEffect, useState, type KeyboardEvent } from 'react';
import { RotateCw } from 'lucide-react';
import { apply, exportModel, getState, type ExportFormat, type Param, type State } from './api';
import TablePreview from './TablePreview';
import './configurator.css';

const OK = '#2ee6a6', WARN = '#ffb020', ERR = '#ff5470';
type Status = { msg: string; color: string };

// Decimal places in a step: 0.01 -> 2, 6 -> 0.
const decimals = (step: number) => (String(step).split('.')[1] ?? '').length;
// Clamp to the range and round to the nearest step. toFixed removes floating-point
// noise such as 80.13000000000001 so the value shown and sent is exactly 80.13.
const snap = (v: number, p: Param) => {
  const stepped = Math.min(p.max, Math.max(p.min, Math.round(v / p.step) * p.step));
  return Number(stepped.toFixed(decimals(p.step)));
};
const fmt = (n: number) => String(Number(n.toFixed(4))); // like Python's {:g}

export default function Configurator() {
  const [state, setState] = useState<State>();
  const [values, setValues] = useState<Record<string, number>>({});
  const [status, setStatus] = useState<Status>({ msg: 'Loading...', color: WARN });
  const [busy, setBusy] = useState(false);
  // Export is allowed only when SolidWorks matches the page: after load, or after an Apply
  // that reached SolidWorks. Any change on the page clears it until the next Apply.
  const [exportable, setExportable] = useState(false);
  const [format, setFormat] = useState<ExportFormat>('step');
  const [customName, setCustomName] = useState(''); // blank = use the auto name

  const load = async () => {
    setStatus({ msg: 'Loading...', color: WARN });
    try {
      const s = await getState();
      setState(s);
      setValues({
        ...Object.fromEntries(s.params.map(p => [p.name, snap(s.values[p.name], p)])),
        ...Object.fromEntries(s.options.map(o => [o.name, s.values[o.name]])),
      });
      setStatus({ msg: 'Ready', color: OK });
      setExportable(true);
    } catch (e) {
      setState(undefined);
      setStatus({ msg: (e as Error).message, color: ERR });
    }
  };
  useEffect(() => { void load(); }, []);

  const change = (name: string, v: number) => {
    setValues(prev => ({ ...prev, [name]: v }));
    setExportable(false);
    setStatus({ msg: 'Changes not applied - click Apply & Rebuild', color: WARN });
  };

  const run = async (vals = values) => {
    if (busy) return;
    setBusy(true);
    setStatus({ msg: 'Rebuilding...', color: WARN });
    try {
      const r = await apply(vals);
      setStatus({ msg: r.message, color: r.synced ? OK : ERR });
      setExportable(r.synced);
    } catch (e) {
      setStatus({ msg: (e as Error).message, color: ERR });
    } finally {
      setBusy(false);
    }
  };

  const runExport = async (name: string) => {
    if (busy || !exportable) return;
    setBusy(true);
    setStatus({
      msg: format === 'step' ? 'Exporting STEP...' : 'Running Pack and Go (this can take a minute)...',
      color: WARN,
    });
    try {
      const file = await exportModel(format, name);
      setStatus({ msg: `Exported ${file}`, color: OK });
    } catch (e) {
      setStatus({ msg: (e as Error).message, color: ERR });
    } finally {
      setBusy(false);
    }
  };

  // Enter applies, like the desktop tool. Number fields handle their own Enter.
  const onKey = (e: KeyboardEvent) => {
    const tag = (e.target as HTMLElement).tagName;
    if (e.key === 'Enter' && tag !== 'BUTTON') void run();
  };

  const header = (
    <div className="cfgHead">
      <div>
        <h1>TABLE CONFIGURATOR</h1>
        <small>PARAMETRIC ASSEMBLY CONTROL // SOLIDWORKS LINK</small>
      </div>
      <span className="cfgLed" style={{ background: status.color, boxShadow: `0 0 10px ${status.color}` }} />
    </div>
  );

  if (!state) {
    return (
      <div className="cfg">
        {header}
        <div className="cfgPanel cfgError">
          <p style={{ color: status.color }}>{status.msg.toUpperCase()}</p>
          {status.color === ERR && (
            <>
              <p className="cfgMuted">
                Check the Table Configurator settings in backend/configurator.env, then restart CAD Vault.
              </p>
              <button onClick={() => void load()}><RotateCw />Retry</button>
            </>
          )}
        </div>
      </div>
    );
  }

  const L = values.TableLength, W = values.TableWidth, H = values.TableHeight;
  // Default export name, e.g. Table_L56.5_W48_H44.5_Casters_2026-11-24 (local date).
  const casters = values.Casters === state.options.find(o => o.name === 'Casters')?.on;
  const today = new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD
  const autoName = `Table_L${fmt(L)}_W${fmt(W)}_H${fmt(H)}_${casters ? 'Casters' : 'NoCasters'}_${today}`;
  const derived = [
    ['CENTER EXTR.', (W - 3) / 3],
    ['HOLE PLATES', W / 6],
    ['VERT. LENGTH', H - 3],
    ['BOTTOM EXTR.', L - 6],
  ] as const;

  return (
    <div className="cfg" onKeyDown={onKey}>
      {header}
      <div className="cfgGrid">
        <section className="cfgPanel">
          <h2>INPUT PARAMETERS</h2>
          {state.params.map(p => (
            <div className="cfgRow" key={p.name}>
              <label htmlFor={`cfg-${p.name}`}>{p.label}</label>
              <input
                type="range" min={p.min} max={p.max} step={p.slider_step}
                value={values[p.name]}
                onChange={e => change(p.name, Number(e.target.value))}
              />
              <NumberField
                id={`cfg-${p.name}`} param={p} value={values[p.name]}
                onCommit={v => change(p.name, v)}
                onEnter={v => void run({ ...values, [p.name]: v })}
              />
              <span className="cfgMuted">in</span>
            </div>
          ))}
          <div className="cfgCards">
            {derived.map(([title, v]) => (
              <div key={title}>
                <small>{title}</small>
                <b>{fmt(v)}</b>
              </div>
            ))}
          </div>
          {/* Like the dimensions, ticking a box only marks a pending change; Apply & Rebuild writes it. */}
          {state.options.map(o => (
            <label className="cfgCheck" key={o.name}>
              <input
                type="checkbox"
                checked={values[o.name] === o.on}
                onChange={e => change(o.name, e.target.checked ? o.on : o.off)}
              />
              {o.label}
            </label>
          ))}
        </section>
        <div className="cfgSide">
          <section className="cfgPanel cfgPreviewPanel">
            <h2>PREVIEW</h2>
            <TablePreview L={L} W={W} H={H} />
          </section>
          <section className="cfgPanel cfgExport">
        <h2>EXPORT</h2>
        <div className="cfgExportRow">
          <div className="cfgFormat" role="radiogroup" aria-label="Export format">
            {([['step', 'STEP'], ['packandgo', 'PACK AND GO (ZIP)']] as const).map(([f, label]) => (
              <label key={f} className={format === f ? 'on' : ''}>
                <input type="radio" name="cfgFormat" checked={format === f} onChange={() => setFormat(f)} />
                {label}
              </label>
            ))}
          </div>
          <input
            className="cfgName" type="text" aria-label="File name"
            value={customName} placeholder={autoName}
            onChange={e => setCustomName(e.target.value)}
            onKeyDown={e => e.stopPropagation()} // Enter here must not trigger Apply & Rebuild
          />
          <span className="cfgMuted">.{format === 'step' ? 'step' : 'zip'}</span>
          <button
            className="cfgApply" disabled={busy || !exportable}
            onClick={() => void runExport(customName.trim() || autoName)}
          >
            EXPORT
          </button>
        </div>
        <p className="cfgMuted">
          {exportable
            ? 'Exports the model as currently rebuilt in SolidWorks. Leave the name blank to use the default shown.'
            : 'Apply & Rebuild first: export is available once SolidWorks matches the input values.'}
        </p>
          </section>
        </div>
      </div>
      <div className="cfgFoot">
        <span style={{ color: status.color }}>{status.msg.toUpperCase()}</span>
        <button className="cfgApply" disabled={busy} onClick={() => void run()}>
          APPLY &amp; REBUILD
        </button>
      </div>
      <p className="cfgPath">{state.equations_file}</p>
    </div>
  );
}

// Lets you type freely, then snaps to the allowed range and step on blur or Enter.
function NumberField({ id, param, value, onCommit, onEnter }: {
  id: string; param: Param; value: number;
  onCommit: (v: number) => void; onEnter: (v: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);

  const commit = () => {
    const n = Number(draft);
    const v = draft.trim() === '' || Number.isNaN(n) ? value : snap(n, param);
    setDraft(String(v));
    if (v !== value) onCommit(v);
    return v;
  };

  return (
    <input
      id={id} type="number" min={param.min} max={param.max} step={param.step}
      value={draft}
      onChange={e => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={e => {
        if (e.key !== 'Enter') return;
        e.stopPropagation();
        onEnter(commit());
      }}
    />
  );
}
