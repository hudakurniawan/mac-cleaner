import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';

const SpaceLens: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState<string>('Idle');
  const [scannedBytes, setScannedBytes] = useState<number>(0);
  const [scanPath, setScanPath] = useState<string>('~/Documents');
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isBrowsing, setIsBrowsing] = useState<boolean>(false);
  const ws = useRef<WebSocket | null>(null);

  const startScan = () => {
    setStatus('Connecting...');
    setData(null);
    setScannedBytes(0);

    if (ws.current) {
        ws.current.close();
    }

    const wsUrl = `ws://${window.location.host}/ws/analyze`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setStatus(`Connected, starting scan on ${scanPath}...`);
      ws.current?.send(JSON.stringify({ path: scanPath }));
    };

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'progress') {
        setScannedBytes(msg.scanned_bytes);
        setStatus('Scanning in progress...');
      } else if (msg.type === 'status') {
        setStatus(msg.message);
      } else if (msg.type === 'complete') {
        setData(msg.tree);
        setScannedBytes(msg.total_bytes);
        setStatus('Scan complete!');
      } else if (msg.type === 'error') {
        setStatus(`Error: ${msg.message}`);
      }
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket Error: ", error);
      setStatus('WebSocket Error. Is the backend running?');
    };

    ws.current.onclose = () => {
      if (status !== 'Scan complete!') {
        setStatus('Connection closed');
      }
    };
  };

  useEffect(() => {
    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const handleBrowse = async () => {
    setIsBrowsing(true);
    try {
      const response = await fetch('/api/browse-folder');
      const result = await response.json();
      if (result.status === 'success' && result.path) {
        setScanPath(result.path);
      }
    } catch (error) {
      console.error('Failed to browse folder', error);
    } finally {
      setIsBrowsing(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const option = {
    title: {
      text: 'Space Lens',
      subtext: 'Hierarchical Storage View',
      textStyle: { fontSize: 14, align: 'center' },
      subtextStyle: { align: 'center' }
    },
    series: {
      type: 'treemap',
      data: data ? [data] : [],
      roam: false,
      nodeClick: false, // We handle clicks manually
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: '{b}\n{c} bytes',
        overflow: 'truncate'
      },
      emphasis: {
        focus: 'ancestor'
      },
      itemStyle: {
        borderRadius: 4,
        borderWidth: 2
      }
    }
  };

  const onChartClick = (params: any) => {
    if (params.data && params.data.path) {
      setSelectedPath(params.data.path);
    }
  };

  const handleDelete = async () => {
    if (!selectedPath) return;
    if (!window.confirm(`Are you sure you want to delete this folder?\n\n${selectedPath}`)) return;
    
    try {
      setStatus(`Deleting ${selectedPath}...`);
      const response = await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [selectedPath] })
      });
      const result = await response.json();
      if (result.status === 'success') {
        setStatus(`Successfully deleted ${selectedPath}. Re-run scan to update view.`);
        setSelectedPath(null);
      } else {
        setStatus(`Deletion failed: ${result.message}`);
      }
    } catch (e: any) {
      setStatus(`Deletion error: ${e.message}`);
    }
  };

  return (
    <div className="space-lens-container" style={{ padding: '20px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '12px', backdropFilter: 'blur(10px)' }}>
      <h2>Space Lens (Disk Analyzer)</h2>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input 
          type="text" 
          value={scanPath}
          onChange={(e) => setScanPath(e.target.value)}
          placeholder="Path to scan (e.g., ~/Downloads or /Applications)"
          style={{ flex: 1, padding: '10px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', color: 'white', border: '1px solid rgba(255,255,255,0.2)' }}
        />
        <button 
          onClick={handleBrowse}
          disabled={isBrowsing}
          style={{ padding: '10px 15px', borderRadius: '8px', background: 'rgba(255,255,255,0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', cursor: isBrowsing ? 'wait' : 'pointer' }}
        >
          {isBrowsing ? '...' : 'Browse...'}
        </button>
        <button 
          onClick={startScan}
          style={{ padding: '10px 20px', borderRadius: '8px', background: '#3b82f6', color: 'white', border: 'none', cursor: 'pointer' }}
        >
          Start Scan
        </button>
      </div>

      {selectedPath && (
        <div style={{ marginBottom: '20px', padding: '15px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong style={{ color: '#ef4444' }}>Selected target:</strong> <br/>
            <code style={{ fontSize: '0.9em' }}>{selectedPath}</code>
          </div>
          <button 
            onClick={handleDelete}
            style={{ padding: '10px 20px', borderRadius: '8px', background: '#ef4444', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Move to Trash
          </button>
        </div>
      )}
      
      <div className="status-bar" style={{ marginBottom: '20px' }}>
        <p><strong>Status:</strong> {status}</p>
        {scannedBytes > 0 && <p><strong>Scanned:</strong> {formatBytes(scannedBytes)}</p>}
      </div>

      {data && (
        <div style={{ height: '600px', width: '100%' }}>
          <ReactECharts 
            option={option} 
            style={{ height: '100%', width: '100%' }} 
            onEvents={{ 'click': onChartClick }}
          />
        </div>
      )}
    </div>
  );
};

export default SpaceLens;
