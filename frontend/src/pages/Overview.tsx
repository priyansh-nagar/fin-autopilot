import SavingsCard from '../components/SavingsCard';
import FindingsFeed from '../components/FindingsFeed';
import { useStore } from '../store/useStore';
import { generatePDFReport } from '../utils/pdfGenerator';

export default function Overview() {
  const { findings, totalWaste, itemsScanned, resolveFinding } = useStore();

  const categoryBreakdown = findings.reduce((acc: any, f) => {
    acc[f.category] = (acc[f.category] || 0) + f.inrImpact;
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <SavingsCard totalRecovered={0} categoryBreakdown={categoryBreakdown} onExportPDF={generatePDFReport} />
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-finCard border border-zinc-800 p-4 rounded-xl">ITEMS SCANNED: <b>{itemsScanned.toLocaleString('en-IN')}</b></div>
        <div className="bg-finCard border border-zinc-800 p-4 rounded-xl">TOTAL WASTE: <b>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(totalWaste)}</b></div>
        <div className="bg-finCard border border-zinc-800 p-4 rounded-xl">ACTIVE ANOMALIES: <b>{findings.length}</b></div>
      </div>
      <FindingsFeed findings={findings} onResolve={resolveFinding} />
    </div>
  );
}
