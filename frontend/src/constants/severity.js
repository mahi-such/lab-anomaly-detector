export const SEVERITY_STYLES = {
  // Statistical Severities
  PANIC:    'bg-red-100 text-red-800 border-red-300',
  SEVERE:   'bg-orange-100 text-orange-800 border-orange-300',
  MODERATE: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  MILD:     'bg-blue-100 text-blue-800 border-blue-300',
  
  // Final ML/Hybrid Labels
  CRITICAL: 'bg-red-100 text-red-800 border-red-300',
  ALERT:    'bg-orange-100 text-orange-800 border-orange-300',
  WATCH:    'bg-yellow-100 text-yellow-800 border-yellow-300',
  NORMAL:   'bg-green-100 text-green-800 border-green-300',
  
  UNKNOWN:  'bg-slate-100 text-slate-600 border-slate-300',
}

export const SEVERITY_DEFAULT = 'bg-slate-100 text-slate-400 border-slate-200'

export const getSeverityStyle = (severity) =>
  SEVERITY_STYLES[severity?.toUpperCase()] ?? SEVERITY_DEFAULT