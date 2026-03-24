import React from 'react';
import SavingsCard from '../components/SavingsCard';
import FindingsFeed from '../components/FindingsFeed';
import { useStore } from '../store/useStore';
import { generatePDFReport } from '../utils/pdfGenerator';

export default function Overview() {
  const { findings } = useStore();
  const activeFindings = findings.filter(f => !f.resolved);
  const resolvedFindings = findings.filter(f => f.resolved);
  
  const totalWaste = activeFindings.reduce((acc, f) => acc + f.inrImpact, 0);
  const savingsRecovered = resolvedFindings.reduce((acc, f) => acc + f.inrImpact, 0);

  const categoryBreakdown = activeFindings.reduce((acc: any, f) => {
    acc[f.category] = (acc[f.category] || 0) + f.inrImpact;
    return acc;
  }, {});

  const handleExportPDF = () => {
    generatePDFReport();
  };

  return (
    <div className="space-y-8">
      <SavingsCard 
        totalRecovered={savingsRecovered} 
        categoryBreakdown={categoryBreakdown}
        onExportPDF={handleExportPDF}
      />
      <FindingsFeed 
        findings={findings} 
        onResolve={(id) => useStore.getState().resolveFinding(id)} 
      />
    </div>
  );
}
