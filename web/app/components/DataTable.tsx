type Row = { label: string; value: React.ReactNode };

export function DataTable({ rows }: { rows: Row[] }) {
  return (
    <table className="w-full text-sm border-collapse">
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-rule align-top">
            <th className="text-left font-typewriter uppercase text-xs tracking-wider text-faded-ink py-3 pr-6 w-1/3">
              {r.label}
            </th>
            <td className="data-cell py-3 text-ink break-all">{r.value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
