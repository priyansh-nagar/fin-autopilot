import { Finding } from '../store/useStore';

export const vendorDetector = (rows: any[]): Finding[] => {
  if (!rows || rows.length === 0) return [];
  const findings: Finding[] = [];
  
  // Find variants with same PAN/GSTIN or similar names
  const panMap = new Map<string, any[]>();
  
  rows.forEach(r => {
    const pan = r.pan || r.PAN || r.GSTIN || r.gstin;
    if (pan) {
      if (!panMap.has(pan)) panMap.set(pan, []);
      panMap.get(pan)!.push(r);
    }
  });

  panMap.forEach((vendorRows, pan) => {
    const names = Array.from(new Set(vendorRows.map(r => r.vendor_name || r.Vendor || r.name)));
    if (names.length > 1) {
      const impact = vendorRows.reduce((acc, r) => acc + (parseFloat(r.amount || r.Amount || r.cost || 0)), 0);
      findings.push({
        id: crypto.randomUUID(),
        category: 'Vendor',
        severity: 'High',
        title: `Duplicate Vendor Profiles (${names.join(', ')})`,
        inrImpact: impact * 0.05, // estimate 5% leakage
        rootCause: `Multiple vendor profiles sharing the same tax ID (${pan}).`,
        recommendation: `Consolidate profiles into master record.`,
        sourceRows: vendorRows,
        resolved: false
      });
    }
  });

  return findings;
};

export const cloudDetector = (rows: any[]): Finding[] => {
  if (!rows || rows.length === 0) return [];
  const findings: Finding[] = [];
  
  // Find spikes > 2.5x rolling avg
  const serviceMap = new Map<string, any[]>();
  rows.forEach(r => {
    const service = r.service || r.Service || r['AWS Service'];
    if (service) {
      if (!serviceMap.has(service)) serviceMap.set(service, []);
      serviceMap.get(service)!.push(r);
    }
  });

  serviceMap.forEach((servRows, service) => {
    const costs = servRows.map(r => parseFloat(r.cost || r.Cost || r.amount || 0));
    if (costs.length > 2) {
      const avg = costs.slice(0, -1).reduce((a, b) => a + b, 0) / (costs.length - 1);
      const latest = costs[costs.length - 1];
      if (avg > 0 && latest > avg * 2.5) {
        findings.push({
          id: crypto.randomUUID(),
          category: 'Cloud',
          severity: 'Critical',
          title: `Compute Spike in ${service}`,
          inrImpact: latest - avg,
          rootCause: `Latest period spend (₹${latest}) exceeded historical rolling average by >2.5x.`,
          recommendation: `Investigate unattached volumes or idle compute instances.`,
          sourceRows: servRows,
          resolved: false
        });
      }
    }
  });
  
  // Find explicitly idle resources if marked
  const idleRows = rows.filter(r => (r.status || '').toLowerCase().includes('idle') || parseInt(r.days_idle || 0) > 15);
  if (idleRows.length > 0) {
    const impact = idleRows.reduce((a, b) => a + parseFloat(b.cost || b.Cost || 0), 0);
    findings.push({
      id: crypto.randomUUID(),
      category: 'Cloud',
      severity: 'Medium',
      title: `${idleRows.length} Idle Resources Detected`,
      inrImpact: impact,
      rootCause: `Resources left running without utilization.`,
      recommendation: `Terminate resources immediately.`,
      sourceRows: idleRows,
      resolved: false
    });
  }

  return findings;
};

export const procurementDetector = (rows: any[]): Finding[] => {
  if (!rows || rows.length === 0) return [];
  const findings: Finding[] = [];
  
  // Items > 15% above benchmark
  const flagged = rows.filter(r => {
    const price = parseFloat(r.unit_price || r['Unit Price'] || r.price || 0);
    const bench = parseFloat(r.benchmark || r.Benchmark || 0);
    return bench > 0 && price > bench * 1.15;
  });

  if (flagged.length > 0) {
    const totalImpact = flagged.reduce((acc, r) => {
      const q = parseFloat(r.qty || r.Qty || 1);
      const p = parseFloat(r.unit_price || r['Unit Price'] || 0);
      const b = parseFloat(r.benchmark || r.Benchmark || 0);
      return acc + ((p - b) * q);
    }, 0);

    findings.push({
      id: crypto.randomUUID(),
      category: 'Procurement',
      severity: 'High',
      title: `Overpriced POs vs Benchmark`,
      inrImpact: totalImpact,
      rootCause: `Detected ${flagged.length} purchase orders priced >15% above market benchmark.`,
      recommendation: `Renegotiate items triggering variance before upcoming renewal cycle.`,
      sourceRows: flagged,
      resolved: false
    });
  }
  return findings;
};

export const budgetDetector = (rows: any[]): Finding[] => {
  if (!rows || rows.length === 0) return [];
  const findings: Finding[] = [];
  
  // depts > 10% over budget
  rows.forEach(r => {
    const dept = r.department || r.Department || r.dept;
    const actual = parseFloat(r.actual || r.Actual || r.spend || 0);
    const budget = parseFloat(r.budget || r.Budget || 0);
    
    if (budget > 0 && actual > budget * 1.10) {
      findings.push({
        id: crypto.randomUUID(),
        category: 'Budget',
        severity: actual > budget * 1.30 ? 'Critical' : 'High',
        title: `${dept} Budget Bleed`,
        inrImpact: actual - budget,
        rootCause: `${dept} actuals (₹${actual}) exceeded allocated budget (₹${budget}) by >10%.`,
        recommendation: `Instigate hiring freeze and audit Q3 OPEX.`,
        sourceRows: [r],
        resolved: false
      });
    }
  });
  return findings;
};

export const runAllDetectors = (data: { vendorRows: any[], cloudRows: any[], procRows: any[], budgetRows: any[] }): Finding[] => {
  const f1 = vendorDetector(data.vendorRows);
  const f2 = cloudDetector(data.cloudRows);
  const f3 = procurementDetector(data.procRows);
  const f4 = budgetDetector(data.budgetRows);
  return [...f1, ...f2, ...f3, ...f4];
};
