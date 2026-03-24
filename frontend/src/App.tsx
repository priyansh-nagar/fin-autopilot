import React, { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Database, LayoutDashboard, CloudRain, ShoppingCart, TrendingDown } from 'lucide-react';

import Sidebar from './components/Sidebar';
import DemoLoader from './components/DemoLoader';
import AIChat from './components/AIChat';
import Overview from './pages/Overview';
import CloudSpend from './pages/CloudSpend';
import Procurement from './pages/Procurement';
import Budgets from './pages/Budgets';

import { useStore } from './store/useStore';
import { uploadAndParse, runDetection } from './lib/api';

type Tab = 'overview' | 'cloud' | 'procurement' | 'budgets';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { parseResult, findings, itemsScanned, isLoading, loadingMessage, setParsed, setFindings, setLoading, reset } = useStore();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true, 'Parsing your file...');
      const parsed = await uploadAndParse(file);
      setParsed(parsed);

      setLoading(true, 'Running anomaly detection...');
      const detected = await runDetection(parsed.data);
      setFindings(detected.findings || []);

      if (parsed.data.cloud?.length) setActiveTab('cloud');
      else if (parsed.data.procurement?.length) setActiveTab('procurement');
      else if (parsed.data.budget?.length) setActiveTab('budgets');
      else setActiveTab('overview');
    } catch (err: any) {
      console.error(err);
      alert(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false, '');
      if (e.target) e.target.value = '';
    }
  };

  const loadDemo = async () => {
    setIsDemoLoading(true);
    reset();
    setTimeout(() => setIsDemoLoading(false), 1000);
  };

  const activeFindings = findings.filter((f) => !f.resolved);

  return (
    <div className="min-h-screen bg-finBg text-white flex overflow-hidden">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        setIsChatOpen={setIsChatOpen}
        loadDemo={loadDemo}
        isDemoLoading={isDemoLoading}
        isUploading={isLoading}
        fileInputRef={fileInputRef}
        handleFileUpload={handleFileUpload}
      />

      <main className="flex-1 ml-64 p-10 h-screen overflow-y-auto w-full relative">
        <div className="max-w-7xl mx-auto space-y-8">
          <header className="flex justify-between items-center bg-finCard border border-zinc-800 p-6 rounded-2xl shadow-xl">
            <div>
              <h1 className="text-3xl font-bold text-white tracking-tight">Fin-Autopilot</h1>
              <p className="text-zinc-400 mt-1">Enterprise Cost Intelligence & Auto-Remediation</p>
            </div>
            <div className="flex space-x-6 text-sm">
              <div className="text-center px-4 border-r border-zinc-800">
                <p className="text-zinc-500 mb-0.5">Items Scanned</p>
                <p className="font-mono text-xl font-medium text-white">{itemsScanned.toLocaleString('en-IN')}</p>
              </div>
              <div className="text-center px-4 border-r border-zinc-800">
                <p className="text-zinc-500 mb-0.5">Active Anomalies</p>
                <p className="font-mono text-xl font-medium text-amber-500">{activeFindings.length}</p>
              </div>
              <div className="text-center pl-4">
                <p className="text-zinc-500 mb-0.5">Data Quality</p>
                <div className="flex items-center space-x-2 text-emerald-500 mt-1">
                  <ShieldCheck size={18} />
                  <span className="font-medium">99.8%</span>
                </div>
              </div>
            </div>
          </header>

          <header className="mb-2 flex justify-between items-end">
            <div>
              <AnimatePresence mode="wait">
                <motion.div key={activeTab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                  <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                    {activeTab === 'overview' && <><LayoutDashboard className="text-violet-400" /> Cost Intelligence Overview</>}
                    {activeTab === 'cloud' && <><CloudRain className="text-cyan-400" /> Cloud Spend Analysis</>}
                    {activeTab === 'procurement' && <><ShoppingCart className="text-emerald-500" /> Vendor & Procurement Intelligence</>}
                    {activeTab === 'budgets' && <><TrendingDown className="text-rose-500" /> Departmental Budgets</>}
                  </h2>
                </motion.div>
              </AnimatePresence>
            </div>
          </header>

          {isDemoLoading || isLoading ? (
            <DemoLoader />
          ) : findings.length === 0 && itemsScanned === 0 ? (
            <div className="bg-finCard border border-zinc-800 rounded-2xl p-16 text-center shadow-xl mt-12">
              <Database className="mx-auto text-zinc-600 mb-6" size={64} />
              <h2 className="text-2xl font-bold text-white mb-3">No Target Acquired</h2>
              <p className="text-zinc-400 max-w-md mx-auto mb-8">Deploy datasets instantly via CSV or PDF to extract real-time financial intelligence.</p>
              <button className="bg-zinc-800 hover:bg-zinc-700 text-white font-medium px-8 py-3 rounded-xl transition-all border border-zinc-700 hover:border-violet-500/50 shadow-lg shadow-black/20"
                onClick={() => fileInputRef.current?.click()} disabled={isLoading}>
                {isLoading ? loadingMessage || 'Processing...' : 'Deploy Dataset'}
              </button>
            </div>
          ) : (
            <div className="mt-6">
              {activeTab === 'overview' && <Overview />}
              {activeTab === 'cloud' && <CloudSpend />}
              {activeTab === 'procurement' && <Procurement />}
              {activeTab === 'budgets' && <Budgets />}
            </div>
          )}
        </div>
      </main>

      <AIChat isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} parseResult={parseResult} />
    </div>
  );
}
