import { useState, useEffect } from 'react';
import { Bell, Plus, X, BookOpen, BarChart2, RefreshCw } from 'lucide-react';

export default function Dashboard() {
  // --- STATE MANAGEMENT ---
  const [activeTab, setActiveTab] = useState('Feed');
  const [isAnalyzerOpen, setIsAnalyzerOpen] = useState(false);
  const [recentResults, setRecentResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    biomarker_code: '',
    result_value_num: '',
    ref_min_parsed: '',
    ref_max_parsed: '',
    test_panel: 'CBC',
  });

  // --- DATA PERSISTENCE ---
  useEffect(() => {
    const saved = localStorage.getItem('recentResults');
    if (saved) setRecentResults(JSON.parse(saved));
  }, []);

  useEffect(() => {
    localStorage.setItem('recentResults', JSON.stringify(recentResults));
  }, [recentResults]);

  // --- DERIVED DATA ---
  const stats = [
    { label: 'Critical', count: recentResults.filter((r) => r.status === 'CRITICAL').length },
    { label: 'Alert', count: recentResults.filter((r) => r.status === 'ALERT').length },
    { label: 'Watch', count: recentResults.filter((r) => r.status === 'WATCH').length },
    { label: 'Normal', count: recentResults.filter((r) => r.status === 'NORMAL').length },
  ];

  // --- HANDLERS ---
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: ['biomarker_code', 'test_panel'].includes(name) ? value.toUpperCase() : value,
    }));
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setLoading(true);
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
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis failed.');

      const result = data.data;
      const colorMap = { CRITICAL: 'red', ALERT: 'orange', WATCH: 'blue', NORMAL: 'green' };

      const newFeedItem = {
        ...result,
        id: crypto.randomUUID(),
        biomarker: formData.biomarker_code,
        panel: formData.test_panel,
        status: result.final_label,
        zScore: result.z_score != null ? result.z_score.toFixed(2) : 'N/A',
        value: formData.result_value_num,
        unit: 'units',
        color: colorMap[result.final_label] || 'blue',
      };

      setRecentResults((prev) => [newFeedItem, ...prev]);
      setIsAnalyzerOpen(false);
      setFormData({ biomarker_code: '', result_value_num: '', ref_min_parsed: '', ref_max_parsed: '', test_panel: 'CBC' });
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
      {/* SIDEBAR NAVIGATION */}
      <aside className="w-64 bg-blue-950 border-r border-blue-900 flex flex-col justify-between text-blue-100 shrink-0">
        <div className="p-6">
          <h1 className="text-xl font-black text-white mb-8">RelyTech LIS</h1>
          <nav className="space-y-2">
            <button onClick={() => setActiveTab('Feed')} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-bold ${activeTab === 'Feed' ? 'bg-blue-900 text-yellow-400' : 'text-blue-400'}`}>
              <Bell size={18} /> Alert Feed
            </button>
          </nav>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-6xl mx-auto">
          
          {/* HEADER SECTION: TITLED AS ANOMALY DETECTION */}
          <div className="flex justify-between items-end mb-8">
            <div>
              <h2 className="text-4xl font-black text-blue-950 tracking-tight">Anomaly Detection Feed</h2>
              <p className="text-blue-400 text-xs font-bold uppercase mt-1">AI-Powered Lab Analysis</p>
            </div>
            <button onClick={() => setIsAnalyzerOpen(true)} className="bg-yellow-400 hover:bg-yellow-300 text-blue-950 px-5 py-3 rounded-xl text-sm font-black shadow-lg">
              <Plus size={18} className="inline mr-2" /> New Anomaly Analysis
            </button>
          </div>

          {/* STATISTICS GRID */}
          <div className="grid grid-cols-4 gap-5 mb-10">
            {stats.map((stat) => (
              <div key={stat.label} className="bg-white border border-blue-100 p-5 rounded-2xl shadow-xl">
                <p className="text-[10px] font-black text-blue-900/60 uppercase">{stat.label} Records</p>
                <p className="text-4xl font-black text-blue-950 mt-2">{stat.count}</p>
              </div>
            ))}
          </div>

          {/* RESULTS FEED LIST */}
          <div className="space-y-4">
            {recentResults.map((result) => {
              const styles = getColorClasses(result.color);
              return (
                <div key={result.id} className={`bg-white border ${styles.border} border-l-4 rounded-xl p-5 shadow flex items-center justify-between`}>
                  <div className="w-1/4">
                    <p className="text-[10px] font-black text-blue-400 uppercase">Classification</p>
                    <span className={`px-2 py-1 text-[10px] font-black uppercase rounded ${styles.badge}`}>{result.status}</span>
                  </div>
                  <div className="w-1/4">
                    <p className="text-[10px] font-black text-blue-400 uppercase">Biomarker</p>
                    <p className="font-black">{result.biomarker}</p>
                    <p className="text-[10px] text-blue-500 uppercase">{result.panel}</p>
                  </div>
                  <div className="w-1/4 text-center">
                    <p className="text-[10px] font-black text-blue-400 uppercase">Statistical Z-Score</p>
                    <p className="font-bold font-mono">{result.zScore}</p>
                  </div>
                  <div className="w-1/4 text-right">
                    <p className="text-[10px] font-black text-blue-400 uppercase">Measured Result</p>
                    <p className="text-xl font-black">{result.value} <span className="text-xs font-normal">{result.unit}</span></p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      {/* ANALYSIS MODAL (OVERLAY) */}
      {isAnalyzerOpen && (
        <div className="fixed inset-0 bg-blue-950/40 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full p-8 shadow-2xl">
            <button onClick={() => setIsAnalyzerOpen(false)} className="mb-6 text-blue-950"><X /></button>
            <h3 className="text-2xl font-black mb-6">New Laboratory Analysis</h3>
            <form onSubmit={handleAnalyze} className="space-y-5">
              <div className="space-y-1">
                <label className="text-[10px] font-black uppercase text-blue-900/60">Biomarker Identification Code</label>
                <input type="text" name="biomarker_code" placeholder="e.g. HB, ALT, GLUCOSE" value={formData.biomarker_code} onChange={handleInputChange} className="w-full p-3 border rounded-lg" required />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-black uppercase text-blue-900/60">Numeric Result Value</label>
                <input type="number" step="0.01" name="result_value_num" placeholder="0.00" value={formData.result_value_num} onChange={handleInputChange} className="w-full p-3 border rounded-lg" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-black uppercase text-blue-900/60">Reference Min</label>
                  <input type="number" step="0.01" name="ref_min_parsed" placeholder="Min" value={formData.ref_min_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-black uppercase text-blue-900/60">Reference Max</label>
                  <input type="number" step="0.01" name="ref_max_parsed" placeholder="Max" value={formData.ref_max_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" />
                </div>
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