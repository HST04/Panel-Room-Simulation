import React from 'react';
import { Bolt } from 'lucide-react';

export default function SingleLineDiagram({ panels, onPanelClick }) {
  
  const getLineStatus = (panelId, upstreamId = null) => {
    const panel = panels[panelId];
    if (!panel) return { color: '#475569', flowClass: 'flow-line-static' };

    const isClosed = panel.state === 'closed';
    const isTripped = panel.state === 'tripped';
    
    let isUpstreamLive = true;
    if (upstreamId) {
      const upstream = panels[upstreamId];
      isUpstreamLive = upstream && upstream.state === 'closed';
    }

    if (isTripped) return { color: '#f59e0b', flowClass: 'flow-line-static' }; 
    
    if (isClosed && isUpstreamLive) {
      if (panelId === 'solar_panel') return { color: '#eab308', flowClass: 'flow-line-reverse' };
      if (panelId === 'capacitor_bank_6' || panelId === 'capacitor_panel') return { color: '#a855f7', flowClass: 'flow-line' };
      return { color: '#ef4444', flowClass: 'flow-line' };
    }

    return { color: '#1e293b', flowClass: 'flow-line-static' };
  };

  const renderPanelBox = (id, x, y, width = 95, height = 50) => {
    const p = panels[id];
    if (!p) return null;

    const isClosed = p.state === 'closed';
    const isTripped = p.state === 'tripped';
    const currentText = p.current > 0 ? `${p.current.toFixed(1)}A` : '0A';
    
    const panelStatusClass = isClosed ? 'sld-panel-closed' : isTripped ? 'sld-panel-tripped' : 'sld-panel-open';
    const rectColor = isClosed ? '#ef4444' : isTripped ? '#f59e0b' : '#334155';

    return (
      <g 
        key={id} 
        transform={`translate(${x - width/2}, ${y - height/2})`}
        onClick={() => onPanelClick(id)}
        className={`sld-node ${panelStatusClass}`}
      >
        <rect 
          width={width} 
          height={height} 
          rx="6" 
          fill="#0f172a" 
          stroke={rectColor}
          strokeWidth={isTripped ? '2' : '1.5'}
          className="sld-rect"
        />
        
        <text 
          x={width/2} 
          y="18" 
          fill="#cbd5e1" 
          fontSize="8" 
          fontWeight="700" 
          textAnchor="middle" 
          className="sld-node-title"
        >
          {p.label.length > 15 ? p.label.substring(0, 14) + '..' : p.label}
        </text>

        <text 
          x={width/2} 
          y="32" 
          fill={isClosed ? '#ef4444' : '#64748b'} 
          fontSize="9" 
          fontWeight="bold" 
          textAnchor="middle" 
          className="sld-node-current"
        >
          {currentText}
        </text>

        <circle 
          cx={width/2} 
          cy="42" 
          r="3" 
          fill={isClosed ? '#ef4444' : isTripped ? '#f59e0b' : '#10b981'} 
        />
      </g>
    );
  };

  return (
    <div className="sld-wrapper glass-panel">
      <div className="sld-header">
        <div>
          <h3 className="panel-title">
            <Bolt size={14} className="text-amber" />
            Interactive Single Line Diagram (SLD)
          </h3>
          <p className="sld-subtitle">Live current flow animations. Click any node box to inspect or override.</p>
        </div>
        <div className="sld-legend">
          <span className="legend-item"><span className="legend-dot bg-red"></span> Closed (Live)</span>
          <span className="legend-item"><span className="legend-dot bg-emerald"></span> Open (Safe)</span>
          <span className="legend-item"><span className="legend-dot bg-amber pulse-anim"></span> Tripped</span>
        </div>
      </div>

      <div className="sld-svg-container">
        <svg viewBox="0 0 1000 520" className="sld-svg">
          <defs>
            <linearGradient id="grid-grad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#b91c1c" stopOpacity="0.2" />
            </linearGradient>
          </defs>

          {/* UTILITY GRID */}
          <g transform="translate(500, 20)" className="sld-utility">
            <rect x="-30" y="-12" width="60" height="24" rx="3" fill="#1e293b" stroke="#475569" strokeWidth="1"/>
            <text x="0" y="4" fill="#94a3b8" fontSize="8" fontWeight="bold" textAnchor="middle">GRID UTILITY</text>
          </g>

          {(() => {
            const line = getLineStatus('33kv_incomer');
            return <line x1="500" y1="32" x2="500" y2="45" stroke={line.color} strokeWidth="2.5" className={line.flowClass} />;
          })()}

          {renderPanelBox('33kv_incomer', 500, 65, 110, 40)}

          {/* 33kV BUSBAR */}
          {(() => {
            const line = getLineStatus('33kv_incomer');
            return (
              <>
                <line x1="350" y1="100" x2="650" y2="100" stroke={line.color} strokeWidth="3" />
                <text x="290" y="98" fill="#475569" fontSize="8" fontWeight="bold">33kV BUSBAR</text>
              </>
            );
          })()}

          {/* Wires to Outgoings */}
          {(() => {
            const line = getLineStatus('33kv_incomer');
            return (
              <>
                <path d="M 500 85 L 500 100" stroke={line.color} strokeWidth="2" />
                <path d="M 350 100 L 350 110" stroke={getLineStatus('outgoing_1', '33kv_incomer').color} strokeWidth="2" className={getLineStatus('outgoing_1', '33kv_incomer').flowClass} />
                <path d="M 650 100 L 650 110" stroke={getLineStatus('outgoing_2', '33kv_incomer').color} strokeWidth="2" className={getLineStatus('outgoing_2', '33kv_incomer').flowClass} />
              </>
            );
          })()}

          {renderPanelBox('outgoing_1', 350, 125, 85, 30)}
          {renderPanelBox('outgoing_2', 650, 125, 85, 30)}

          {/* TRANSFORMERS */}
          {(() => {
            return (
              <>
                <path d="M 350 140 L 350 145 L 200 145 L 200 160" stroke={getLineStatus('t_2_panel', 'outgoing_1').color} strokeWidth="2" fill="none" className={getLineStatus('t_2_panel', 'outgoing_1').flowClass} />
                <path d="M 350 140 L 350 160" stroke={getLineStatus('t_3_panel', 'outgoing_1').color} strokeWidth="2" fill="none" className={getLineStatus('t_3_panel', 'outgoing_1').flowClass} />
                <path d="M 650 140 L 650 145 L 500 145 L 500 160" stroke={getLineStatus('t_4_panel', 'outgoing_2').color} strokeWidth="2" fill="none" className={getLineStatus('t_4_panel', 'outgoing_2').flowClass} />
                <path d="M 650 140 L 650 160" stroke={getLineStatus('t_5_panel', 'outgoing_2').color} strokeWidth="2" fill="none" className={getLineStatus('t_5_panel', 'outgoing_2').flowClass} />
                <path d="M 650 140 L 650 145 L 800 145 L 800 160" stroke={getLineStatus('t_6_panel', 'outgoing_2').color} strokeWidth="2" fill="none" className={getLineStatus('t_6_panel', 'outgoing_2').flowClass} />
              </>
            );
          })()}

          {[200, 350, 500, 650, 800].map((x, idx) => {
            const tid = `t_${idx + 2}_panel`;
            const panel = panels[tid];
            const isClosed = panel && panel.state === 'closed';
            const color = isClosed ? '#ef4444' : '#334155';
            return (
              <g key={tid} transform={`translate(${x}, 175)`}>
                <circle cx="0" cy="-6" r="10" fill="none" stroke={color} strokeWidth="2" />
                <circle cx="0" cy="6" r="10" fill="none" stroke={color} strokeWidth="2" />
                <text x="18" y="4" fill="#94a3b8" fontSize="8" fontWeight="bold">T-{idx + 2}</text>
              </g>
            );
          })}

          {renderPanelBox('t_2_panel', 200, 215, 65, 30)}
          {renderPanelBox('t_3_panel', 350, 215, 65, 30)}
          {renderPanelBox('t_4_panel', 500, 215, 65, 30)}
          {renderPanelBox('t_5_panel', 650, 215, 65, 30)}
          {renderPanelBox('t_6_panel', 800, 215, 65, 30)}

          {/* 11kV BUSBAR */}
          {(() => {
            return (
              <>
                <path d="M 350 230 L 350 250 L 300 250 L 300 265" stroke={getLineStatus('incomer_01', 't_3_panel').color} strokeWidth="2" fill="none" className={getLineStatus('incomer_01', 't_3_panel').flowClass} />
                <path d="M 500 230 L 500 250 L 700 250 L 700 265" stroke={getLineStatus('incomer_02', 't_4_panel').color} strokeWidth="2" fill="none" className={getLineStatus('incomer_02', 't_4_panel').flowClass} />
              </>
            );
          })()}

          {renderPanelBox('incomer_01', 300, 280, 80, 30)}
          {renderPanelBox('incomer_02', 700, 280, 80, 30)}

          {(() => {
            return (
              <>
                <line x1="300" y1="295" x2="300" y2="330" stroke={getLineStatus('incomer_01').color} strokeWidth="2.5" className={getLineStatus('incomer_01').flowClass} />
                <line x1="700" y1="295" x2="700" y2="330" stroke={getLineStatus('incomer_02').color} strokeWidth="2.5" className={getLineStatus('incomer_02').flowClass} />
              </>
            );
          })()}

          {(() => {
            const inc1 = getLineStatus('incomer_01');
            const inc2 = getLineStatus('incomer_02');
            const coupler = panels['bus_coupler'];
            const couplerClosed = coupler && coupler.state === 'closed';
            
            const leftColor = inc1.color !== '#1e293b' ? inc1.color : (couplerClosed ? inc2.color : '#1e293b');
            const rightColor = inc2.color !== '#1e293b' ? inc2.color : (couplerClosed ? inc1.color : '#1e293b');

            return (
              <>
                <line x1="100" y1="330" x2="445" y2="330" stroke={leftColor} strokeWidth="4" />
                <text x="50" y="327" fill="#475569" fontSize="8" fontWeight="bold">11kV BUS SEC-A</text>
                
                <line x1="445" y1="330" x2="455" y2="330" stroke={leftColor} strokeWidth="2" />
                <line x1="545" y1="330" x2="555" y2="330" stroke={rightColor} strokeWidth="2" />

                <line x1="555" y1="330" x2="900" y2="330" stroke={rightColor} strokeWidth="4" />
                <text x="910" y="327" fill="#475569" fontSize="8" fontWeight="bold">11kV BUS SEC-B</text>
              </>
            );
          })()}

          {renderPanelBox('bus_coupler', 500, 330, 90, 30)}

          {/* FEEDERS */}
          {(() => {
            const coupler = panels['bus_coupler'];
            const couplerClosed = coupler && coupler.state === 'closed';
            const inc1 = getLineStatus('incomer_01');
            const inc2 = getLineStatus('incomer_02');
            const leftActive = (inc1.color !== '#1e293b') || (couplerClosed && inc2.color !== '#1e293b');
            
            return (
              <>
                <path d="M 120 330 L 120 410" stroke={getLineStatus('solar_panel').color} strokeWidth="2" className={getLineStatus('solar_panel').flowClass} />
                <path d="M 200 330 L 200 410" stroke={leftActive && panels['breaker_11kv_730'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={leftActive && panels['breaker_11kv_730'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 280 330 L 280 410" stroke={leftActive && panels['tlb_plant'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={leftActive && panels['tlb_plant'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 360 330 L 360 410" stroke={leftActive && panels['p14_c1'].state === 'closed' ? (panels['p14_c1'].state === 'tripped' ? '#f59e0b' : '#ef4444') : '#1e293b'} strokeWidth="2" className={leftActive && panels['p14_c1'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 440 330 L 440 410" stroke={leftActive && panels['p14_c2'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={leftActive && panels['p14_c2'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
              </>
            );
          })()}

          {(() => {
            const coupler = panels['bus_coupler'];
            const couplerClosed = coupler && coupler.state === 'closed';
            const inc1 = getLineStatus('incomer_01');
            const inc2 = getLineStatus('incomer_02');
            const rightActive = (inc2.color !== '#1e293b') || (couplerClosed && inc1.color !== '#1e293b');
            
            return (
              <>
                <path d="M 560 330 L 560 410" stroke={rightActive && panels['capacitor_bank_6'].state === 'closed' ? '#a855f7' : '#1e293b'} strokeWidth="2" className={rightActive && panels['capacitor_bank_6'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 640 330 L 640 410" stroke={rightActive && panels['vcb_11kv'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={rightActive && panels['vcb_11kv'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 720 330 L 720 410" stroke={rightActive && panels['p13_c2'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={rightActive && panels['p13_c2'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 800 330 L 800 410" stroke={rightActive && panels['p12_c2'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={rightActive && panels['p12_c2'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
                <path d="M 880 330 L 880 410" stroke={rightActive && panels['p13_c3'].state === 'closed' ? '#ef4444' : '#1e293b'} strokeWidth="2" className={rightActive && panels['p13_c3'].state === 'closed' ? 'flow-line' : 'flow-line-static'} />
              </>
            );
          })()}

          {renderPanelBox('solar_panel', 120, 430, 75, 40)}
          {renderPanelBox('breaker_11kv_730', 200, 430, 75, 40)}
          {renderPanelBox('tlb_plant', 280, 430, 75, 40)}
          {renderPanelBox('p14_c1', 360, 430, 75, 40)}
          {renderPanelBox('p14_c2', 440, 430, 75, 40)}

          {renderPanelBox('capacitor_bank_6', 560, 430, 75, 40)}
          {renderPanelBox('vcb_11kv', 640, 430, 75, 40)}
          {renderPanelBox('p13_c2', 720, 430, 75, 40)}
          {renderPanelBox('p12_c2', 800, 430, 75, 40)}
          {renderPanelBox('p13_c3', 880, 430, 75, 40)}

          <text x="360" y="475" fill="#475569" fontSize="7" fontWeight="bold" textAnchor="middle">Old Compressor</text>
          <text x="440" y="475" fill="#475569" fontSize="7" fontWeight="bold" textAnchor="middle">Paint Shop</text>
          <text x="560" y="475" fill="#a855f7" fontSize="7" fontWeight="bold" textAnchor="middle">Cap Bank-6</text>
          <text x="720" y="475" fill="#475569" fontSize="7" fontWeight="bold" textAnchor="middle">Paint Shop #12</text>
          <text x="800" y="475" fill="#475569" fontSize="7" fontWeight="bold" textAnchor="middle">Compressor</text>
          <text x="880" y="475" fill="#475569" fontSize="7" fontWeight="bold" textAnchor="middle">Paint Shop #11</text>

          <g transform="translate(48, 480)" className="sld-floating-box" onClick={() => onPanelClick('remote_tap_changer')}>
            <rect width="80" height="35" rx="4" fill="#0f172a" stroke="#475569" strokeWidth="1" />
            <text x="40" y="12" fill="#94a3b8" fontSize="7" fontWeight="bold" textAnchor="middle">TAP CHANGER</text>
            <text x="40" y="27" fill="#10b981" fontSize="9" fontWeight="bold" textAnchor="middle" className="sld-mono">TAP: {panels['remote_tap_changer'] && panels['remote_tap_changer'].voltage ? panels['remote_tap_changer'].voltage.toFixed(0) : '0'} V</text>
          </g>

          <g transform="translate(872, 480)" className="sld-floating-box" onClick={() => onPanelClick('capacitor_panel')}>
            <rect width="80" height="35" rx="4" fill="#0f172a" stroke="#475569" strokeWidth="1" />
            <text x="40" y="12" fill="#94a3b8" fontSize="7" fontWeight="bold" textAnchor="middle">CAP PANEL</text>
            <text x="40" y="27" fill="#a855f7" fontSize="9" fontWeight="bold" textAnchor="middle" className="sld-mono">PF METER</text>
          </g>

          <g transform="translate(120, 395)" className="sld-solar-icon">
            <line x1="0" y1="0" x2="0" y2="15" stroke="#eab308" strokeWidth="1.5" strokeDasharray="3,2" />
            {panels['solar_panel'] && panels['solar_panel'].state === 'closed' && (
              <circle cx="0" cy="5" r="3" fill="#eab308" className="pulse-anim" />
            )}
          </g>
        </svg>
      </div>
    </div>
  );
}
