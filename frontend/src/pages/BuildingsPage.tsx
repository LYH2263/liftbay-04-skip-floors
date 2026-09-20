import { useEffect, useState } from "react";
import { api } from "../api/client";
type Blocked = { id: number; building_id: number; floor: number };
type B = { id: number; name: string; floors: number; blocked_floors: Blocked[] };
export default function BuildingsPage() {
  const [rows, setRows] = useState<B[]>([]);
  const [drafts, setDrafts] = useState<Record<number, number>>({});
  const [err, setErr] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const reload = () => api<B[]>("/buildings").then(setRows);
  useEffect(() => { reload(); }, []);

  async function addBlocked(b: B) {
    const floor = drafts[b.id] ?? 0;
    setErr(e => ({ ...e, [b.id]: "" }));
    setBusy(b.id);
    try {
      await api(`/buildings/${b.id}/blocked-floors`, { method: "POST", body: JSON.stringify({ floor }) });
      setDrafts(d => ({ ...d, [b.id]: 0 }));
      await reload();
    } catch (e) {
      setErr(prev => ({ ...prev, [b.id]: e instanceof Error ? e.message : String(e) }));
    } finally {
      setBusy(null);
    }
  }

  async function removeBlocked(b: B, floor: number) {
    setErr(e => ({ ...e, [b.id]: "" }));
    setBusy(b.id);
    try {
      await api(`/buildings/${b.id}/blocked-floors/${floor}`, { method: "DELETE" });
      await reload();
    } catch (e) {
      setErr(prev => ({ ...prev, [b.id]: e instanceof Error ? e.message : String(e) }));
    } finally {
      setBusy(null);
    }
  }

  return (<>
    <h2>楼栋</h2>
    <table className="table"><thead><tr><th>名称</th><th>楼层数</th><th>禁停层</th></tr></thead>
    <tbody>{rows.map(b => {
      const blocked = [...b.blocked_floors].sort((x, y) => x.floor - y.floor).map(f => f.floor);
      const draft = drafts[b.id] ?? 0;
      const draftTaken = blocked.includes(draft);
      return (
        <tr key={b.id}>
          <td>{b.name}</td>
          <td className="mono">{b.floors}</td>
          <td>
            <div className="blocked-row">
              {blocked.map(f => (
                <span key={f} className="blocked-chip">
                  {f}F
                  <button
                    type="button"
                    className="blocked-chip-x"
                    title="取消禁停"
                    disabled={busy === b.id}
                    onClick={() => removeBlocked(b, f)}
                  >×</button>
                </span>
              ))}
              {!blocked.length && <span className="blocked-empty">无</span>}
              <input
                type="number" min={1} max={b.floors}
                value={draft || ""}
                placeholder="楼层"
                style={{ width: 76 }}
                onChange={e => setDrafts(d => ({ ...d, [b.id]: Number(e.target.value) }))}
              />
              <button
                type="button"
                disabled={busy === b.id || draft < 1 || draft > b.floors || draftTaken}
                onClick={() => addBlocked(b)}
              >标为禁停</button>
              {err[b.id] && <span className="err blocked-err">{err[b.id]}</span>}
            </div>
          </td>
        </tr>
      );
    })}</tbody></table>
  </>);
}
