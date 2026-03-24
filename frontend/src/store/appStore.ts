import { create } from 'zustand';

export type Finding = {
  id: string;
  category: 'vendor' | 'cloud' | 'procurement' | 'budget' | string;
  severity: 'critical' | 'high' | 'medium' | 'low' | string;
  title: string;
  inrImpact: number;
  rootCause: string;
  recommendation: string;
  effort?: string;
  sourceRows: number[];
  detectorId?: string;
  resolved?: boolean;
};

export type ParseResult = {
  success: boolean;
  fileName: string;
  totalRows: number;
  rowCounts: Record<string, number>;
  data: {
    vendor: any[];
    cloud: any[];
    procurement: any[];
    budget: any[];
    unclassified: any[];
  };
  rawText: string;
};

interface AppState {
  parseResult: ParseResult | null;
  findings: Finding[];
  totalWaste: number;
  itemsScanned: number;
  isLoading: boolean;
  loadingMessage: string;
  setParsed: (data: ParseResult) => void;
  setFindings: (f: Finding[]) => void;
  setLoading: (isLoading: boolean, message?: string) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  parseResult: null,
  findings: [],
  totalWaste: 0,
  itemsScanned: 0,
  isLoading: false,
  loadingMessage: '',
  setParsed: (data) =>
    set({
      parseResult: data,
      itemsScanned: data.totalRows || 0,
    }),
  setFindings: (f) =>
    set({
      findings: f,
      totalWaste: f.reduce((sum, item) => sum + (Number(item.inrImpact) || 0), 0),
    }),
  setLoading: (isLoading, message = '') =>
    set({
      isLoading,
      loadingMessage: message,
    }),
  reset: () =>
    set({
      parseResult: null,
      findings: [],
      totalWaste: 0,
      itemsScanned: 0,
      isLoading: false,
      loadingMessage: '',
    }),
}));
