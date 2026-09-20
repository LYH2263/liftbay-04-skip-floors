import { useEffect, useState } from "react";
import { api } from "../api/client";
type RestrictedFloor = { id: number; building_id: number; floor: number };
type B = { id: number; name: string; floors: number; restricted_floors: RestrictedFloor[] };
export default function BuildingsPage() {
  const [rows, setRows] = useState<B[]>([]);
  const [drafts, setDrafts] = useState<Record<number, number | "">>({});
  const [err, setErr] = useState("");
  const reload = () => api<B[]>("/buildings").then(setRows);
  useEffect(() => { reload(); }, []);
  async function add(b: B) {
    const floor = drafts[b.id];
    setErr("");
    if (floor === "" || floor === undefined) return;
    try {
      await api(`/buildings/${b.id}/restricted-floors`, { method: "POST", body: JSON.stringify({ floor }) });
      setDrafts(d => ({ ...d, [b.id]: "" }));
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  async function remove(b: B, rf: RestrictedFloor) {
    setErr("");
    try {
      await api(`/buildings/${b.id}/restricted-floors/${rf.id}`, { method: "DELETE" });
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>楼栋</h2>
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>名称</th><th>楼层数</th><th>禁停层</th></tr></thead>
    <tbody>{rows.map(b => {
      const floors = [...b.restricted_floors].sort((x, y) => x.floor - y.floor);
      return (<tr key={b.id}>
        <td>{b.name}</td>
        <td className="mono">{b.floors}</td>
        <td>
          <div className="restricted-list">
            {floors.map(rf => (
              <span key={rf.id} className="chip chip-restricted" title="禁停层">
                {rf.floor}F
                <button type="button" className="chip-x" onClick={() => remove(b, rf)}>×</button>
              </span>
            ))}
            {!floors.length && <span className="muted">无</span>}
            <span className="restricted-add">
              <input
                type="number" min={1} max={b.floors}
                value={drafts[b.id] ?? ""}
                onChange={e => setDrafts(d => ({ ...d, [b.id]: e.target.value === "" ? "" : Number(e.target.value) }))}
                style={{ width: 72 }}
              />
              <button type="button" onClick={() => add(b)}>标为禁停</button>
            </span>
          </div>
        </td>
      </tr>);
    })}</tbody></table>
  </>);
}
