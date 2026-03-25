import { motion } from 'framer-motion';
import { Server } from 'lucide-react';

export default function DemoLoader() {
  return (
    <div className="flex flex-col items-center justify-center p-20 text-zinc-500 bg-finCard border border-zinc-800 border-dashed rounded-3xl mt-8">
      <motion.div animate={{ rotate: 360, opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} className="w-24 h-24 rounded-full bg-violet-900/20 flex flex-col items-center justify-center mb-6 ring-2 ring-violet-500/50">
        <Server size={40} className="text-violet-400" />
      </motion.div>
      <h3 className="text-2xl font-bold text-white mb-3">Syncing Enterprise Telemetry...</h3>
      <p className="text-sm max-w-sm text-center mb-8 text-zinc-400">
        Ingesting financial ledgers, cloud utilization arrays, and procurement vendor profiles into the context engine.
      </p>
      <div className="flex space-x-2">
         <motion.div animate={{ height: [10, 24, 10] }} transition={{ repeat: Infinity, duration: 1, delay: 0 }} className="w-2 bg-violet-500 rounded-full" />
         <motion.div animate={{ height: [10, 32, 10] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-2 bg-cyan-500 rounded-full" />
         <motion.div animate={{ height: [10, 16, 10] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-2 bg-emerald-500 rounded-full" />
      </div>
    </div>
  );
}
