import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { useStore } from '../store/useStore';

export const generatePDFReport = () => {
  const store = useStore.getState();
  const { parseResult, findings, itemsScanned } = store;
  const budgetRows = parseResult?.data.budget || [];

  const totalItems = itemsScanned;
  if (totalItems === 0) {
    alert("Upload data first");
    return;
  }

  const doc = new jsPDF();
  const formatINR = (val: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

  // Helper for Headers
  const renderHeader = (title: string, pageNum: number) => {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("CFO Intelligence Report", 14, 20);
    doc.setFontSize(16);
    doc.setTextColor(139, 92, 246);
    doc.text(title, 14, 30);
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 38);
    doc.text(`Page ${pageNum} of 6`, 180, 20);
  };

  const activeFindings = findings.filter(f => !f.resolved);
  const totalWaste = activeFindings.reduce((a, b) => a + b.inrImpact, 0);

  // PAGE 1: Executive Summary
  renderHeader("Executive Summary", 1);
  doc.setFontSize(14);
  doc.text(`Total Waste Identified: ${formatINR(totalWaste)}`, 14, 50);
  doc.text(`Active Anomalies: ${activeFindings.length}`, 14, 60);
  doc.text(`Total Scanned Items: ${totalItems.toLocaleString()}`, 14, 70);

  doc.setFontSize(16);
  doc.text("Top 3 High-Impact Findings", 14, 90);
  const topFindings = [...activeFindings].sort((a,b) => b.inrImpact - a.inrImpact).slice(0,3);
  
  if (topFindings.length > 0) {
    autoTable(doc, {
      startY: 95,
      head: [['Category', 'Issue', 'Waste (INR)', 'Recommendation']],
      body: topFindings.map(f => [f.category, f.title, formatINR(f.inrImpact), f.recommendation]),
      theme: 'grid',
      headStyles: { fillColor: [139, 92, 246] }
    });
  } else {
    doc.setFontSize(12);
    doc.text("No critical anomalies detected in the dataset.", 14, 100);
  }

  // PAGE 2: Vendor Anomalies Table
  doc.addPage();
  renderHeader("Vendor Duplicate Anomalies", 2);
  const vendorFinds = activeFindings.filter(f => f.category === 'vendor');
  if (vendorFinds.length > 0) {
    autoTable(doc, {
      startY: 45,
      head: [['Issue Title', 'Root Cause', 'INR Risk', 'Recommendation']],
      body: vendorFinds.map(f => [f.title, f.rootCause, formatINR(f.inrImpact), f.recommendation]),
      theme: 'grid',
      headStyles: { fillColor: [16, 185, 129] }
    });
  } else {
    doc.text("Zero duplicate vendor occurrences identified.", 14, 50);
  }

  // PAGE 3: Cloud Spend Anomalies
  doc.addPage();
  renderHeader("Cloud Spend & Idle Resources", 3);
  const cloudFinds = activeFindings.filter(f => f.category === 'cloud');
  if (cloudFinds.length > 0) {
    autoTable(doc, {
      startY: 45,
      head: [['Resource Issue', 'Category', 'Waste (INR)', 'Recommendation']],
      body: cloudFinds.map(f => [f.title, f.severity, formatINR(f.inrImpact), f.recommendation]),
      theme: 'grid',
      headStyles: { fillColor: [6, 182, 212] }
    });
  } else {
    doc.text("Cloud infrastructure running at optimal baseline efficiency.", 14, 50);
  }

  // PAGE 4: Procurement Overspend
  doc.addPage();
  renderHeader("Procurement Overspend (vs Benchmark)", 4);
  const procFinds = activeFindings.filter(f => f.category === 'procurement');
  if (procFinds.length > 0) {
     autoTable(doc, {
        startY: 45,
        head: [['Finding', 'Root Cause', 'Excess Spend', 'Recommendation']],
        body: procFinds.map(f => [f.title, f.rootCause, formatINR(f.inrImpact), f.recommendation]),
        theme: 'grid',
        headStyles: { fillColor: [244, 63, 94] }
     });
  } else {
     doc.text("All procurement items fall within acceptable benchmark variances.", 14, 50);
  }

  // PAGE 5: Budget Variance Table
  doc.addPage();
  renderHeader("Departmental Budget View", 5);
  
  if (budgetRows.length > 0) {
     // Consolidate budgets
     const chartDataMap = new Map<string, any>();
     budgetRows.forEach((row: any) => {
       const dept = row.department || row.Department || row.dept || 'Unknown';
       const actual = parseFloat(row.actual || row.Actual || row.spend || 0);
       const budget = parseFloat(row.budget || row.Budget || 0);
       
       if (!chartDataMap.has(dept)) chartDataMap.set(dept, { dept, actual: 0, budget: 0 });
       const entry = chartDataMap.get(dept);
       entry.actual += actual;
       entry.budget += budget;
     });
     
     const deptArray = Array.from(chartDataMap.values()).map(d => {
       const v = d.budget > 0 ? ((d.actual - d.budget) / d.budget) * 100 : 0;
       return [d.dept, formatINR(d.budget), formatINR(d.actual), formatINR(d.actual - d.budget), `${v.toFixed(1)}%`];
     });

     autoTable(doc, {
        startY: 45,
        head: [['Department', 'Allocated Budget', 'Actual Spend', 'Variance (INR)', 'Variance %']],
        body: deptArray,
        theme: 'grid',
        headStyles: { fillColor: [39, 39, 42] }
     });
  } else {
     doc.text("No budgeting data provided in extract.", 14, 50);
  }

  // PAGE 6: Prioritised Action Plan
  doc.addPage();
  renderHeader("Prioritised Action Plan", 6);
  
  const allFindings = [...activeFindings].sort((a,b) => b.inrImpact - a.inrImpact);
  if (allFindings.length > 0) {
    autoTable(doc, {
      startY: 45,
      head: [['Priority', 'Category', 'Action Required', 'Financial Recovery']],
      body: allFindings.map((f, i) => [i+1, f.category, f.recommendation, formatINR(f.inrImpact)]),
      theme: 'grid',
      headStyles: { fillColor: [8, 145, 178] }
    });
  } else {
    doc.text("No actions required. Operations normalized.", 14, 50);
  }

  const dateStr = new Date().toISOString().split('T')[0];
  doc.save(`CFO_Report_[${dateStr}].pdf`);
};
