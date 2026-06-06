import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, Lightbulb, Send, Radio, Flame, Sun, 
  RefreshCw, Clock, Server, Sliders, Play, Pause, 
  HelpCircle, TrendingUp, Cpu
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts';

import SingleLineDiagram from './components/SingleLineDiagram';
import PanelDetailModal from './components/PanelDetailModal';

import './index.css';

export default function App() {
  const [state, setState] = useState(null);
  const [selectedPanelId, setSelectedPanelId] = useState(null);
  const [chatHistory, setChatHistory] = useState([
    { role: 'agent', text: "Hello! I am the Diagnostic RAG Agent. I have indexed the technical manuals for Protection Relay CSAD-F-170, step-down transformer T-4, and the DC control power batteries. How can I assist you with substation maintenance today?" }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/state');
        if (!res.ok) throw new Error('API server error');
        const data = await res.json();
        setState(data);
        setIsConnected(true);
      } catch (err) {
        setIsConnected(false);
        console.error("Failed to connect to substation API:", err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  if (!isConnected || !state) {
    return (
      <div className="loading-screen">
        <div className="spinner-container">
          <div className="spinner-ring"></div>
          <Radio className="spinner-icon pulse-anim" size={24} />
        </div>
        <div className="loading-text">
          <h2 className="pulse-anim">CONNECTING TO SUBSTATION OS GATEWAY...</h2>
          <p>Please ensure backend server (FastAPI) is running at http://localhost:8000</p>
        </div>
      </div>
    );
  }

  const { panels, history, system_time, bus_11kv_voltage, solar_generation_kw, solar_auto, faults, t4_wti, t4_oti, t4_cooling_fans_on } = state.simulator;
  const { alerts, recommendations, schedule } = state.agents;

  const getOverallActivekW = () => {
    return Object.values(panels)
      .filter(p => p.state === 'closed' && !['33kv_incomer', 'outgoing_1', 'outgoing_2', 'incomer_01', 'incomer_02', 'capacitor_panel', 'solar_panel'].includes(p.id))
      .reduce((sum, p) => sum + p.active_power, 0);
  };

  const getSystemPF = () => history.length > 0 ? history[history.length - 1].system_pf : 0.90;

  const handleBreakerAction = async (panelId, stateName) => {
    try {
      const res = await fetch('http://localhost:8000/api/breaker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ panel_id: panelId, state: stateName })
      });
      if (!res.ok) {
        const errData = await res.json();
        alert(errData.detail || "Action rejected.");
      }
    } catch (err) {
      alert("Failed to connect to backend server.");
    }
  };

  const handleResetAction = async (panelId) => {
    try {
      const res = await fetch('http://localhost:8000/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ panel_id: panelId })
      });
      if (res.ok) setSelectedPanelId(null);
    } catch (err) { console.error(err); }
  };

  const handleFaultInjection = async (faultName, enable) => {
    try {
      await fetch('http://localhost:8000/api/fault', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fault_name: faultName, enable })
      });
    } catch (err) { console.error(err); }
  };

  const handleToggleSolarMode = async () => {
    try {
      await fetch('http://localhost:8000/api/solar-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    } catch (err) { console.error(err); }
  };

  const handleApproveRecommendation = async (rec) => {
    try {
      const res = await fetch('http://localhost:8000/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ panel_id: rec.target, state: rec.action })
      });
      if (!res.ok) alert("Failed to apply recommendation.");
    } catch (err) { console.error(err); }
  };

  const handleChatSubmit = async (e, customText = null) => {
    if (e) e.preventDefault();
    const queryText = customText || chatInput;
    if (!queryText.trim()) return;

    setChatHistory(prev => [...prev, { role: 'user', text: queryText }]);
    if (!customText) setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: queryText })
      });
      const data = await res.json();
      setChatHistory(prev => [...prev, { role: 'agent', text: data.response }]);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'agent', text: "Error: Diagnostic Agent is unreachable." }]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="layout-container">
      {/* 1. TOP HEADER NAVIGATION */}
      <header className="app-header">
        <div className="header-title-group">
          <div className="header-icon-box">
            <Sliders size={20} />
          </div>
          <div>
            <h1>
              SUBSTATION OPERATING SYSTEM 
              <span className="badge-digital-twin">Digital Twin</span>
            </h1>
            <p className="header-subtitle">STATION ID: SEC-11KV-SPD | TELEMETRY FREQ: 1Hz</p>
          </div>
        </div>

        <div className="header-telemetry-widgets">
          <div className="widget-item">
            <span className="widget-label">Active Load Demand</span>
            <span className="widget-value text-sky">{(getOverallActivekW()).toFixed(1)} kW</span>
          </div>
          <div className="widget-divider" />
          <div className="widget-item">
            <span className="widget-label">Solar Injection</span>
            <span className="widget-value text-yellow">{(solar_generation_kw).toFixed(1)} kW</span>
          </div>
          <div className="widget-divider" />
          <div className="widget-item">
            <span className="widget-label">Power Factor</span>
            <span className={`widget-value ${getSystemPF() < 0.90 ? 'text-red pulse-anim' : getSystemPF() < 0.95 ? 'text-yellow' : 'text-emerald'}`}>
              {(getSystemPF()).toFixed(2)}
            </span>
          </div>
          <div className="widget-divider" />
          <div className="widget-item">
            <span className="widget-label">T-4 Temp Winding/Oil</span>
            <span className={`widget-value ${t4_wti > 90.0 ? 'text-red pulse-anim' : 'text-slate'}`}>
              {t4_wti.toFixed(0)}°C / {t4_oti.toFixed(0)}°C
            </span>
          </div>
        </div>

        <div className="header-controls">
          <div className="control-group">
            <span className="control-label">Solar Mode:</span>
            <button 
              onClick={handleToggleSolarMode} 
              className={`btn-mode ${solar_auto ? 'btn-mode-active' : ''}`}
            >
              {solar_auto ? 'Diurnal' : 'Fixed'}
            </button>
          </div>

          <div className="control-dropdown">
            <Flame size={14} className="text-red" />
            <select 
              onChange={(e) => {
                const fault = e.target.value;
                if (!fault) return;
                if (fault === "clear_all") {
                  handleFaultInjection("p14_c1_spike", false);
                  handleFaultInjection("t4_temp_rise", false);
                  handleFaultInjection("dc_fail", false);
                } else {
                  handleFaultInjection(fault, true);
                }
                e.target.value = "";
              }}
            >
              <option value="" disabled selected>INJECT TEST FAULT</option>
              <option value="p14_c1_spike">P14-C1 Compressor Overcurrent Spike</option>
              <option value="t4_temp_rise">Transformer T-4 Thermal Overload</option>
              <option value="dc_fail">DC Auxiliary Control Fail</option>
              <option value="clear_all">-- CLEAR ALL ACTIVE FAULTS --</option>
            </select>
          </div>
        </div>
      </header>

      {/* 2. MAIN CORE LAYOUT */}
      <main className="dashboard-content">
        
        {/* LEFT COMPONENT: SLD + TELEMETRY CHARTS */}
        <div className="panel-col">
          <div className="sld-container">
            <SingleLineDiagram panels={panels} onPanelClick={(pid) => setSelectedPanelId(pid)} />
          </div>

          <div className="chart-container">
            <div className="chart-header">
              <h3>
                <TrendingUp size={14} className="text-sky" />
                Station Telemetry Waveform Analysis (kW / °C)
              </h3>
              <div className="chart-subtitle">Ticks updated in real-time (last 30s)</div>
            </div>
            
            <div className="chart-body">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
                  <CartesianGrid stroke="#0f172a" vertical={false} />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis stroke="#475569" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff', fontSize: '12px' }}
                    labelStyle={{ display: 'none' }}
                  />
                  <Line type="monotone" dataKey="total_active_kw" stroke="#38bdf8" strokeWidth={2} name="Total kW" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="solar_kw" stroke="#eab308" strokeWidth={1.5} strokeDasharray="3 3" name="Solar kW" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="t4_wti" stroke="#f43f5e" strokeWidth={1.5} name="T-4 Temp (°C)" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* RIGHT COMPONENT: AGENT ORCHESTRATION FEED & RAG CHAT */}
        <div className="panel-col">
          
          {/* Agent Alerts and Recommendations */}
          <div className="agent-feed glass-panel">
            <h3 className="panel-title">
              <Cpu size={14} className="text-sky" />
              Agent Core Recommendations & Alerts
            </h3>
            
            <div className="agent-items-list">
              {alerts.map((alert) => (
                <div key={alert.id} className={`alert-card ${alert.severity === 'CRITICAL' ? 'alert-critical pulse-border' : 'alert-warning'}`}>
                  <div className="alert-header">
                    <ShieldAlert size={16} className={alert.severity === 'CRITICAL' ? 'text-red' : 'text-yellow'} />
                    <span>{alert.title}</span>
                  </div>
                  <p className="alert-body">{alert.message}</p>
                  {alert.action_suggestion && (
                    <div className="alert-action">
                      <strong>SOP Guide:</strong> {alert.action_suggestion}
                    </div>
                  )}
                </div>
              ))}

              {recommendations.map((rec) => (
                <div key={rec.id} className="rec-card">
                  <div className="rec-header">
                    <Lightbulb size={16} />
                    <span>Optimization Recommendation</span>
                  </div>
                  <p className="rec-body">{rec.message}</p>
                  <button onClick={() => handleApproveRecommendation(rec)} className="btn-approve">
                    Approve & Energize
                  </button>
                </div>
              ))}

              <div className="schedule-card">
                <div className="schedule-header">
                  <Clock size={12} className="text-sky" />
                  Upcoming Industrial Demand Schedules
                </div>
                <div className="schedule-list">
                  {schedule.map((sch, idx) => (
                    <div key={idx} className="schedule-item">
                      <span>{sch.time} - {sch.event}</span>
                      <span className="text-emerald">{sch.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              {alerts.length === 0 && recommendations.length === 0 && (
                <div className="agent-empty-state">
                  ● Substation is stable. No active alerts or optimizations.
                </div>
              )}
            </div>
          </div>

          {/* Diagnostic RAG Chat Dialog */}
          <div className="chat-dialog glass-panel">
            <div className="chat-header">
              <h3 className="panel-title">
                <HelpCircle size={14} className="text-emerald" />
                Diagnostic RAG Chat Agent
              </h3>
              <span className="badge-index">Manuals Library Index</span>
            </div>

            <div className="chat-feed">
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`chat-bubble-wrapper ${msg.role === 'user' ? 'chat-right' : 'chat-left'}`}>
                  <div className={`chat-bubble ${msg.role === 'user' ? 'user' : 'agent'}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="chat-bubble-wrapper chat-left">
                  <div className="chat-bubble agent loading-bubble pulse-anim">
                    Agent searching manuals and protection catalogs...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="chat-quick-actions">
              <button onClick={(e) => handleChatSubmit(e, "How to reset T-4 thermal trip?")}>T-4 Trip SOP</button>
              <button onClick={(e) => handleChatSubmit(e, "What causes DC FAIL alarm and how to inspect batteries?")}>DC Fail Protocol</button>
              <button onClick={(e) => handleChatSubmit(e, "How to recover from P14-C1 overcurrent trip?")}>P14-C1 Overcurrent Reset</button>
            </div>

            <form onSubmit={handleChatSubmit} className="chat-input-form">
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask RAG agent for troubleshooting guidelines..." 
              />
              <button type="submit"><Send size={16} /></button>
            </form>
          </div>
        </div>
      </main>

      {/* 3. MODALS & POPUPS */}
      {selectedPanelId && (
        <PanelDetailModal 
          panel={panels[selectedPanelId]} 
          onClose={() => setSelectedPanelId(null)}
          onBreakerAction={handleBreakerAction}
          onResetAction={handleResetAction}
          dcFail={faults.dc_fail}
        />
      )}
    </div>
  );
}
