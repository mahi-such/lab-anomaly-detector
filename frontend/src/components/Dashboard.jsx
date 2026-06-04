import { useState, useEffect } from 'react';
import { Bell, Plus, X, BookOpen, BarChart2, RefreshCw, Info } from 'lucide-react';

export default function Dashboard() {
  // --- STATE MANAGEMENT ---
  const [activeTab, setActiveTab] = useState('Feed');
  const [isAnalyzerOpen, setIsAnalyzerOpen] = useState(false);
  const [recentResults, setRecentResults] = useState([]);
  const [baselines, setBaselines] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    biomarker_code: '',
    result_value_num: '',
    ref_min_parsed: '',
    ref_max_parsed: '',
    test_panel: '',
    unit: '', // Track unit for form rendering
  });

  // --- DATA FETCHING ---
  useEffect(() => {
    fetch('/baselines')
      .then((res) => res.json())
      .then((data) => setBaselines(data))
      .catch((err) => console.error('Failed to load baselines', err));
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem('recentResults');
    if (saved) setRecentResults(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem('recentResults', JSON.stringify(recentResults));
  }, [recentResults]);

  // --- DERIVED STATISTICS ---
  const stats = [
    { label: 'Critical', count: recentResults.filter((r) => r.status === 'CRITICAL').length },
    { label: 'Alert', count: recentResults.filter((r) => r.status === 'ALERT').length },
    { label: 'Watch', count: recentResults.filter((r) => r.status === 'WATCH').length },
    { label: 'Normal', count: recentResults.filter((r) => r.status === 'NORMAL').length },
  ];

  // --- HANDLERS ---
  const handleInputChange = (e) => {
    const { name, value } = e.target;

    if (name === 'biomarker_code') {
      const baseline = baselines[value] || {};
      const valueUpper = value.toUpperCase();
      
      // Trust the backend metadata panel explicitly; default to 'UNKNOWN' token
      const autoPanel = baseline.panel || 'UNKNOWN';
      const autoUnit = baseline.unit || baseline.units || 'units';

      setFormData((prev) => ({
        ...prev,
        biomarker_code: valueUpper,
        ref_min_parsed: baseline.ref_min_typical ?? '',
        ref_max_parsed: baseline.ref_max_typical ?? '',
        test_panel: autoPanel, 
        unit: autoUnit, 
      }));
      return;
    }

    setFormData((prev) => ({
      ...prev,
      [name]: name === 'test_panel' ? value.toUpperCase() : value,
    }));
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true); // FIXED: Changed from loading(true) to avoid script crashes
    setError(null);

    const payload = {
      biomarker_code: formData.biomarker_code,
      result_value_num: parseFloat(formData.result_value_num),
      test_panel: formData.test_panel,
      ...(formData.ref_min_parsed && { ref_min_parsed: parseFloat(formData.ref_min_parsed) }),
      ...(formData.ref_max_parsed && { ref_max_parsed: parseFloat(formData.ref_max_parsed) }),
    };

    try {
      const response = await fetch('/analyze', {
        method: 'POST', // FIXED: Removed stray 'photo' key mapping parameter
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed.');

      const result = data.data || data; 
      const colorMap = { CRITICAL: 'red', ALERT: 'orange', WATCH: 'blue', NORMAL: 'green' };

      const newFeedItem = {
        ...result,
        id: crypto.randomUUID(),
        biomarker: formData.biomarker_code,
        panel: formData.test_panel,
        status: result.final_label,
        zScore: result.z_score != null ? result.z_score.toFixed(2) : 'N/A',
        value: formData.result_value_num,
        unit: formData.unit || 'units', 
        color: colorMap[result.final_label] || 'blue',
        message: result.alert_message || `AI Prediction: ${result.ml_prediction} (Reason: ${result.decision_reason})`,
      };

      setRecentResults((prev) => [newFeedItem, ...prev]);
      setIsAnalyzerOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getColorClasses = (color) => {
    const map = {
      red: { border: 'border-l-red-500', badge: 'bg-red-100 text-red-800' },
      orange: { border: 'border-l-orange-500', badge: 'bg-orange-100 text-orange-800' },
      blue: { border: 'border-l-blue-500', badge: 'bg-blue-100 text-blue-800' },
      green: { border: 'border-l-green-500', badge: 'bg-green-100 text-green-800' },
    };
    return map[color] || map.blue;
  };

  return (
    <div className="flex h-screen bg-[#F4F7FB] text-blue-950 font-sans overflow-hidden">
      <aside className="w-64 bg-blue-950 border-r border-blue-900 flex flex-col justify-between text-blue-100 shrink-0">
        <div className="p-6">
          <h1 className="text-xl font-black text-white mb-8">RelyTech LIS</h1>
          <nav className="space-y-2">
            <button onClick={() => setActiveTab('Feed')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold ${activeTab === 'Feed' ? 'bg-blue-900 text-yellow-400' : 'text-blue-400'}`}>
              <Bell size={18} /> Alert Feed
            </button>
            <button onClick={() => setActiveTab('Library')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold ${activeTab === 'Library' ? 'bg-blue-900 text-yellow-400' : 'text-blue-400'}`}>
              <BookOpen size={18} /> Reference Library
            </button>
          </nav>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">
          {activeTab === 'Feed' && (
            <>
              <div className="flex justify-between items-end mb-8">
                <div>
                  <h2 className="text-4xl font-black text-blue-950 tracking-tight">Anomaly Detection Feed</h2>
                  <p className="text-blue-400 text-xs font-bold uppercase mt-1">AI-Powered Diagnostic Engine</p>
                </div>
                <button onClick={() => setIsAnalyzerOpen(true)} className="bg-yellow-400 hover:bg-yellow-300 text-blue-950 px-5 py-3 rounded-xl text-sm font-black shadow-lg">
                  <Plus size={18} className="inline mr-2" /> New Anomaly Analysis
                </button>
              </div>

              <div className="grid grid-cols-4 gap-5 mb-10">
                {stats.map((stat) => (
                  <div key={stat.label} className="bg-white border border-blue-100 p-5 rounded-2xl shadow-xl">
                    <p className="text-[10px] font-black text-blue-900/60 uppercase">{stat.label} Records</p>
                    <p className="text-4xl font-black text-blue-950 mt-2">{stat.count}</p>
                  </div>
                ))}
              </div>

              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl font-medium text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                {recentResults.map((result) => {
                  const styles = getColorClasses(result.color);
                  return (
                    <div key={result.id} className={`bg-white border ${styles.border} border-l-4 rounded-xl p-5 shadow flex flex-col gap-4`}>
                      <div className="flex items-center justify-between">
                        <div className="w-1/4"><p className="text-[10px] font-black text-blue-400 uppercase">Classification</p><span className={`px-2 py-1 text-[10px] font-black uppercase rounded ${styles.badge}`}>{result.status}</span></div>
                        <div className="w-1/4"><p className="text-[10px] font-black text-blue-400 uppercase">Biomarker</p><p className="font-black">{result.biomarker}</p><p className="text-[10px] text-blue-500 uppercase">{result.panel}</p></div>
                        <div className="w-1/4 text-center"><p className="text-[10px] font-black text-blue-400 uppercase">Statistical Z-Score</p><p className="font-bold font-mono">{result.zScore}</p></div>
                        <div className="w-1/4 text-right"><p className="text-[10px] font-black text-blue-400 uppercase">Measured Result</p><p className="text-xl font-black">{result.value} <span className="text-xs font-normal">{result.unit}</span></p></div>
                      </div>

                      <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 flex items-start gap-3 mt-2">
                        <Info size={16} className="text-blue-400 mt-0.5 shrink-0" />
                        <div>
                          <p className="text-[10px] font-black text-blue-900/40 uppercase mb-1">AI Clinical Justification</p>
                          <p className="text-sm font-medium text-blue-950/80 leading-relaxed">
                            {result.message}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {activeTab === 'Library' && (
            <div className="bg-white p-8 rounded-3xl shadow-lg border border-blue-50">
              <h2 className="text-3xl font-black text-blue-950 mb-6">Reference Library</h2>
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] uppercase text-blue-400 font-bold tracking-widest border-b border-blue-50">
                    <th className="pb-4">Biomarker</th>
                    <th className="pb-4">Panel</th>
                    <th className="pb-4">Unit</th>
                    <th className="pb-4">Min Typical</th>
                    <th className="pb-4">Max Typical</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-blue-50">
                  {Object.entries(baselines).map(([k, v]) => {
                    const panelName = v.panel || 'UNKNOWN';
                    const unitName = v.unit || v.units || '—';
                    
                    return (
                      <tr key={k} className="text-sm font-bold text-blue-950 hover:bg-blue-50/50">
                        <td className="py-4">{k}</td>
                        <td className="py-4 text-[11px] font-black text-blue-400 uppercase tracking-wide">{panelName}</td>
                        <td className="py-4 text-xs text-blue-500 font-medium">{unitName}</td>
                        <td className="py-4 font-mono">{v.ref_min_typical ?? '—'}</td>
                        <td className="py-4 font-mono">{v.ref_max_typical ?? '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {isAnalyzerOpen && (
        <div className="fixed inset-0 bg-blue-950/40 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full p-8 shadow-2xl">
            <button onClick={() => setIsAnalyzerOpen(false)} className="mb-6 text-blue-950"><X /></button>
            <h3 className="text-2xl font-black mb-6">New Laboratory Analysis</h3>
            <form onSubmit={handleAnalyze} className="space-y-5">
              
              <div className="space-y-1">
                <label className="text-[10px] font-black uppercase text-blue-900/60">Biomarker Identification Code</label>
                <select name="biomarker_code" value={formData.biomarker_code} onChange={handleInputChange} className="w-full p-3 border rounded-lg bg-white font-bold" required>
                  <option value="">Select a biomarker...</option>
                  {Object.keys(baselines).sort().map((code) => <option key={code} value={code}>{code}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-black uppercase text-blue-900/60">Test Panel</label>
                  <input type="text" name="test_panel" placeholder="e.g. CBC, VIT_D" value={formData.test_panel} onChange={handleInputChange} className="w-full p-3 border rounded-lg uppercase" required />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-black uppercase text-blue-900/60">Reporting Unit</label>
                  <input type="text" name="unit" value={formData.unit} readOnly className="w-full p-3 border rounded-lg bg-slate-50 text-slate-400 font-bold cursor-not-allowed select-none" placeholder="—" />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-black uppercase text-blue-900/60">Numeric Result Value</label>
                <input type="number" step="0.01" name="result_value_num" placeholder="0.00" value={formData.result_value_num} onChange={handleInputChange} className="w-full p-3 border rounded-lg" required />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1"><label className="text-[10px] font-black uppercase text-blue-900/60">Ref Min</label><input type="number" step="0.01" name="ref_min_parsed" placeholder="Min" value={formData.ref_min_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" /></div>
                <div className="space-y-1"><label className="text-[10px] font-black uppercase text-blue-900/60">Ref Max</label><input type="number" step="0.01" name="ref_max_parsed" placeholder="Max" value={formData.ref_max_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" /></div>
              </div>
              
              <button type="submit" disabled={loading} className="w-full bg-yellow-400 py-4 rounded-xl font-black text-blue-950 hover:bg-yellow-300 mt-4">
                {loading ? 'Running Detection...' : 'Run Anomaly Detection'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}