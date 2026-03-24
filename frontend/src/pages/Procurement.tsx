import { useStore } from '../store/useStore';
import { ShieldCheck, Truck } from 'lucide-react';

export default function Procurement() {
  const { parseResult, findings } = useStore();
  const procRows = parseResult?.data.procurement || [];
  
  if (!procRows || procRows.length === 0) {
    return (
      <div className="bg-finCard p-12 text-center rounded-2xl border border-zinc-800">
        <h2 className="text-xl font-bold text-white mb-2">No Procurement Data</h2>
        <p className="text-zinc-500">Upload vendor purchase orders to analyze benchmarking.</p>
      </div>
    );
  }

  const formatINR = (val: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  const getVariance = (price: number, bench: number) => {
    if (!bench) return 0;
    return ((price - bench) / bench) * 100;
  };

  const flaggedRows = procRows.filter(r => {
    const p = parseFloat(r.unit_price || r['Unit Price'] || r.price || 0);
    const b = parseFloat(r.benchmark || r.Benchmark || 0);
    return getVariance(p, b) > 15;
  });

  const totalOverspend = flaggedRows.reduce((acc, r) => {
    const q = parseFloat(r.qty || r.Qty || 1);
    const p = parseFloat(r.unit_price || r['Unit Price'] || 0);
    const b = parseFloat(r.benchmark || r.Benchmark || 0);
    return acc + ((p - b) * q);
  }, 0);

  const duplicateVendors = findings.filter(f => f.category === 'vendor' && !f.resolved);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-6">
         <div className="bg-rose-900/10 border border-rose-900/30 p-5 rounded-2xl flex items-center space-x-4">
           <div className="p-3 bg-rose-500/10 rounded-xl text-rose-400"><ShieldCheck /></div>
           <div><p className="text-sm text-zinc-400 uppercase tracking-wider">Flagged POs</p><p className="text-2xl font-bold text-rose-400">{flaggedRows.length}</p></div>
         </div>
         <div className="bg-rose-900/10 border border-rose-900/30 p-5 rounded-2xl flex items-center space-x-4">
           <div className="p-3 bg-rose-500/10 rounded-xl text-rose-400"><Truck /></div>
           <div><p className="text-sm text-zinc-400 uppercase tracking-wider">Total Overspend</p><p className="text-2xl font-bold text-rose-400">{formatINR(totalOverspend)}</p></div>
         </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-finCard p-6 rounded-2xl border border-zinc-800">
          <h3 className="text-lg font-bold text-white mb-4">Purchase Order Variance Table</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-zinc-300">
              <thead className="text-xs text-zinc-500 uppercase bg-zinc-900/50">
                <tr>
                  <th className="px-4 py-3">PO ID</th>
                  <th className="px-4 py-3">Item</th>
                  <th className="px-4 py-3">Vendor</th>
                  <th className="px-4 py-3">Qty</th>
                  <th className="px-4 py-3">Unit Price</th>
                  <th className="px-4 py-3">Benchmark</th>
                  <th className="px-4 py-3">Variance %</th>
                  <th className="px-4 py-3">Total (INR)</th>
                  <th className="px-4 py-3 text-center">Flag</th>
                </tr>
              </thead>
              <tbody>
                {procRows.map((r, i) => {
                  const q = parseFloat(r.qty || r.Qty || 1);
                  const p = parseFloat(r.unit_price || r['Unit Price'] || r.price || 0);
                  const b = parseFloat(r.benchmark || r.Benchmark || 0);
                  const v = getVariance(p, b);
                  const isFlagged = v > 15;

                  return (
                    <tr key={i} className={`border-b border-zinc-800/50 transition-colors ${isFlagged ? 'bg-rose-900/10 hover:bg-rose-900/20' : 'hover:bg-white/5'}`}>
                      <td className="px-4 py-3 font-mono text-xs text-zinc-400">{r.po_id || `PO-${1000+i}`}</td>
                      <td className="px-4 py-3">{r.item || r.Item || 'Item'}</td>
                      <td className="px-4 py-3">{r.vendor || r.Vendor || 'Vendor'}</td>
                      <td className="px-4 py-3 text-right">{q}</td>
                      <td className="px-4 py-3 text-right">{formatINR(p)}</td>
                      <td className="px-4 py-3 text-right">{formatINR(b)}</td>
                      <td className={`px-4 py-3 text-right ${isFlagged ? 'text-rose-400 font-bold' : 'text-emerald-400'}`}>{v.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono">{formatINR(p * q)}</td>
                      <td className="px-4 py-3 text-center">
                        {isFlagged ? <span className="bg-rose-500/20 text-rose-400 px-2 py-1 rounded text-xs font-bold ring-1 ring-rose-500/50">HIGH</span> : <span className="text-zinc-600">-</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-finCard p-6 rounded-2xl border border-zinc-800">
          <h3 className="text-lg font-bold text-white mb-4">Vendor Consolidation</h3>
          <div className="space-y-4">
            {duplicateVendors.map(v => (
              <div key={v.id} className="p-4 bg-zinc-900/80 rounded-xl border border-rose-900/50 ring-1 ring-rose-500/10">
                <span className="text-xs font-bold text-rose-400 uppercase tracking-wider mb-1 block">Duplicate Profile Risk</span>
                <p className="font-medium text-white mb-2">{v.title}</p>
                <p className="text-sm text-zinc-400">{v.rootCause}</p>
              </div>
            ))}
            {duplicateVendors.length === 0 && <p className="text-sm text-emerald-400 bg-emerald-500/10 p-4 rounded-xl">No duplicate vendors detected spanning identical PAN/GSTINs.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
