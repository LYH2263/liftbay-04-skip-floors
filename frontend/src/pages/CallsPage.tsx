import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
type RestrictedFloor = { id: number; floor: number };
type B = { id: number; name: string; floors: number; restricted_floors: RestrictedFloor[] };
type Call = { id: number; floor: number; direction: string; passengers: number; status: string; assigned_car_id: number | null; score: string };
export default function CallsPage() {
  const [buildings, setBuildings] = useState<B[]>([]);
  const [rows, setRows] = useState<Call[]>([]);
  const [bid, setBid] = useState<number | "">("");
  const [floor, setFloor] = useState(5);
  const [dir, setDir] = useState("up");
  const [pax, setPax] = useState(1);
  const [err, setErr] = useState("");
  const reload = () => api<Call[]>("/calls").then(setRows);
  useEffect(() => {
    api<B[]>("/buildings").then(b => { setBuildings(b); if (b[0]) setBid(b[0].id); });
    reload();
  }, []);
  const building = useMemo(() => buildings.find(b => b.id === bid), [buildings, bid]);
  const banned = useMemo(
    () => new Set((building?.restricted_floors ?? []).map(r => r.floor)),
    [building],
  );
  const levels = useMemo(
    () => (building ? Array.from({ length: building.floors }, (_, i) => i + 1) : []),
    [building],
  );
  function pickBuilding(id: number) {
    setBid(id);
    setErr("");
    const target = buildings.find(b => b.id === id);
    if (!target) return;
    const blocked = new Set(target.restricted_floors.map(r => r.floor));
    if (blocked.has(floor)) {
      const firstOpen = Array.from({ length: target.floors }, (_, i) => i + 1).find(f => !blocked.has(f));
      setFloor(firstOpen ?? 1);
    }
  }
  async function create() {
    setErr("");
    try {
      await api("/calls", { method: "POST", body: JSON.stringify({ building_id: bid, floor, direction: dir, passengers: pax }) });
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>呼梯</h2>
    <div className="toolbar">
      <select value={bid} onChange={e => pickBuilding(Number(e.target.value))}>{buildings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
      <select value={floor} onChange={e => setFloor(Number(e.target.value))}>
        {levels.map(f => <option key={f} value={f} disabled={banned.has(f)}>{f} 层{banned.has(f) ? "（禁停）" : ""}</option>)}
      </select>
      <select value={dir} onChange={e => setDir(e.target.value)}><option value="up">上行</option><option value="down">下行</option></select>
      <input type="number" value={pax} min={1} onChange={e => setPax(Number(e.target.value))} style={{ width: 64 }} />
      <button onClick={create}>登记呼梯</button>
    </div>
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>ID</th><th>楼层</th><th>方向</th><th>人数</th><th>状态</th><th>轿厢</th><th>评分</th></tr></thead>
    <tbody>{rows.map(c => <tr key={c.id}><td>{c.id}</td><td className="mono">{c.floor}</td><td>{c.direction}</td><td>{c.passengers}</td><td>{c.status}</td><td>{c.assigned_car_id ?? "—"}</td><td className="mono">{c.score || "—"}</td></tr>)}</tbody></table>
  </>);
}
