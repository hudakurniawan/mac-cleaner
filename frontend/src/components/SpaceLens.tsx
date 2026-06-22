import React, { useState, useEffect, useRef } from 'react';
import ReactECharts from 'echarts-for-react';

const SpaceLens: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState<string>('Idle');
  const [scannedBytes, setScannedBytes] = useState<number>(0);
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
      setStatus('Connected, starting scan...');
      ws.current?.send(JSON.stringify({ path: '~/Documents' })); // Scan Documents by default for safety/speed demo
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
      type: 'sunburst',
      data: data ? [data] : [],
      radius: [0, '90%'],
      label: {
        rotate: 'radial',
        formatter: '{b}'
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

  return (
    <div className="space-lens-container" style={{ padding: '20px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '12px', backdropFilter: 'blur(10px)' }}>
      <h2>Space Lens (Disk Analyzer)</h2>
      <button 
        onClick={startScan}
        style={{ padding: '10px 20px', borderRadius: '8px', background: '#3b82f6', color: 'white', border: 'none', cursor: 'pointer', marginBottom: '20px' }}
      >
        Start Scan (~/Documents)
      </button>
      
      <div className="status-bar" style={{ marginBottom: '20px' }}>
        <p><strong>Status:</strong> {status}</p>
        {scannedBytes > 0 && <p><strong>Scanned:</strong> {formatBytes(scannedBytes)}</p>}
      </div>

      {data && (
        <div style={{ height: '600px', width: '100%' }}>
          <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
        </div>
      )}
    </div>
  );
};

export default SpaceLens;
