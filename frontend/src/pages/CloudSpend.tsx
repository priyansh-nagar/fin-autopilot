import React from 'react';
import { useStore } from '../store/useStore';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { AlertTriangle, Cpu, Database } from 'lucide-react';

export default function CloudSpend() {
  const { cloudRows, findings } = useStore();
  
  if (!cloudRows || cloudRows.length === 0) {
    return (
      <div className="bg-finCard p-12 text-center rounded-2xl border border-zinc-800">
        <h2 className="text-xl font-bold text-white mb-2">No Cloud Data Detected</h2>
        <p className="text-zinc-500">Upload an AWS Cost Explorer CSV to visualize cloud spend.</p>
      </div>
    );
  }

  const cloudFindings = findings.filter(f => f.category === 'Cloud' && !f.resolved);

  // Parse chart data
  // Assuming columns: date/month, service, cost
  const chartDataMap = new Map<string, any>();
  cloudRows.forEach(row => {
    const d = row.month || row.date || row.Date || 'Unknown';
    const s = (row.service || row.Service || 'EC2').toLowerCase();
    const c = parseFloat(row.cost || row.Cost || row.amount || 0);
    
    if (!chartDataMap.has(d)) chartDataMap.set(d, { name: d, ec2: 0, s3: 0, rds: 0, other: 0 });
    const entry = chartDataMap.get(d);
    
    if (s.includes('ec2')) entry.ec2 += c;
    else if (s.includes('s3')) entry.s3 += c;
    else if (s.includes('rds')) entry.rds += c;
    else entry.other += c;
  });
  
  const chartData = Array.from(chartDataMap.values()).sort((a,b) => a.name.localeCompare(b.name));

  const formatINR = (val: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-6">
         <div className="bg-finCard border border-cyan-900/30 p-5 rounded-2xl flex items-center space-x-4">
           <div className="p-3 bg-cyan-500/10 rounded-xl text-cyan-400"><Cpu /></div>
           <div><p className="text-sm text-zinc-400">Total Cloud Spend</p><p className="text-xl font-bold">{formatINR(cloudRows.reduce((a, b) => a + parseFloat(b.cost || b.Cost || 0), 0))}</p></div>
         </div>
      </div>

      {/* Line Chart */}
      <div className="bg-finCard p-6 rounded-2xl border border-zinc-800 h-96">
        <h3 className="text-lg font-bold text-white mb-6">Monthly Spend per AWS Service</h3>
        <ResponsiveContainer width="100%" height="85%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
            <XAxis dataKey="name" stroke="#a1a1aa" />
            <YAxis stroke="#a1a1aa" tickFormatter={(val) => `₹${val/1000}k`} />
            <Tooltip contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px' }} />
            <Line type="monotone" dataKey="ec2" stroke="#8b5cf6" strokeWidth={3} dot={{r: 4}} name="EC2 Compute" />
            <Line type="monotone" dataKey="s3" stroke="#06b6d4" strokeWidth={3} dot={{r: 4}} name="S3 Storage" />
            <Line type="monotone" dataKey="rds" stroke="#10b981" strokeWidth={3} dot={{r: 4}} name="RDS Database" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Spike Findings */}
        <div className="bg-finCard p-6 rounded-2xl border border-zinc-800">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center"><AlertTriangle className="mr-2 text-amber-500" size={20} /> Spike Findings</h3>
          <div className="space-y-3">
            {cloudFindings.map(f => (
              <div key={f.id} className="p-4 bg-zinc-900/50 rounded-xl border border-zinc-800/80">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-white">{f.title}</h4>
                  <span className="text-rose-400 font-mono font-medium">{formatINR(f.inrImpact)} Waste</span>
                </div>
                <p className="text-sm text-zinc-400">{f.rootCause}</p>
                <div className="mt-3 pt-3 border-t border-zinc-800 text-sm">
                  <span className="text-violet-400 font-medium">Action: </span><span className="text-zinc-300">{f.recommendation}</span>
                </div>
              </div>
            ))}
            {cloudFindings.length === 0 && <p className="text-zinc-500">No active compute spikes detected.</p>}
          </div>
        </div>

        {/* Idle Resources Table */}
        <div className="bg-finCard p-6 rounded-2xl border border-zinc-800 overflow-y-auto max-h-96">
          <h3 className="text-lg font-bold text-white mb-4">Idle Resources Dashboard</h3>
          <table className="w-full text-left text-sm text-zinc-300">
            <thead className="text-xs text-zinc-500 uppercase bg-zinc-900/50 hidden md:table-header-group">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Resource ID</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Days Idle</th>
                <th className="px-4 py-3 rounded-tr-lg">Monthly Cost (INR)</th>
              </tr>
            </thead>
            <tbody>
              {cloudRows.filter(r => (r.status || '').toLowerCase().includes('idle') || parseInt(r.days_idle || 0) > 15).map((r, i) => (
                <tr key={i} className="border-b border-zinc-800/50 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{r.resource_id || `i-0x${Math.floor(Math.random()*100000)}`}</td>
                  <td className="px-4 py-3">{r.type || r.service || 'Unknown'}</td>
                  <td className="px-4 py-3 text-amber-500 font-medium">{r.days_idle || 16}</td>
                  <td className="px-4 py-3 text-rose-400 font-mono">{formatINR(parseFloat(r.cost || 0))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
