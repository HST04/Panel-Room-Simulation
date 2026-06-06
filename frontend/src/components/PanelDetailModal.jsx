import React, { useState } from 'react';
import { X, ShieldAlert, Zap, Cpu, Settings } from 'lucide-react';

export default function PanelDetailModal({ panel, onClose, onBreakerAction, onResetAction, dcFail }) {
  const [lampTest, setLampTest] = useState(false);
  const [rotaryState, setRotaryState] = useState('NEUTRAL'); 
  const [showMechanicalManual, setShowMechanicalManual] = useState(false);

  const rotateSwitch = (target) => {
    if (dcFail && !showMechanicalManual) {
      alert("DC FAIL: Electrical remote command blocked. Control circuit is dead. Use the Mechanical Override manual trip lever.");
      return;
    }
    setRotaryState(target);
    if (target === 'CLOSE') {
      onBreakerAction(panel.id, showMechanicalManual ? 'manual_closed' : 'closed');
      setTimeout(() => setRotaryState('NEUTRAL'), 800);
    } else if (target === 'TRIP') {
      onBreakerAction(panel.id, showMechanicalManual ? 'manual_open' : 'open');
      setTimeout(() => setRotaryState('NEUTRAL'), 800);
    }
  };

  const handleEmergencyStop = () => {
    onBreakerAction(panel.id, showMechanicalManual ? 'manual_open' : 'tripped');
  };

  const alarmGrids = [
    { key: "DC FAIL ALARM", label: "DC FAIL" },
    { key: "TRIP CKT FAIL", label: "TRIP CKT FAIL" },
    { key: "WTI HIGH ALARM", label: "WTI ALARM" },
    { key: "OTI HIGH ALARM", label: "OTI ALARM" },
    { key: "BUCHHOLZ ALARM", label: "BUCHHOLZ ALARM" },
    { key: "OVERCURRENT ALERT", label: "OVERCURRENT" },
    { key: "EARTH FAULT", label: "EARTH FAULT" },
    { key: "SPRING DISCHG", label: "SPRING DISCHG" },
    { key: "TAP CHANGING", label: "TAP CHANGING" },
    { key: "WTI TRIP", label: "TEMP TRIP" },
    { key: "OVERCURRENT TRIP", label: "OVERCURRENT TRIP" },
    { key: "BUZZER ACTIVE", label: "AUX FAULT" }
  ];

  const isLedActive = (color, type) => {
    if (lampTest) return true;
    if (dcFail && type !== 'dc_fail') return false; 
    switch (type) {
      case 'on': return panel.state === 'closed';
      case 'off': return panel.state === 'open';
      case 'trip': return panel.state === 'tripped';
      case 'spring': return panel.spring_charged;
      case 'healthy': return panel.trip_ckt_healthy && panel.state === 'closed';
      case 'dc_fail': return dcFail;
      default: return false;
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content glass-panel">
        
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <Zap size={24} className={panel.state === 'closed' ? 'icon-zap-live' : 'icon-zap-dead'} />
            <div>
              <h2>{panel.label}</h2>
              <p>PANEL ID: {panel.id.toUpperCase()} | SYSTEM TYPE: 11kV VCB DRAWOUT PANEL</p>
            </div>
          </div>
          <button onClick={onClose} className="btn-close">
            <X size={24} />
          </button>
        </div>

        {/* Panel Faceplate Body */}
        <div className="modal-body">
          
          {/* LEFT SECTION: PHYSICAL CONTROL PANEL FACEPLATE */}
          <div className="modal-left-col metal-panel">
            <div className="metal-panel-brand">CNH ELECTRICAL SUBSTATION DEPT</div>
            
            {/* INDICATOR LIGHTS */}
            <div className="indicator-row shadow-inset border-metal">
              <div className="led-group">
                <span className={`led-indicator red ${isLedActive('red', 'on') ? 'active' : 'inactive'}`}></span>
                <span className="led-label">ON</span>
              </div>
              <div className="led-group">
                <span className={`led-indicator green ${isLedActive('green', 'off') ? 'active' : 'inactive'}`}></span>
                <span className="led-label">OFF</span>
              </div>
              <div className="led-group">
                <span className={`led-indicator amber ${isLedActive('amber', 'trip') ? 'active' : 'inactive'}`}></span>
                <span className="led-label">TRIP</span>
              </div>
              <div className="led-group">
                <span className={`led-indicator blue ${isLedActive('blue', 'spring') ? 'active' : 'inactive'}`}></span>
                <span className="led-label">SPRING<br/>CHRGD</span>
              </div>
              <div className="led-group">
                <span className={`led-indicator white ${isLedActive('white', 'healthy') ? 'active' : 'inactive'}`}></span>
                <span className="led-label">TRIP CKT<br/>HLTHY</span>
              </div>
              <div className="led-group">
                <span className={`led-indicator red ${isLedActive('red', 'dc_fail') ? 'active' : 'inactive'}`}></span>
                <span className="led-label led-label-red">DC<br/>FAIL</span>
              </div>
            </div>

            {/* METERS AND RELAYS */}
            <div className="meters-row">
              <div className="meter-module shadow-inset border-metal">
                <div className="meter-header">
                  <span className="meter-brand">SCHNEIDER ELECTRIC</span>
                  <span className="meter-model">A9F54-MFM</span>
                </div>
                <div className="meter-displays">
                  <div className="meter-display-col">
                    <div className={`segment-display ${dcFail ? 'inactive' : ''}`}>{dcFail ? "0.000" : panel.current.toFixed(2)}</div>
                    <span className="meter-label">CURRENT (A)</span>
                  </div>
                  <div className="meter-display-col">
                    <div className={`segment-display ${dcFail ? 'inactive' : ''}`}>{dcFail ? "0.00" : (panel.voltage / 1000.0).toFixed(2)}</div>
                    <span className="meter-label">VOLTAGE (kV)</span>
                  </div>
                </div>
                <div className="meter-footer">
                  <span>PF: {dcFail ? "0.00" : panel.power_factor.toFixed(2)}</span>
                  <span>FREQ: 50.02 Hz</span>
                </div>
              </div>

              <div className="relay-module">
                <div className="relay-model">CSAD-F-170</div>
                <div className="relay-header">
                  <span>PROTECTION RELAY</span>
                  <span className="pulse-anim">● ONLINE</span>
                </div>
                {dcFail ? (
                  <div className="relay-dead-screen">[DISPLAY DARK - DC SUPPLY FAIL]</div>
                ) : (
                  <div className="relay-stats">
                    <div>FEEDER CURRENT: {panel.current.toFixed(1)} A</div>
                    <div>SET POINT (I&gt;): 60.0 A (NI 0.15)</div>
                    <div>SET POINT (I&gt;&gt;): 120.0 A (DT 0.05)</div>
                    <div className="relay-status">STATUS: {panel.state === 'tripped' ? "TRIPPED ON OC" : panel.annunciator_alarms.length > 0 ? "ALARM ACTIVE" : "NORMAL OPERATION"}</div>
                  </div>
                )}
                <div className="relay-footer">
                  <span>CSE PROTEC</span>
                  <span>RESET REQUIRED: {panel.state === 'tripped' ? 'YES' : 'NO'}</span>
                </div>
              </div>
            </div>

            {/* ANNUNCIATOR MATRIX */}
            <div className="annunciator-module">
              <div className="annunciator-title">MM30 Annunciator Panel Matrix</div>
              <div className="annunciator-grid">
                {alarmGrids.map((cell, idx) => {
                  const isActive = !lampTest && (dcFail ? (cell.key === "DC FAIL ALARM") : panel.annunciator_alarms.includes(cell.key));
                  return (
                    <div key={idx} className={`annunciator-cell ${isActive ? 'alarm-active' : ''}`}>
                      {cell.label}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* SWITCHES AND INTERACTIVE CONTROLS */}
            <div className="controls-row shadow-inset border-metal">
              <div className="rotary-col">
                <span className="control-label-dark">Breaker Control<br/>CS Switch</span>
                <div className="rotary-switch-container">
                  <div className="rotary-tick-top">NEUTRAL</div>
                  <div className="rotary-tick-left" onClick={() => rotateSwitch('TRIP')}>TRIP</div>
                  <div className="rotary-tick-right" onClick={() => rotateSwitch('CLOSE')}>CLOSE</div>
                  <div className="switch-rotary" onClick={() => rotateSwitch(rotaryState === 'NEUTRAL' ? 'CLOSE' : 'NEUTRAL')}>
                    <div className="switch-rotary-knob" style={{ transform: rotaryState === 'TRIP' ? 'rotate(-45deg)' : rotaryState === 'CLOSE' ? 'rotate(45deg)' : 'rotate(0deg)' }}></div>
                  </div>
                </div>
              </div>

              <div className="estop-col">
                <span className="control-label-red">Emergency<br/>Trip Push</span>
                <button onClick={handleEmergencyStop} className="btn-estop" title="Immediately trips the circuit breaker mechanically">
                  <div className="btn-estop-inner">TRIP</div>
                </button>
              </div>

              <div className="action-btns-col">
                <div className="action-btns-row">
                  <button onClick={() => setLampTest(!lampTest)} className="btn-lamp-test">Lamp Test</button>
                  <button onClick={() => { if (panel.annunciator_alarms.length > 0) alert("Annunciator alarms acknowledged."); }} className="btn-accept">Accept</button>
                </div>
                <button onClick={() => onResetAction(panel.id)} className="btn-reset">Reset Relay & Alarm</button>
              </div>
            </div>
          </div>

          {/* RIGHT SECTION: TELEMETRY ANALYSIS AND AGENT READOUTS */}
          <div className="modal-right-col">
            <div className="telemetry-card">
              <h3 className="panel-title">
                <Cpu size={14} className="text-sky" /> Live Telemetry Calculations
              </h3>
              <div className="telemetry-grid">
                <div className="telemetry-cell">
                  <div className="telemetry-label">CURRENT</div>
                  <div className="telemetry-value text-sky">{panel.current.toFixed(1)} A</div>
                </div>
                <div className="telemetry-cell">
                  <div className="telemetry-label">VOLTAGE</div>
                  <div className="telemetry-value text-sky">{(panel.voltage / 1000).toFixed(2)} kV</div>
                </div>
                <div className="telemetry-cell full-width">
                  <div className="telemetry-label">ACTIVE DEMAND</div>
                  <div className="telemetry-value text-emerald">{panel.active_power.toFixed(1)} kW</div>
                </div>
                <div className="telemetry-cell full-width">
                  <div className="telemetry-label">REACTIVE DRAW</div>
                  <div className="telemetry-value text-purple">{panel.reactive_power.toFixed(1)} kVar</div>
                </div>
              </div>
            </div>

            <div className="interlocks-card">
              <h3 className="panel-title">
                <Settings size={14} className="text-slate" /> Mechanical Interlocks
              </h3>
              <div className="interlocks-list">
                <div className="interlock-item">
                  <span className="interlock-label">Breaker Status:</span>
                  <span className={`interlock-status ${panel.state === 'closed' ? 'text-red' : panel.state === 'tripped' ? 'text-yellow pulse-anim' : 'text-emerald'}`}>
                    {panel.state.toUpperCase()}
                  </span>
                </div>
                <div className="interlock-item">
                  <span className="interlock-label">Spring Charge Status:</span>
                  <span className="interlock-status text-sky">CHARGED (Motorized)</span>
                </div>
                <div className="interlock-item">
                  <span className="interlock-label">Trip Circuit Supervision:</span>
                  <span className={`interlock-status ${panel.trip_ckt_healthy ? 'text-emerald' : 'text-red'}`}>
                    {panel.trip_ckt_healthy ? 'HEALTHY' : 'FAULTY / DISCHARGED'}
                  </span>
                </div>
              </div>
            </div>

            {dcFail && (
              <div className="dc-fail-card pulse-border">
                <h4 className="dc-fail-title">
                  <ShieldAlert size={14} /> DC Failure Emergency Protocol
                </h4>
                <p className="dc-fail-body">
                  Electrical remote close/trip signals are locked out. Use the VCB housing mechanical release lever to hand-trip or manual-close.
                </p>
                <div className="mech-override">
                  <input type="checkbox" id="chk-mech-override" checked={showMechanicalManual} onChange={(e) => setShowMechanicalManual(e.target.checked)} />
                  <label htmlFor="chk-mech-override">Engage Mechanical Manual Lever</label>
                </div>
              </div>
            )}

            <div className="modal-tip-card">
              <strong>💡 Quick Operator Tip</strong>
              <p>To simulate overcurrent tripping, close this panel, go to the top header fault injector, and trigger a "P14-C1 Compressor Spike". It will trip this panel within 5 seconds.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
