// Blueprint-style table sketch, ported from the Python tool's canvas drawing.
// ML: left margin, wider than M so the height label (drawn left of the legs) is not clipped.
const CW = 300, CH = 230, M = 34, ML = 50, K = 0.4;
const DIM = '#2f5f73', BRIGHT = '#00d1ff', TEXT = '#e6edf3';

export default function TablePreview({ L, W, H }: { L: number; W: number; H: number }) {
  const s = Math.min((CW - ML - M) / (W + K * L), (CH - 2 * M) / (H + 0.6 * K * L));
  const p = (w: number, l: number, h: number): [number, number] =>
    [ML + (w + K * l) * s, CH - M - (h + 0.6 * K * l) * s];
  const line = (a: [number, number], b: [number, number], stroke: string, key: string) =>
    <line key={key} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={stroke} strokeWidth={2} />;
  const poly = (pts: [number, number][]) => pts.map(q => q.join(',')).join(' ');
  const t = 3;

  const grid = [];
  for (let x = 0; x < CW; x += 20) grid.push(<line key={`x${x}`} x1={x} y1={0} x2={x} y2={CH} stroke="#1c232c" />);
  for (let y = 0; y < CH; y += 20) grid.push(<line key={`y${y}`} x1={0} y1={y} x2={CW} y2={y} stroke="#1c232c" />);

  const [wx, wy] = p(W / 2, 0, 0), [lx, ly] = p(W, L / 2, 0), [hx, hy] = p(0, 0, H / 2);

  return (
    <svg viewBox={`0 0 ${CW} ${CH}`} className="cfgPreview" role="img" aria-label={`Table ${L} by ${W} by ${H} inches`}>
      {grid}
      {/* back legs and rails */}
      {[0, W].map(w => line(p(w, L, 0), p(w, L, H), DIM, `bl${w}`))}
      {line(p(0, L, 4), p(W, L, 4), DIM, 'br')}
      {line(p(0, 0, 4), p(0, L, 4), DIM, 'sl')}
      {line(p(W, 0, 4), p(W, L, 4), DIM, 'sr')}
      {/* front legs and rail */}
      {[0, W].map(w => line(p(w, 0, 0), p(w, 0, H), BRIGHT, `fl${w}`))}
      {line(p(0, 0, 4), p(W, 0, 4), BRIGHT, 'fr')}
      {/* top slab */}
      <polygon points={poly([p(0, 0, H), p(W, 0, H), p(W, L, H), p(0, L, H)])} fill="#103442" stroke={BRIGHT} strokeWidth={2} />
      <polygon points={poly([p(0, 0, H - t), p(W, 0, H - t), p(W, 0, H), p(0, 0, H)])} fill="#0a222c" stroke={BRIGHT} />
      <polygon points={poly([p(W, 0, H - t), p(W, L, H - t), p(W, L, H), p(W, 0, H)])} fill="#0a222c" stroke={BRIGHT} />
      {/* dimension labels */}
      <text x={wx} y={wy + 14} textAnchor="middle" dominantBaseline="middle" fill={TEXT}>W {W}</text>
      <text x={lx + 10} y={ly + 4} dominantBaseline="middle" fill={TEXT}>L {L}</text>
      <text x={hx - 8} y={hy} textAnchor="end" dominantBaseline="middle" fill={TEXT}>H {H}</text>
    </svg>
  );
}
