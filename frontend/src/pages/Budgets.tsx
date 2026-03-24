import { useState, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';
import { PieChart as PieChartIcon, TrendingDown, Filter } from 'lucide-react';

export default function Budgets() {
  const { parseResult } = useStore();
  const budgetRows = parseResult?.data.budget || [];
  const [quarter, setQuarter] = useState<string>('All');
  
  if (!budgetRows || budgetRows.length === 0) {
    return (
      <div className="bg-finCard p-12 text-center rounded-2xl border border-zinc-800">
        <h2 className="text-xl font-bold text-white mb-2">No Budget Data</h2>
        <p className="text-zinc-500">Upload department budget exports vs actuals to view tracking.</p>
      </div>
    );
  }

  const formatINR = (val: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  const filteredRows = useMemo(() => {
    if (quarter === 'All') return budgetRows;
    return budgetRows.filter(r => (r.quarter || r.Quarter || 'Q1') === quarter);
  }, [budgetRows, quarter]);

  const chartDataMap = new Map<string, any>();
  filteredRows.forEach(row => {
    const dept = row.department || row.Department || row.dept || 'Unknown';
    const actual = parseFloat(row.actual || row.Actual || row.spend || 0);
    const budget = parseFloat(row.budget || row.Budget || 0);
    
    if (!chartDataMap.has(dept)) chartDataMap.set(dept, { name: dept, actual: 0, budget: 0 });
    const entry = chartDataMap.get(dept);
    entry.actual += actual;
    entry.budget += budget;
  });
  
  const deptData = Array.from(chartDataMap.values()).map(d => {
    const variance = d.budget > 0 ? ((d.actual - d.budget) / d.budget) * 100 : 0;
    return { ...d, variance };
  }).sort((a, b) => b.variance - a.variance);

  const getStatusBadge = (variance: number) => {
    if (variance > 30) return <span className="bg-rose-500/20 text-rose-400 border border-rose-500/50 px-2 py-1 rounded text-xs font-bold w-20 inline-block text-center shadow-[0_0_10px_rgba(244,63,94,0.2)]">CRITICAL</span>;
    if (variance > 10) return <span className="bg-amber-500/20 text-amber-500 border border-amber-500/50 px-2 py-1 rounded text-xs font-bold w-20 inline-block text-center shadow-[0_0_10px_rgba(245,158,11,0.2)]">WATCH</span>;
    if (variance > 0) return <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-1 rounded text-xs font-bold w-20 inline-block text-center">OK</span>;
    return <span className="bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 px-2 py-1 rounded text-xs font-bold w-20 inline-block text-center">GOOD</span>;
  };

  const totalBudget = deptData.reduce((a, b) => a + b.budget, 0);
  const totalActual = deptData.reduce((a, b) => a + b.actual, 0);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center"><PieChartIcon className="mr-3 text-rose-500" /> Operating Budgets vs Actuals</h2>
        
        <div className="flex items-center space-x-2 bg-zinc-900/50 p-1.5 rounded-xl border border-zinc-800">
           <Filter size={16} className="text-zinc-500 ml-2" />
           {['All', 'Q1', 'Q2', 'Q3', 'Q4'].map(q => (
             <button 
               key={q} 
               onClick={() => setQuarter(q)}
               className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${quarter === q ? 'bg-zinc-800 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-300'}`}
             >
               {q}
             </button>
           ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
         <div className="col-span-1 bg-finCard border border-zinc-800 p-6 rounded-2xl">
           <p className="text-sm text-zinc-500 uppercase tracking-wider mb-2">Total Budget Allocation</p>
           <p className="text-3xl font-bold text-white mb-6">{formatINR(totalBudget)}</p>
           
           <p className="text-sm text-zinc-500 uppercase tracking-wider mb-2">Total Actual Spend</p>
           <p className={`text-3xl font-bold ${totalActual > totalBudget ? 'text-rose-400' : 'text-emerald-400'}`}>{formatINR(totalActual)}</p>
           
           <div className="mt-6 pt-6 border-t border-zinc-800">
             <div className="flex justify-between items-center text-sm">
                <span className="text-zinc-400">Run Rate</span>
                <span className="font-mono text-white">{totalBudget > 0 ? ((totalActual / totalBudget) * 100).toFixed(1) : 0}%</span>
             </div>
             <div className="w-full bg-zinc-900 rounded-full h-2 mt-3 overflow-hidden">
                <div 
                  className={`h-full ${totalActual > totalBudget ? 'bg-rose-500' : 'bg-emerald-500'}`} 
                  style={{ width: `${Math.min((totalActual / totalBudget) * 100, 100)}%` }} 
                />
             </div>
           </div>
         </div>
         
         <div className="col-span-3 bg-finCard p-6 rounded-2xl border border-zinc-800 h-80">
           <ResponsiveContainer width="100%" height="100%">
             <BarChart data={deptData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
               <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
               <XAxis dataKey="name" stroke="#a1a1aa" tick={{ fill: '#a1a1aa' }} />
               <YAxis stroke="#a1a1aa" tickFormatter={(val) => `₹${val/1000}k`} />
               <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }} 
                  itemStyle={{ color: '#fff' }}
                  formatter={(val: number) => formatINR(val)}
               />
               <Legend wrapperStyle={{ paddingTop: '20px' }} />
               <Bar dataKey="budget" fill="#3f3f46" name="Allocated Budget" radius={[4, 4, 0, 0]} />
               <Bar dataKey="actual" fill="#f43f5e" name="Actual Spend" radius={[4, 4, 0, 0]} />
             </BarChart>
           </ResponsiveContainer>
         </div>
      </div>

      <div className="bg-finCard rounded-2xl border border-zinc-800 overflow-hidden">
        <div className="p-5 border-b border-zinc-800 bg-zinc-900/30 flex justify-between items-center">
           <h3 className="text-lg font-bold text-white flex items-center"><TrendingDown className="mr-2 text-rose-500" size={20} /> Department Variance Report</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="text-xs text-zinc-500 uppercase bg-zinc-900/80">
              <tr>
                <th className="px-6 py-4">Department</th>
                <th className="px-6 py-4 text-right">Budget (INR)</th>
                <th className="px-6 py-4 text-right">Actual (INR)</th>
                <th className="px-6 py-4 text-right">Variance (INR)</th>
                <th className="px-6 py-4 text-right">Variance %</th>
                <th className="px-6 py-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {deptData.map((d, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 font-medium text-white">{d.name}</td>
                  <td className="px-6 py-4 text-right font-mono text-zinc-400">{formatINR(d.budget)}</td>
                  <td className="px-6 py-4 text-right font-mono text-white">{formatINR(d.actual)}</td>
                  <td className="px-6 py-4 text-right font-mono items-center space-x-1 justify-end flex">
                    <span className={d.actual > d.budget ? 'text-rose-400' : 'text-emerald-400'}>
                      {d.actual > d.budget ? '+' : ''}{formatINR(d.actual - d.budget)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-bold">
                    <span className={d.variance > 0 ? 'text-rose-400' : 'text-emerald-400'}>
                      {d.variance > 0 ? '+' : ''}{d.variance.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-center">
                    {getStatusBadge(d.variance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
