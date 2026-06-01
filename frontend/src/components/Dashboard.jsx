import { useState, useEffect } from 'react';
import { Bell, Plus, X } from 'lucide-react';

export default function Dashboard() {
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

  useEffect(() => {
    const saved = localStorage.getItem('recentResults');
    if (saved) {
      try { setRecentResults(JSON.parse(saved)); } 
      catch (e) { console.error('Load failed', e); }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('recentResults', JSON.stringify(recentResults));
  }, [recentResults]);

  const stats = [
    { label: 'Critical', count: recentResults.filter((r) => r.status === 'CRITICAL').length },
    { label: 'Alert', count: recentResults.filter((r) => r.status === 'ALERT').length },
    { label: 'Watch', count: recentResults.filter((r) => r.status === 'WATCH').length },
    { label: 'Normal', count: recentResults.filter((r) => r.status === 'NORMAL').length },
  ];

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

    // Build clean payload: Omit optional fields if they are empty
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
      red: { border: 'border-l-red-500 border-blue-50', badge: 'bg-red-100 text-red-800 border-red-200' },
      orange: { border: 'border-l-orange-500 border-blue-50', badge: 'bg-orange-100 text-orange-800 border-orange-200' },
      blue: { border: 'border-l-blue-500 border-blue-50', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
      green: { border: 'border-l-green-500 border-blue-50', badge: 'bg-green-100 text-green-800 border-green-200' },
    };
    return map[color] || map.blue;
  };

  return (
    <div className="flex h-screen bg-[#F4F7FB] text-blue-950 font-sans overflow-hidden">
      <aside className="w-64 bg-blue-950 border-r border-blue-900 flex flex-col justify-between text-blue-100 shadow-xl shrink-0">
        <div className="p-6 border-b border-blue-900/50">
          <h1 className="text-xl font-black text-white flex items-center gap-3">
            <span className="w-3 h-3 rounded-full bg-yellow-400"></span> RelyTech LIS
          </h1>
        </div>
        <div className="p-4">
          <div className="flex items-center gap-3 px-3 py-3 bg-blue-900/50 text-yellow-400 border-l-4 border-yellow-400 rounded-r-lg font-bold">
            <Bell size={18} /> <span className="text-sm">Alert Feed</span>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-6xl mx-auto">
          <div className="flex justify-between items-end mb-8">
            <h2 className="text-4xl font-black text-blue-950 tracking-tight">Alert Feed</h2>
            <button onClick={() => setIsAnalyzerOpen(true)} className="bg-yellow-400 hover:bg-yellow-300 text-blue-950 px-5 py-2.5 rounded-xl text-sm font-black shadow-lg">
              <Plus size={18} className="inline mr-2" /> New Analysis
            </button>
          </div>

          <div className="grid grid-cols-4 gap-5 mb-10">
            {stats.map((stat) => (
              <div key={stat.label} className="bg-white border border-blue-100 p-5 rounded-2xl shadow-xl">
                <span className="text-xs font-black text-blue-900/60 uppercase">{stat.label}</span>
                <p className="text-4xl font-black text-blue-950 mt-2">{stat.count}</p>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            {recentResults.map((result) => {
              const styles = getColorClasses(result.color);
              return (
                <div key={result.id} className={`bg-white border ${styles.border} border-l-4 rounded-xl p-5 shadow-lg flex items-center justify-between`}>
                  <div className="flex items-center gap-6 w-1/3">
                    <span className={`px-2.5 py-1 text-[11px] font-black uppercase rounded-md border ${styles.badge}`}>{result.status}</span>
                    <div>
                      <p className="text-sm font-black text-blue-950">{result.biomarker}</p>
                      <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">{result.panel}</p>
                    </div>
                  </div>
                  <div className="w-1/3 text-center">
                    <p className="text-[10px] font-bold text-blue-900/40 uppercase tracking-widest">Z-Score</p>
                    <p className="text-sm font-bold text-blue-900/80">{result.zScore}</p>
                  </div>
                  <div className="w-1/3 text-right">
                    <p className="text-2xl font-black text-blue-950">{result.value}</p>
                    <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest">{result.unit}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      {isAnalyzerOpen && (
        <div className="absolute inset-0 bg-blue-950/40 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full p-6 shadow-2xl">
            <button onClick={() => setIsAnalyzerOpen(false)} className="mb-4 text-blue-950"><X /></button>
            <h3 className="text-lg font-black mb-4">New Analysis</h3>
            {error && <div className="bg-red-50 p-3 mb-4 rounded-lg"><p className="text-red-600 text-xs font-bold">{error}</p></div>}
            <form onSubmit={handleAnalyze} className="space-y-4">
              <input type="text" name="biomarker_code" placeholder="Code (e.g. HB)" value={formData.biomarker_code} onChange={handleInputChange} className="w-full p-3 border rounded-lg" required />
              <input type="number" step="0.01" name="result_value_num" placeholder="Result Value" value={formData.result_value_num} onChange={handleInputChange} className="w-full p-3 border rounded-lg" required />
              <input type="number" step="0.01" name="ref_min_parsed" placeholder="Ref Min (Optional)" value={formData.ref_min_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" />
              <input type="number" step="0.01" name="ref_max_parsed" placeholder="Ref Max (Optional)" value={formData.ref_max_parsed} onChange={handleInputChange} className="w-full p-3 border rounded-lg" />
              <button type="submit" disabled={loading} className="w-full bg-yellow-400 py-3 rounded-xl font-black hover:bg-yellow-300">
                {loading ? 'Analyzing...' : 'Analyze'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}