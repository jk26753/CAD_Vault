import { useEffect, useRef, useState } from 'react';
import * as T from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { API, type F } from '../api';
export default function Viewer({
  modelId,
  files,
  reload,
}: {
  modelId: number;
  files: F[];
  reload: () => Promise<void>;
}) {
  const ref = useRef<HTMLDivElement>(null),
    [msg, setMsg] = useState(''),
    source = files.find((f) => f.role === 'source'),
    glb = files.find((f) => f.role === 'preview' && f.original_name.endsWith('.glb'));
  useEffect(() => {
    if (!ref.current) return;
    const h = ref.current;
    let w: Worker | undefined;
    const s = new T.Scene();
    s.background = new T.Color(0x080d15);
    const c = new T.PerspectiveCamera(45, 1, 0.01, 1e5),
      r = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    h.replaceChildren(r.domElement);
    const o = new OrbitControls(c, r.domElement);
    s.add(new T.HemisphereLight(0xffffff, 0x334155, 2.3));
    const l = new T.DirectionalLight(0xffffff, 2.5);
    l.position.set(100, 150, 100);
    s.add(l);
    const fit = (x: T.Object3D) => {
      const b = new T.Box3().setFromObject(x),
        z = b.getSize(new T.Vector3()),
        q = b.getCenter(new T.Vector3()),
        m = Math.max(z.x, z.y, z.z) || 100;
      x.position.sub(q);
      c.position.set(m * 1.25, m * 0.85, m * 1.25);
      c.updateProjectionMatrix();
      o.target.set(0, 0, 0);
      o.update();
    };
    const up = async (b: Blob, n: string) => {
      const f = new FormData();
      f.append('role', 'preview');
      f.append('upload', b, n);
      await fetch(`${API}/models/${modelId}/files`, { method: 'POST', body: f });
    };
    (async () => {
      try {
        if (glb) {
          setMsg('Loading saved preview...');
          const g = await new GLTFLoader().loadAsync(`${API}/files/${glb.id}`);
          s.add(g.scene);
          fit(g.scene);
          setMsg('');
          return;
        }
        if (!source) {
          setMsg('Upload a STEP/STP source file to generate a preview.');
          return;
        }
        setMsg('Parsing STEP in background...');
        const buffer = await (await fetch(`${API}/files/${source.id}`)).arrayBuffer();
        const ms: any[] = await new Promise((ok, no) => {
          w = new Worker(new URL('../workers/step.worker.ts', import.meta.url), { type: 'module' });
          w.onmessage = (e: any) => (e.data.ok ? ok(e.data.meshes) : no(Error(e.data.error)));
          w.postMessage({ buffer }, [buffer]);
        });
        const g = new T.Group();
        for (const m of ms) {
          const x = new T.BufferGeometry();
          x.setAttribute('position', new T.BufferAttribute(m.positions, 3));
          m.normals
            ? x.setAttribute('normal', new T.BufferAttribute(m.normals, 3))
            : x.computeVertexNormals();
          x.setIndex(new T.BufferAttribute(m.indices, 1));
          g.add(
            new T.Mesh(
              x,
              new T.MeshStandardMaterial({
                color: m.color ? new T.Color(...m.color) : new T.Color(0xcbd5e1),
                roughness: 0.7,
                side: T.DoubleSide,
              }),
            ),
          );
        }
        s.add(g);
        fit(g);
        setMsg('Creating cached preview...');
        const a = await new Promise<ArrayBuffer>((ok, no) =>
          new GLTFExporter().parse(g, (x) => (x instanceof ArrayBuffer ? ok(x) : no(Error())), no, {
            binary: true,
          }),
        );
        await up(new Blob([a]), 'preview.glb');
        r.render(s, c);
        const png = await new Promise<Blob>((ok, no) =>
          r.domElement.toBlob((x) => (x ? ok(x) : no(Error())), 'image/png'),
        );
        await up(png, 'thumbnail_dark.png');
        await reload();
        setMsg('');
      } catch (e) {
        setMsg(e instanceof Error ? e.message : 'Viewer error');
      }
    })();
    const rs = () => {
      r.setSize(h.clientWidth, h.clientHeight, false);
      c.aspect = h.clientWidth / h.clientHeight;
      c.updateProjectionMatrix();
    };
    const ro = new ResizeObserver(rs);
    ro.observe(h);
    rs();
    let id = 0;
    const loop = () => {
      o.update();
      r.render(s, c);
      id = requestAnimationFrame(loop);
    };
    loop();
    return () => {
      w?.terminate();
      cancelAnimationFrame(id);
      ro.disconnect();
      o.dispose();
      r.dispose();
    };
  }, [modelId, source?.id, glb?.id]);
  return (
    <div className="viewer">
      <div className="canvas" ref={ref} />
      {msg && <div className="viewerMessage">{msg}</div>}
    </div>
  );
}
