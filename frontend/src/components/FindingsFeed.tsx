import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Info, CheckCircle, X, ShieldAlert } from 'lucide-react';
import { formatINR } from '../utils';
import { Finding } from '../store/useStore';

export default function FindingsFeed({ findings, onResolve }: { findings: Finding[], onResolve: (id: string) => void }) {
  const [selected, setSelected] = useState<Finding | null>(null);

  const activeFindings = findings.filter(f => !f.resolved);

  return (
    <div className="flex space-x-6">
      <div className="flex-1 space-y-4">
        <h3 className="text-xl font-semibold mb-6 flex items-center">
          <ShieldAlert className="mr-2 text-rose-500" /> Active Anomalies ({activeFindings.length})
        </h3>
        <AnimatePresence>
          {activeFindings.map(finding => (
            <motion.div
              key={finding.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              onClick={() => setSelected(finding)}
              className="bg-finCard border border-zinc-800 hover:border-violet-500/50 p-5 rounded-2xl cursor-pointer transition-all group shadow-sm"
            >
              <div className="flex justify-between items-start">
                 <div>
                   <div className="flex items-center space-x-3 mb-2">
                     <span className={`px-2.5 py-1 text-xs font-bold rounded-md ${
                        finding.severity === 'Critical' ? 'bg-rose-500/20 text-rose-400' :
                        finding.severity === 'High' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-emerald-500/20 text-emerald-400'
                     }`}>
                        {finding.severity}
                     </span>
                     <span className="text-zinc-500 text-sm font-medium">{finding.category}</span>
                   </div>
                   <h4 className="text-lg font-medium text-zinc-200 group-hover:text-violet-400 transition-colors">
                     {finding.title}
                   </h4>
                   <p className="text-zinc-400 mt-2 text-sm max-w-2xl">{finding.rootCause}</p>
                 </div>
                 <div className="text-right">
                   <div className="text-xl font-bold text-rose-400">
                     {formatINR(finding.inrImpact)}
                   </div>
                   <div className="text-xs text-zinc-500 mt-1">Impact / Year</div>
                 </div>
              </div>
            </motion.div>
          ))}
          {activeFindings.length === 0 && (
            <motion.div 
               initial={{ opacity: 0 }} animate={{ opacity: 1 }}
               className="text-center p-12 text-zinc-500 bg-finCard border border-zinc-800 border-dashed rounded-3xl"
            >
               <CheckCircle size={48} className="mx-auto mb-4 text-emerald-500/50" />
               <p>No active anomalies pending resolution.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="w-[400px] bg-finCard border border-zinc-800 rounded-2xl p-6 flex flex-col h-fit sticky top-24 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-6">
               <h3 className="font-semibold text-lg text-white">Remediation Plan</h3>
               <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-white transition-colors">
                 <X size={20} />
               </button>
            </div>
            
            <div className="space-y-6">
               <div>
                 <div className="text-sm text-zinc-500 mb-1">Detected Issue</div>
                 <div className="font-medium text-zinc-200 leading-snug">{selected.title}</div>
               </div>
               
               <div className="bg-violet-500/10 border border-violet-500/20 p-4 rounded-xl">
                 <div className="text-sm text-violet-400 mb-2 flex items-center font-medium">
                    <Info size={16} className="mr-1" /> Recommended Action
                 </div>
                 <div className="text-zinc-300 leading-relaxed text-sm">{selected.recommendation}</div>
               </div>

               <div className="grid grid-cols-2 gap-4">
                 <div className="bg-zinc-900/50 p-4 rounded-xl text-center border border-zinc-800">
                    <div className="text-xs text-zinc-500 mb-1">Assigned Owner</div>
                    <div className="font-medium text-emerald-400">Finance Team</div>
                 </div>
                 <div className="bg-zinc-900/50 p-4 rounded-xl text-center border border-zinc-800">
                    <div className="text-xs text-zinc-500 mb-1">Est. Effort</div>
                    <div className="font-medium text-amber-400">4 Hours</div>
                 </div>
               </div>

               <button
                  onClick={() => {
                     onResolve(selected.id);
                     setSelected(null);
                  }}
                  className="w-full mt-4 bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_20px_rgba(16,185,129,0.5)]"
               >
                  Execute Fix & Reclaim {formatINR(selected.inrImpact)}
               </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
