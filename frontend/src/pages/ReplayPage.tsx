import { useEffect, useState } from "react";
import { api } from "../api/client";
type Log = { id: number; call_id: number; car_id: number | null; detail: string; created_at: string };
function tag(detail: string, carId: number | null): { text: string; cls: string } | null {
  if (carId !== null) return null;
  if (detail.includes("禁停")) return { text: "禁停层", cls: "tag tag-restricted" };
  if (detail.includes("满员")) return { text: "轿厢满员", cls: "tag tag-full" };
  return { text: "拒绝", cls: "tag tag-full" };
}
export default function ReplayPage() {
  const [rows, setRows] = useState<Log[]>([]);
  useEffect(() => { api<Log[]>("/replay").then(setRows); }, []);
  return (<>
    <h2>回放</h2>
    <table className="table"><thead><tr><th>时间</th><th>呼梯</th><th>轿厢</th><th>原因</th><th>详情</th></tr></thead>
    <tbody>{rows.map(l => {
      const t = tag(l.detail, l.car_id);
      return (<tr key={l.id}>
        <td className="mono">{new Date(l.created_at).toLocaleString()}</td>
        <td>#{l.call_id}</td>
        <td>{l.car_id ?? "—"}</td>
        <td>{t ? <span className={t.cls}>{t.text}</span> : <span className="tag tag-ok">已派工</span>}</td>
        <td>{l.detail}</td>
      </tr>);
    })}</tbody></table>
  </>);
}
