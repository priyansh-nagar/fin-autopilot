import React from 'react';
import { CloudRain, ShoppingCart, TrendingDown, LayoutDashboard, MessageSquare } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  setIsChatOpen: (v: boolean) => void;
  loadDemo: () => void;
  isDemoLoading: boolean;
  isUploading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement>;
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function Sidebar({
  activeTab, setActiveTab, setIsChatOpen, loadDemo, isDemoLoading, isUploading, fileInputRef, handleFileUpload
}: SidebarProps) {
  return (
    <aside className="w-64 border-r border-zinc-800 p-6 flex flex-col h-screen fixed bg-finSide z-10 transition-colors shadow-2xl">
      <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-fuchsia-400 mb-12 select-none">
        Fin-Autopilot
      </h1>
      <nav className="flex-1 space-y-2">
        <button onClick={() => setActiveTab('overview')} 
           className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${activeTab === 'overview' ? 'text-white bg-violet-600/10 shadow-[inset_2px_0_0_#8b5cf6]' : 'text-zinc-400 hover:text-white hover:bg-white/5'}`}>
          <LayoutDashboard size={20} className={activeTab === 'overview' ? 'text-violet-400' : ''} />
          <span className="font-medium">Overview</span>
        </button>
        <button onClick={() => setActiveTab('cloud')}
           className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${activeTab === 'cloud' ? 'text-white bg-cyan-600/10 shadow-[inset_2px_0_0_#06b6d4]' : 'text-zinc-400 hover:text-white hover:bg-white/5 group'}`}>
          <CloudRain size={20} className={activeTab === 'cloud' ? 'text-cyan-400' : 'group-hover:text-cyan-400 transition-colors'} />
          <span className="font-medium">Cloud Spend</span>
        </button>
        <button onClick={() => setActiveTab('procurement')}
           className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${activeTab === 'procurement' ? 'text-white bg-emerald-600/10 shadow-[inset_2px_0_0_#10b981]' : 'text-zinc-400 hover:text-white hover:bg-white/5 group'}`}>
          <ShoppingCart size={20} className={activeTab === 'procurement' ? 'text-emerald-500' : 'group-hover:text-emerald-400 transition-colors'} />
          <span className="font-medium">Procurement</span>
        </button>
        <button onClick={() => setActiveTab('budgets')}
           className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl cursor-pointer transition-all ${activeTab === 'budgets' ? 'text-white bg-rose-600/10 shadow-[inset_2px_0_0_#f43f5e]' : 'text-zinc-400 hover:text-white hover:bg-white/5 group'}`}>
          <TrendingDown size={20} className={activeTab === 'budgets' ? 'text-rose-500' : 'group-hover:text-rose-400 transition-colors'} />
          <span className="font-medium">Budgets</span>
        </button>
      </nav>
      
      <div className="mt-auto space-y-4">
        <button 
          className="w-full bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 text-zinc-300 py-3 rounded-xl font-medium transition-all group flex items-center justify-center space-x-2"
          onClick={() => setIsChatOpen(true)}
        >
          <MessageSquare size={18} className="group-hover:text-violet-400 transition-colors" />
          <span>Ask FinBot AI</span>
        </button>
        
        <div className="flex space-x-2">
          <button 
            className="flex-1 bg-violet-600 hover:bg-violet-500 text-white py-3 rounded-xl font-medium transition-all shadow-[0_0_20px_rgba(139,92,246,0.2)] hover:shadow-[0_0_25px_rgba(139,92,246,0.4)] flex items-center justify-center space-x-1 text-sm relative overflow-hidden disabled:opacity-50"
            onClick={loadDemo}
            disabled={isDemoLoading || isUploading}
          >
            <span className="relative z-10">{isDemoLoading ? 'Loading...' : 'Load Demo'}</span>
          </button>
          <button 
            className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-3 rounded-xl font-medium transition-all flex items-center justify-center space-x-1 text-sm border border-zinc-700 hover:border-violet-500/50 disabled:opacity-50"
            onClick={() => fileInputRef.current?.click()}
            disabled={isDemoLoading || isUploading}
          >
            <span>{isUploading ? 'Uploading...' : 'Upload Data'}</span>
          </button>
          <input type="file" ref={fileInputRef} className="hidden" accept=".csv,.xlsx,.xls,.pdf,.doc,.docx" onChange={handleFileUpload} />
        </div>
      </div>
    </aside>
  );
}
