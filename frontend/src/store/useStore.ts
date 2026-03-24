import { create } from 'zustand';

export type Finding = {
  id: string;
  category: 'Vendor' | 'Cloud' | 'Procurement' | 'Budget' | string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  title: string;
  inrImpact: number;
  rootCause: string;
  recommendation: string;
  sourceRows: any[];
  resolved: boolean;
};

interface AppState {
  vendorRows: any[];
  cloudRows: any[];
  procRows: any[];
  budgetRows: any[];
  rawText: string;
  fileName: string | null;
  uploadedAt: string | null;
  findings: Finding[];
  
  setParsedData: (data: {
    vendorRows?: any[];
    cloudRows?: any[];
    procRows?: any[];
    budgetRows?: any[];
    rawText?: string;
    fileName: string;
  }) => void;
  
  setFindings: (findings: Finding[]) => void;
  resolveFinding: (id: string) => void;
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  vendorRows: [],
  cloudRows: [],
  procRows: [],
  budgetRows: [],
  rawText: '',
  fileName: null,
  uploadedAt: null,
  findings: [],

  setParsedData: (data) => set((state) => ({
    ...state,
    ...data,
    vendorRows: data.vendorRows || [],
    cloudRows: data.cloudRows || [],
    procRows: data.procRows || [],
    budgetRows: data.budgetRows || [],
    rawText: data.rawText || '',
    fileName: data.fileName,
    uploadedAt: new Date().toISOString(),
  })),

  setFindings: (findings) => set({ findings }),
  
  resolveFinding: (id) => set((state) => ({
    findings: state.findings.map(f => f.id === id ? { ...f, resolved: true } : f)
  })),

  reset: () => set({
    vendorRows: [], cloudRows: [], procRows: [], budgetRows: [], rawText: '', fileName: null, uploadedAt: null, findings: []
  })
}));
