import { useEffect, useState } from 'react';
import {
  Box,
  Grid3X3,
  List,
  Plus,
  Pencil,
  Search,
  Download,
  Trash2,
  Upload,
  FilePlus2,
} from 'lucide-react';
import { API, req, type M, type F } from './api';
import Tags from './components/Tags';
import RobotSelect from './components/RobotSelect';
import Viewer from './components/Viewer';
import HeaderActions from './shell/HeaderActions';
import './style.css';
const CAT = [
  'Robot Mounting (Table/Pedestals/Mobile Carts)',
  'Robot EOAT',
  '3D-Printed Accessories',
  'Misc TSLOT Model',
  'Fixture',
  'Reference Models',
  'Sheet Metal/Plate',
  'Misc',
];
const cc = (x: string) =>
  ['mount', 'eoat', 'print', 'tslot', 'fixture', 'ref', 'sheet', 'misc'][
    Math.max(0, CAT.indexOf(x))
  ];
export default function App() {
  const [ms, setMs] = useState<M[]>([]),
    [id, setId] = useState<number>(),
    [grid, setGrid] = useState(true),
    [query, setQuery] = useState(''),
    [sort, setSort] = useState('category'),
    [form, setForm] = useState(false),
    [del, setDel] = useState(false),
    [tags, setTags] = useState<string[]>([]);
  const load = async () => {
    const [a, t] = await Promise.all([
      req<M[]>(`/models?qs=${encodeURIComponent(query)}`),
      req<string[]>('/tags'),
    ]);
    setMs(a);
    setTags(t);
    setId((v) => (a.some((x) => x.id === v) ? v : a[0]?.id));
  };
  useEffect(() => {
    void load();
  }, [query]);
  const items = [...ms].sort((a, b) =>
      sort === 'category'
        ? a.category.localeCompare(b.category)
        : sort === 'price'
          ? (parseFloat(b.rom_price) || 0) - (parseFloat(a.rom_price) || 0)
          : (b.last_quoted_on || '').localeCompare(a.last_quoted_on || ''),
    ),
    m = ms.find((x) => x.id === id);
  return (
    <>
      <HeaderActions>
        <nav>
          <button onClick={() => setGrid(!grid)}>
            {grid ? <List /> : <Grid3X3 />}
            <span>{grid ? 'Detail view' : 'Grid view'}</span>
          </button>
          <button className="primary" onClick={() => setForm(true)}>
            <Plus />
            <span>Add model</span>
          </button>
        </nav>
      </HeaderActions>
      <main>
        <div className="search">
          <Search />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search names, part numbers, tags, and design projects"
          />
          {grid && (
            <>
              <label>Sort By</label>
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="category">Category</option>
                <option value="price">Price</option>
                <option value="quoted">Most recently quoted</option>
              </select>
            </>
          )}
        </div>
        {grid ? (
          <div className="cards">
            {items.map((x) => {
              const pic = x.files.find(
                (f) => f.role === 'preview' && f.original_name.endsWith('.png'),
              );
              return (
                <article
                  className={cc(x.category)}
                  onClick={() => {
                    setId(x.id);
                    setGrid(false);
                  }}
                >
                  <div className="preview">
                    {pic ? <img src={`${API}/files/${pic.id}`} /> : <Box />}
                  </div>
                  <div className="body">
                    <small>{x.part_number}</small>
                    <h2>{x.name}</h2>
                    <p>{x.category}</p>
                    <footer>
                      <span>{x.rom_price ? `$${x.rom_price.replace(/^\$/, '')}` : 'No price'}</span>
                      <span>{x.last_quoted_on || 'No quote date'}</span>
                    </footer>
                  </div>
                  <div className="strip" />
                </article>
              );
            })}
          </div>
        ) : m ? (
          <div className="detailLayout">
            <aside className="modelSidebar">
              <div className="sidebarHeading">Models</div>
              {ms.map((x) => (
                <button
                  key={x.id}
                  className={x.id === id ? 'selectedModel' : ''}
                  onClick={() => setId(x.id)}
                >
                  <b>{x.name}</b>
                  <small>{x.part_number}</small>
                </button>
              ))}
            </aside>
            <Detail
              m={m}
              edit={() => setForm(true)}
              confirmDelete={() => setDel(true)}
              reload={load}
            />
          </div>
        ) : null}
      </main>
      {form && (
        <Form
          model={m && !grid ? m : undefined}
          suggestions={tags}
          close={() => setForm(false)}
          done={load}
        />
      )}{' '}
      {del && m && (
        <Confirm
          name={m.name}
          close={() => setDel(false)}
          yes={async () => {
            await req(`/models/${m.id}`, { method: 'DELETE' });
            setDel(false);
            setGrid(true);
            await load();
          }}
        />
      )}
    </>
  );
}
function Detail({
  m,
  edit,
  confirmDelete,
  reload,
}: {
  m: M;
  edit: () => void;
  confirmDelete: () => void;
  reload: () => Promise<void>;
}) {
  const [tab, setTab] = useState('files');
  const visible = m.files.filter((f) => f.role !== 'preview');
  return (
    <div className="detail">
      <div className="title">
        <div>
          <small>{m.part_number}</small>
          <h1>{m.name}</h1>
        </div>
        <div className="detailActions">
          <button className="compactAction" onClick={edit}>
            <Pencil />
            Edit model
          </button>
          <button className="danger compactAction" onClick={confirmDelete}>
            <Trash2 />
            Delete model
          </button>
        </div>
      </div>
      <div className="detailGrid">
        <Viewer modelId={m.id} files={m.files} reload={reload} />
        <div className="panel">
          <dl>
            <dt>Design Project</dt>
            <dd>{m.design_project || '\u2014'}</dd>
            <dt>Category</dt>
            <dd>{m.category}</dd>
            <dt>Compatible robots</dt>
            <dd>{m.compatible_robots || '\u2014'}</dd>
            <dt>Dimensions</dt>
            <dd>
              {m.dimension_length || '\u2014'} &times; {m.dimension_width || '\u2014'} &times;{' '}
              {m.dimension_height || '\u2014'} {m.dimension_unit}
            </dd>
            <dt>ROM Price</dt>
            <dd>{m.rom_price ? `$${m.rom_price.replace(/^\$/, '')}` : '\u2014'}</dd>
            <dt>Last Quoted On</dt>
            <dd>{m.last_quoted_on || '\u2014'}</dd>
            <dt>Tags</dt>
            <dd className="bubbles">
              {m.tags
                .split(',')
                .map((x) => x.trim())
                .filter(Boolean)
                .map((t) => (
                  <span>{t}</span>
                ))}
            </dd>
          </dl>
        </div>
      </div>
      <div className="tabs">
        <button onClick={() => setTab('files')} className={tab === 'files' ? 'on' : ''}>
          Files
        </button>
        <button onClick={() => setTab('prices')} className={tab === 'prices' ? 'on' : ''}>
          Pricing History
        </button>
      </div>
      {tab === 'files' ? (
        <div className="rows">
          {visible.map((f) => (
            <div>
              <b>{f.original_name}</b>
              <a href={`${API}/files/${f.id}`}>
                <Download />
                Download
              </a>
            </div>
          ))}
        </div>
      ) : (
        <div className="pricingTable">
          <div className="pricingHeader">
            <b>ROM Price</b>
            <b>Last Quoted On</b>
            <b>Modified On</b>
          </div>
          {[...m.pricing_history].reverse().map((p) => (
            <div className="pricingRow">
              <b>${p.rom_price.replace(/^\$/, '')}</b>
              <span>{p.quoted_on || '\u2014'}</span>
              <span>{new Date(p.recorded_at).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
function Form({
  model,
  suggestions,
  close,
  done,
}: {
  model?: M;
  suggestions: string[];
  close: () => void;
  done: () => Promise<void>;
}) {
  const [rt, setRt] = useState(
      model?.tags
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean) || [],
    ),
    [rr, setRr] = useState(
      model?.compatible_robots
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean) || [],
    ),
    [step, setStep] = useState<File>(),
    [pack, setPack] = useState<File>(),
    [extra, setExtra] = useState<File[]>([]);
  const userFiles = model?.files.filter((f) => f.role !== 'preview') || [];
  const remove = async (f: F) => {
    await req(`/files/${f.id}`, { method: 'DELETE' });
    await done();
  };
  return (
    <div className="modal">
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget),
            data: any = {
              ...Object.fromEntries(f),
              tags: rt.join(', '),
              compatible_robots: rr.join(', '),
            };
          data.rom_price = String(data.rom_price || '').replace(/^\$/, '');
          let out: M;
          if (model)
            out = await req(`/models/${model.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data),
            });
          else
            out = await req('/models', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data),
            });
          for (const [file, role] of [
            [step, 'source'],
            [pack, 'pack_and_go'],
          ] as const)
            if (file) {
              const fd = new FormData();
              fd.append('role', role);
              fd.append('upload', file);
              await fetch(`${API}/models/${out.id}/files`, { method: 'POST', body: fd });
            }
          for (const file of extra) {
            const fd = new FormData();
            fd.append('role', 'document');
            fd.append('upload', file);
            await fetch(`${API}/models/${out.id}/files`, { method: 'POST', body: fd });
          }
          close();
          await done();
        }}
      >
        <h2>{model ? 'Edit model' : 'Add model'}</h2>
        <div className="g">
          <label>
            Part Number
            <input
              name="part_number"
              defaultValue={model?.part_number}
              required
              disabled={!!model}
            />
          </label>
          <label>
            Name
            <input name="name" defaultValue={model?.name} required />
          </label>
          <label>
            Design Project
            <input name="design_project" defaultValue={model?.design_project} />
          </label>
          <label>
            Category
            <select name="category" defaultValue={model?.category}>
              {CAT.map((x) => (
                <option>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Compatible Robots
            <RobotSelect value={rr} setValue={setRr} />
          </label>
          <fieldset>
            <legend>Dimensions</legend>
            {['length', 'width', 'height'].map((x) => (
              <label>
                {x}
                <input name={`dimension_${x}`} defaultValue={(model as any)?.[`dimension_${x}`]} />
              </label>
            ))}
            <label>
              Unit
              <select name="dimension_unit" defaultValue={model?.dimension_unit || 'in'}>
                {['mm', 'm', 'in', 'ft'].map((x) => (
                  <option>{x}</option>
                ))}
              </select>
            </label>
          </fieldset>
          <label>
            ROM Price
            <div className="money">
              <span>$</span>
              <input name="rom_price" defaultValue={model?.rom_price.replace(/^\$/, '')} />
            </div>
          </label>
          <label>
            Last Quoted On
            <input type="date" name="last_quoted_on" defaultValue={model?.last_quoted_on} />
          </label>
          <label className="wide">
            Tags
            <Tags value={rt} setValue={setRt} suggestions={suggestions} />
          </label>
          <label className="wide">
            Description
            <textarea name="description" defaultValue={model?.description} />
          </label>
          <div className="uploads">
            <UploadBox title="STEP/STP source" accept=".step,.stp" change={setStep} />
            <UploadBox title="Pack and Go ZIP" accept=".zip" change={setPack} />
            <label className="upload full">
              <FilePlus2 />
              <b>Drawings, BOMs, native CAD, images, and documents</b>
              <input
                type="file"
                multiple
                onChange={(e) => setExtra(Array.from(e.target.files || []))}
              />
              <small>{extra.length ? `${extra.length} selected` : 'Optional'}</small>
            </label>
          </div>
          {model && (
            <div className="editFiles wide">
              <h3>Associated files</h3>
              {userFiles.map((f) => (
                <div>
                  <span>{f.original_name}</span>
                  <button type="button" className="danger" onClick={() => void remove(f)}>
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <footer>
          <button type="button" onClick={close}>
            Cancel
          </button>
          <button className="primary">Save</button>
        </footer>
      </form>
    </div>
  );
}
function UploadBox({
  title,
  accept,
  change,
}: {
  title: string;
  accept: string;
  change: (f: File | undefined) => void;
}) {
  return (
    <label className="upload">
      <Upload />
      <b>{title}</b>
      <input type="file" accept={accept} onChange={(e) => change(e.target.files?.[0])} />
      <small>Optional</small>
    </label>
  );
}
function Confirm({ name, close, yes }: { name: string; close: () => void; yes: () => void }) {
  return (
    <div className="confirm">
      <div>
        <h2>Delete model?</h2>
        <p>
          Delete <b>{name}</b> and all associated stored files? This cannot be undone.
        </p>
        <footer>
          <button onClick={close}>Cancel</button>
          <button className="danger" onClick={yes}>
            Delete model
          </button>
        </footer>
      </div>
    </div>
  );
}
