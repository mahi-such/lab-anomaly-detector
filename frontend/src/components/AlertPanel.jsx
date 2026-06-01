import { useState } from 'react';
import { Bell, BarChart2, Users, Sliders, Database, Settings } from 'lucide-react';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('All');

  const stats = [
    { label: 'Critical', count: 3, trend: '↑ 2 since last hour', color: 'text-red-600', dot: 'bg-red-500' },
    { label: 'Alert', count: 7, trend: 'No change', color: 'text-orange-600', dot: 'bg-orange-500' },
    { label: 'Watch', count: 12, trend: '↓ 3 since last hour', color: 'text-blue-600', dot: 'bg-blue-500' },
    { label: 'Normal', count: 24, trend: '95% within range', color: 'text-green-600', dot: 'bg-green-500' }
  ];

  const recentResults = [
    {
      id: 1, biomarker: 'Haemoglobin', panel: 'CBC', status: 'CRITICAL', rule: 'panic threshold exceeded',
      delta: '-5.70', zScore: '-2.84', value: '4.2', unit: 'g/dL', refRange: '12.9 - 17.0', color: 'red'
    },
    {
      id: 2, biomarker: 'Haemoglobin', panel: 'CBC', status: 'ALERT', rule: 'downgraded from CRITICAL',
      delta: '-0.60', zScore: '+0.14', value: '11.4', unit: 'g/dL', refRange: '13.0 - 17.0', color: 'orange'
    },
    {
      id: 3, biomarker: 'Fasting Blood Glucose', panel: 'GLUCOSE', status: 'CRITICAL', rule: 'high ML confidence',
      delta: '+32.00', zScore: '+4.25', value: '132', unit: 'mg/dL', refRange: '70 - 100', color: 'red'
    },
    {
      id: 4, biomarker: 'TSH', panel: 'TFT', status: 'WATCH', rule: 'ml prediction',
      delta: '+2.10', zScore: '+1.82', value: '7.2', unit: 'mIU/L', refRange: '0.4 - 4.5', color: 'blue'
    }
  ];

  const getColorClasses = (color) => {
    const map = {
      red: { border: 'border-l-red-500 border-blue-50', bg: 'bg-red-50', text: 'text-red-700', badge: 'bg-red-100 text-red-800 border-red-200' },
      orange: { border: 'border-l-orange-500 border-blue-50', bg: 'bg-orange-50', text: 'text-orange-800', badge: 'bg-orange-100 text-orange-800 border-orange-200' },
      blue: { border: 'border-l-blue-500 border-blue-50', bg: 'bg-blue-50', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-800 border-blue-200' },
      green: { border: 'border-l-green-500 border-blue-50', bg: 'bg-green-50', text: 'text-green-700', badge: 'bg-green-100 text-green-800 border-green-200' }
    };
    return map[color];
  };

  return (
    <div className="flex h-screen bg-[#F4F7FB] text-blue-950 font-sans overflow-hidden">
      
      {/* Sidebar - Deep Navy */}
      <aside className="w-64 bg-blue-950 border-r border-blue-900 flex flex-col justify-between text-blue-100 shadow-xl z-10">
        <div>
          <div className="p-6 border-b border-blue-900/50">
            <h1 className="text-xl font-black text-white flex items-center gap-3 tracking-tight">
              <span className="w-3 h-3 rounded-full bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.5)]"></span>
              RelyTech LIS
            </h1>
            <p className="text-xs text-blue-300 mt-1.5 font-medium tracking-wide">AI Anomaly Detector - v2.1</p>
          </div>

          <div className="p-4">
            <p className="text-[10px] font-black text-blue-400/70 mb-3 px-3 uppercase tracking-widest">Monitor</p>
            <nav className="space-y-1.5">
              <a href="#" className="flex items-center gap-3 px-3 py-3 bg-blue-900/50 text-yellow-400 border-l-4 border-yellow-400 rounded-r-lg font-bold shadow-inner">
                <Bell size={18} strokeWidth={2.5} />
                <span className="text-sm">Alert Feed</span>
                <span className="ml-auto bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-black shadow-sm">3</span>
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-blue-200 hover:text-white hover:bg-blue-900/30 rounded-lg transition-colors font-medium">
                <BarChart2 size={18} />
                <span className="text-sm">Analytics</span>
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-blue-200 hover:text-white hover:bg-blue-900/30 rounded-lg transition-colors font-medium">
                <Users size={18} />
                <span className="text-sm">Patients</span>
              </a>
            </nav>

            <p className="text-[10px] font-black text-blue-400/70 mt-8 mb-3 px-3 uppercase tracking-widest">Configure</p>
            <nav className="space-y-1.5">
              <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-blue-200 hover:text-white hover:bg-blue-900/30 rounded-lg transition-colors font-medium">
                <Sliders size={18} />
                <span className="text-sm">Thresholds</span>
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-blue-200 hover:text-white hover:bg-blue-900/30 rounded-lg transition-colors font-medium">
                <Database size={18} />
                <span className="text-sm">Baselines</span>
              </a>
              <a href="#" className="flex items-center gap-3 px-4 py-2.5 text-blue-200 hover:text-white hover:bg-blue-900/30 rounded-lg transition-colors font-medium">
                <Settings size={18} />
                <span className="text-sm">Settings</span>
              </a>
            </nav>
          </div>
        </div>

        <div className="p-4 border-t border-blue-900/50 bg-blue-900/20">
          <div className="flex items-center gap-3 px-2">
            <div className="w-10 h-10 rounded-full bg-yellow-400 flex items-center justify-center text-sm font-black text-blue-950 shadow-md">MP</div>
            <div>
              <p className="text-sm font-bold text-white">Dr. M. Patel</p>
              <p className="text-xs text-blue-300 font-medium">Pathologist</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content - Soft Blue Background */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8 max-w-6xl mx-auto">
          
          {/* Header Row */}
          <div className="flex justify-between items-end mb-8">
            <div>
              <h2 className="text-4xl font-black text-blue-950 tracking-tight">Alert Feed</h2>
              <p className="text-sm font-bold text-blue-900/50 mt-1 uppercase tracking-wider">Today · 14 Jun 2026 · Tenant 1</p>
            </div>
            <button className="flex items-center gap-2 bg-yellow-400 hover:bg-yellow-300 text-blue-950 px-5 py-2.5 rounded-xl text-sm font-black transition-transform active:scale-95 shadow-lg shadow-yellow-400/20">
              <BarChart2 size={18} strokeWidth={2.5} /> Analytics
            </button>
          </div>

          {/* Stats Cards - Crisp White */}
          <div className="grid grid-cols-4 gap-5 mb-10">
            {stats.map((stat, idx) => (
              <div key={idx} className="bg-white border border-blue-100 p-5 rounded-2xl shadow-xl shadow-blue-900/5">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${stat.dot}`}></span>
                  <span className="text-xs font-black text-blue-900/60 uppercase tracking-widest">{stat.label}</span>
                </div>
                <p className="text-4xl font-black text-blue-950 mb-1">{stat.count}</p>
                <p className={`text-xs font-bold ${stat.color}`}>{stat.trend}</p>
              </div>
            ))}
          </div>

          {/* Feed List */}
          <div>
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-sm font-black text-blue-900/60 uppercase tracking-widest">Recent results</h3>
              <div className="flex gap-2 p-1.5 bg-blue-900/5 rounded-xl border border-blue-900/10">
                {['All', 'Critical', 'Alert'].map(tab => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-5 py-2 rounded-lg text-sm font-bold transition-all ${
                      activeTab === tab 
                        ? 'bg-blue-950 text-white shadow-md' 
                        : 'bg-transparent text-blue-900/60 hover:text-blue-950 hover:bg-white/60'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              {recentResults.map((result) => {
                const styles = getColorClasses(result.color);
                return (
                  <div key={result.id} className={`bg-white border ${styles.border} border-l-4 rounded-xl p-5 shadow-lg shadow-blue-900/5 hover:shadow-xl hover:shadow-blue-900/10 transition-shadow flex items-center justify-between`}>
                    
                    <div className="flex items-center gap-6 w-1/3">
                      <span className={`px-2.5 py-1 text-[11px] font-black uppercase tracking-wider rounded-md flex items-center gap-1.5 border ${styles.badge}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                        {result.status}
                      </span>
                      <div>
                        <p className="text-sm font-black text-blue-950">{result.biomarker}</p>
                        <p className="text-xs font-bold text-blue-900/60 mt-0.5">· {result.panel}</p>
                        <p className="text-[10px] font-bold text-blue-400 mt-1.5 uppercase tracking-widest">
                          LAB24/{result.id} · {result.rule}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 w-1/3 justify-center">
                      <span className="px-2.5 py-1 bg-orange-50 border border-orange-200 text-orange-700 text-xs font-bold rounded-lg shadow-sm">
                        Δ {result.delta}
                      </span>
                      <span className="px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold rounded-lg shadow-sm">
                        z {result.zScore}
                      </span>
                    </div>

                    <div className="w-1/3 text-right">
                      <p className="text-2xl font-black text-blue-950">
                        {result.value} <span className="text-sm font-bold text-blue-900/50">{result.unit}</span>
                      </p>
                      <p className="text-xs font-bold text-blue-900/50 mt-1 uppercase tracking-wider">ref {result.refRange}</p>
                    </div>

                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}