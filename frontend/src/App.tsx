import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Database, LayoutDashboard, CloudRain, ShoppingCart, TrendingDown } from 'lucide-react';
import axios from 'axios';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import Papa from 'papaparse';

import Sidebar from './components/Sidebar';
import DemoLoader from './components/DemoLoader';
import AIChat from './components/AIChat';
import Overview from './pages/Overview';
import CloudSpend from './pages/CloudSpend';
import Procurement from './pages/Procurement';
import Budgets from './pages/Budgets';

import { useStore, Finding } from './store/useStore';
import { runAllDetectors } from './utils/detectors';

type Tab = 'overview' | 'cloud' | 'procurement' | 'budgets';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { vendorRows, cloudRows, procRows, budgetRows, findings, setParsedData, setFindings } = useStore();

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    try {
      let parsed = { vendorRows: [] as any[], cloudRows: [] as any[], procRows: [] as any[], budgetRows: [] as any[], rawText: '', fileName: file.name };
      
      if (file.name.toLowerCase().endsWith('.csv')) {
         const text = await file.text();
         const result = Papa.parse(text, { header: true, skipEmptyLines: true });
         const rows = result.data as any[];
         const headers = result.meta.fields?.map(h => h.toLowerCase()) || [];
         
         if (headers.some(h => ['aws', 'service', 'resource'].includes(h))) parsed.cloudRows = rows;
         else if (headers.some(h => ['po', 'benchmark', 'qty'].includes(h))) parsed.procRows = rows;
         else if (headers.some(h => ['department', 'budget'].includes(h))) parsed.budgetRows = rows;
         else parsed.vendorRows = rows;
      } else {
         const formData = new FormData();
         formData.append('file', file);
         const { data } = await axios.post('http://localhost:8000/api/parse', formData);
         parsed = { ...parsed, ...data };
      }
      
      setParsedData(parsed);
      const generatedFindings = runAllDetectors(parsed);
      setFindings(generatedFindings);
      
      if (generatedFindings.length > 0) {
        if (parsed.cloudRows.length > 0) setActiveTab('cloud');
        else if (parsed.procRows.length > 0) setActiveTab('procurement');
        else if (parsed.budgetRows.length > 0) setActiveTab('budgets');
        else setActiveTab('overview');
      }
    } catch (err: any) {
      console.error(err);
      alert("Upload failed: " + err.message);
    } finally {
      setIsUploading(false);
      if (e.target) e.target.value = '';
    }
  };

  const loadDemo = async () => {
    setIsDemoLoading(true);
    setFindings([]);
    setParsedData({ vendorRows: [], cloudRows: [], procRows: [], budgetRows: [], rawText: '', fileName: 'Demo Data' });
    try {
      const { data } = await axios.get('http://localhost:8000/api/demo');
      setFindings(data);
    } catch(e) {
      console.error(e);
    } finally {
      setIsDemoLoading(false);
    }
  };

  const activeFindings = findings.filter(f => !f.resolved);
  const totalItemsScanned = vendorRows.length + cloudRows.length + procRows.length + budgetRows.length;

  return (
    <div className="min-h-screen bg-finBg text-white flex overflow-hidden">
      <Sidebar 
        activeTab={activeTab} setActiveTab={setActiveTab} setIsChatOpen={setIsChatOpen} 
        loadDemo={loadDemo} isDemoLoading={isDemoLoading} isUploading={isUploading} 
        fileInputRef={fileInputRef} handleFileUpload={handleFileUpload} 
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
                <p className="font-mono text-xl font-medium text-white">{totalItemsScanned > 0 ? totalItemsScanned.toLocaleString('en-IN') : '0'}</p>
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

          {isDemoLoading ? (
            <DemoLoader />
          ) : findings.length === 0 && totalItemsScanned === 0 ? (
            <div className="bg-finCard border border-zinc-800 rounded-2xl p-16 text-center shadow-xl mt-12">
              <Database className="mx-auto text-zinc-600 mb-6" size={64} />
              <h2 className="text-2xl font-bold text-white mb-3">No Target Acquired</h2>
              <p className="text-zinc-400 max-w-md mx-auto mb-8">Deploy datasets instantly via CSV, Excel, or PDF to extract real-time financial intelligence.</p>
              <button className="bg-zinc-800 hover:bg-zinc-700 text-white font-medium px-8 py-3 rounded-xl transition-all border border-zinc-700 hover:border-violet-500/50 shadow-lg shadow-black/20"
                onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
                {isUploading ? 'Parsing intelligence...' : 'Deploy Dataset'}
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

      <AIChat isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
