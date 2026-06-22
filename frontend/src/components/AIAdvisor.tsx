import React, { useState } from 'react';

const AIAdvisor: React.FC = () => {
  const [actionPlan, setActionPlan] = useState<string>('');
  const [status, setStatus] = useState<string>('Awaiting input...');

  const handleExport = async () => {
    try {
      setStatus('Generating system report...');
      const response = await fetch('/api/apps');
      const data = await response.json();
      
      const report = {
        instructions: "You are an AI assistant. Review this list of installed apps on the user's Mac. Identify any that are typically considered bloatware, outdated, or unnecessary. Reply ONLY with a raw JSON array of strings representing the names of the apps to delete. Do not include markdown formatting.",
        installed_apps: data.apps
      };

      const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'smartclean_report.json';
      a.click();
      URL.revokeObjectURL(url);
      
      setStatus('Report exported! Upload it to ChatGPT/Claude.');
    } catch (e: any) {
      setStatus(`Export failed: ${e.message}`);
    }
  };

  const handleExecute = async () => {
    try {
      const itemsToDelete = JSON.parse(actionPlan);
      if (!Array.isArray(itemsToDelete)) {
        throw new Error('Action plan must be a JSON array of strings.');
      }
      
      setStatus(`Executing deletion of ${itemsToDelete.length} items...`);
      // Note: In a real app, we would first scan these apps to get their paths, then delete.
      // For this demo, we simulate the delete call to the backend.
      const response = await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: itemsToDelete })
      });
      
      const result = await response.json();
      if (result.status === 'success') {
        setStatus(`Successfully processed ${result.results.length} items.`);
      } else {
        setStatus(`Execution error: ${result.message}`);
      }
    } catch (e: any) {
      setStatus(`Invalid JSON or execution failed: ${e.message}`);
    }
  };

  return (
    <div style={{ padding: '20px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '12px', backdropFilter: 'blur(10px)', marginTop: '20px' }}>
      <h2>AI Advisor (No-API-Key Mode)</h2>
      <p style={{ opacity: 0.8, marginBottom: '20px' }}>
        Don't know what to clean? Export your system state, ask an external AI like ChatGPT, and paste its action plan here.
      </p>
      
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <button 
          onClick={handleExport}
          style={{ padding: '10px 20px', borderRadius: '8px', background: '#10b981', color: 'white', border: 'none', cursor: 'pointer' }}
        >
          1. Export System Report (.json)
        </button>
      </div>

      <textarea 
        value={actionPlan}
        onChange={(e) => setActionPlan(e.target.value)}
        placeholder='Paste the JSON action plan here (e.g. ["App1", "/path/to/cache"])'
        style={{ width: '100%', height: '100px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', padding: '10px', marginBottom: '10px', fontFamily: 'monospace' }}
      />

      <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
        <button 
          onClick={handleExecute}
          style={{ padding: '10px 20px', borderRadius: '8px', background: '#ef4444', color: 'white', border: 'none', cursor: 'pointer' }}
        >
          2. Execute AI Action Plan
        </button>
        <span style={{ opacity: 0.8 }}>Status: {status}</span>
      </div>
      
      <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', fontSize: '0.9em' }}>
        <strong>CLI Agent Instructions:</strong> If you are using an agent like Antigravity or Cursor, instruct it to:
        <br/> <code>curl http://127.0.0.1:8000/api/apps</code> to list apps, then 
        <br/> <code>curl -X POST http://127.0.0.1:8000/api/delete -H "Content-Type: application/json" -d '&#123;"items":["/path/to/delete"]&#125;'</code> to safely delete.
      </div>
    </div>
  );
};

export default AIAdvisor;
