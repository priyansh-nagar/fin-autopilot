import { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { formatINR } from '../utils';

export default function SavingsCard({ totalRecovered, categoryBreakdown, onExportPDF }: any) {
  // Animated counter
  const springValue = useSpring(0, { bounce: 0, duration: 2000 });
  const [displayValue, setDisplayValue] = useState("₹0");

  useEffect(() => {
    springValue.set(totalRecovered);
  }, [totalRecovered]);

  useEffect(() => {
    return springValue.onChange((latest) => {
      setDisplayValue(formatINR(latest));
    });
  }, [springValue]);

  const COLORS = ['#8b5cf6', '#06b6d4', '#10b981', '#f43f5e'];
  const chartData = Object.keys(categoryBreakdown).map(k => ({ name: k, value: categoryBreakdown[k] })).filter(d => d.value > 0);

  return (
    <div className="bg-finCard border border-zinc-800/80 p-6 rounded-2xl flex items-center justify-between mb-10 shadow-lg relative overflow-hidden group hover:border-violet-500/30 transition-colors">
      <div className="absolute top-0 right-0 w-64 h-64 bg-violet-600/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none group-hover:bg-violet-600/20 transition-all"></div>
      
      <div className="relative z-10">
        <h3 className="text-sm font-medium text-violet-400 mb-2 uppercase tracking-wider">Savings Unlocked This Session</h3>
        <motion.div 
          className="text-5xl font-extrabold text-white tracking-tight drop-shadow-[0_0_15px_rgba(139,92,246,0.5)]"
          key={totalRecovered}
          initial={{ scale: 1.1, color: '#a78bfa' }}
          animate={{ scale: 1, color: '#ffffff' }}
          transition={{ duration: 0.5 }}
        >
          {displayValue}
        </motion.div>
      </div>
      
      {chartData.length > 0 && (
        <div className="w-[300px] h-[100px] flex items-center relative z-10">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                innerRadius={30}
                outerRadius={45}
                paddingAngle={5}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => formatINR(value)} contentStyle={{ backgroundColor: '#18181b', border: '1px solid #27272a', borderRadius: '8px', color: '#fff' }} itemStyle={{ color: '#fff' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="relative z-10">
         <button onClick={onExportPDF} className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-6 py-3 rounded-xl font-medium transition-all text-sm border border-zinc-700 hover:border-violet-500/50 shadow-sm">
           Export CFO Report (PDF)
         </button>
      </div>
    </div>
  );
}
