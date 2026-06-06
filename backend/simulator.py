import random
import math
import time

# Panel IDs matching the CNH substation layout
PANEL_IDS = [
    "33kv_incomer", "outgoing_1", "outgoing_2",
    "t_2_panel", "t_3_panel", "t_4_panel", "t_5_panel", "t_6_panel",
    "incomer_01", "incomer_02", "bus_coupler", "vcb_11kv",
    "breaker_11kv_730", "tlb_plant", "capacitor_panel", "capacitor_bank_6",
    "solar_panel", "remote_tap_changer",
    "p14_c1", "p14_c2", "p13_c2", "p12_c2", "p13_c3"
]

PANEL_LABELS = {
    "33kv_incomer": "[33Kv] INCOMER",
    "outgoing_1": "OUTGOING 1",
    "outgoing_2": "OUTGOING 2",
    "t_2_panel": "T-2 PANEL",
    "t_3_panel": "T-3 PANEL",
    "t_4_panel": "T-4 PANEL",
    "t_5_panel": "T-5 PANEL",
    "t_6_panel": "T-6 PANEL",
    "incomer_01": "INCOMER -01",
    "incomer_02": "INCOMER-02",
    "bus_coupler": "Bus Coupler",
    "vcb_11kv": "11Kv(VCB)",
    "breaker_11kv_730": "11 kV Breaker(730 substation to spd)",
    "tlb_plant": "TLB Plant",
    "capacitor_panel": "Capacitor Panel",
    "capacitor_bank_6": "Capacitor Bank-6 (11Kv) HT",
    "solar_panel": "SOLAR PANEL(11Kv Switchboard)",
    "remote_tap_changer": "Remote Tap Changer Control Panel",
    "p14_c1": "P14-C1 (old compressor)",
    "p14_c2": "P14-C2 (paint shop)",
    "p13_c2": "P13-C2 (paint shop no:12)",
    "p12_c2": "P12-C2 (compressor panel)",
    "p13_c3": "P13-C3 (paint shop no:11)"
}

class SubstationSimulator:
    def __init__(self):
        self.panels = {}
        self.history = [] # Records global system state history
        self.system_time = 0
        
        # Grid parameters
        self.grid_voltage = 33000.0 # 33 kV
        self.bus_11kv_voltage = 11000.0 # 11 kV nominal
        self.tap_position = 0 # Tap range: -5 to +5. Each tap changes voltage by 1.25%
        self.solar_generation_kw = 450.0 # Nominal active generation
        self.solar_auto = True
        
        # System faults
        self.faults = {
            "p14_c1_spike": False, # Triggers overcurrent spike on old compressor
            "t4_temp_rise": False,  # Triggers winding temperature rise on T-4
            "dc_fail": False        # Triggers DC failure in control circuit
        }
        
        # Accumulated fault timers
        self.p14_c1_spike_duration = 0
        
        # Transformer temperature states
        self.t4_wti = 72.0 # Winding Temp Indicator (°C)
        self.t4_oti = 63.0 # Oil Temp Indicator (°C)
        self.t4_cooling_fans_on = True

        self.initialize_panels()

    def initialize_panels(self):
        for pid in PANEL_IDS:
            # Breaker states: closed, open, tripped
            # By default, incomers and transformers are closed (running)
            state = "closed"
            if pid in ["p14_c1", "capacitor_bank_6"]:
                state = "open" # Keep capacitor bank and old compressor initially off
                
            self.panels[pid] = {
                "id": pid,
                "label": PANEL_LABELS[pid],
                "state": state,
                "voltage": 0.0,
                "current": 0.0,
                "active_power": 0.0, # kW
                "reactive_power": 0.0, # kVar
                "power_factor": 0.90,
                "trip_ckt_healthy": True,
                "dc_fail": False,
                "spring_charged": True,
                "annunciator_alarms": []
            }

    def set_breaker(self, panel_id, state):
        """Toggle breaker state (closed, open). Cannot close if tripped, must reset first."""
        if panel_id not in self.panels:
            return False

        panel = self.panels[panel_id]
        
        # If DC fail is active, breakers CANNOT be tripped or closed electrically
        # They can only be tripped mechanically (we will implement this override)
        if self.faults["dc_fail"] and not state.startswith("manual_"):
            return False

        target_state = state.replace("manual_", "")
        
        if target_state == "closed":
            if panel["state"] == "tripped":
                # Must reset alarms/relays first
                return False
            panel["state"] = "closed"
        elif target_state == "open":
            panel["state"] = "open"
        elif target_state == "tripped":
            panel["state"] = "tripped"
            panel["current"] = 0.0
            panel["active_power"] = 0.0
            panel["reactive_power"] = 0.0
            
        return True

    def reset_panel_alarms(self, panel_id):
        """Clear tripped status and reset alarms for a panel."""
        if panel_id not in self.panels:
            return False
            
        panel = self.panels[panel_id]
        if panel["state"] == "tripped":
            panel["state"] = "open"
            
        panel["annunciator_alarms"] = []
        panel["trip_ckt_healthy"] = True
        
        if panel_id == "t_4_panel" and not self.faults["t4_temp_rise"]:
            self.t4_wti = 70.0
            self.t4_oti = 61.0
            
        return True

    def inject_fault(self, fault_name, enable=True):
        if fault_name in self.faults:
            self.faults[fault_name] = enable
            if fault_name == "dc_fail":
                for pid in self.panels:
                    self.panels[pid]["dc_fail"] = enable
                    if enable:
                        self.panels[pid]["annunciator_alarms"].append("DC FAIL ALARM")
                        self.panels[pid]["trip_ckt_healthy"] = False
                    else:
                        if "DC FAIL ALARM" in self.panels[pid]["annunciator_alarms"]:
                            self.panels[pid]["annunciator_alarms"].remove("DC FAIL ALARM")
                        self.panels[pid]["trip_ckt_healthy"] = True
            return True
        return False

    def tick(self, dt_seconds=1):
        self.system_time += dt_seconds
        
        # --- 1. Update Fault Accumulators & States ---
        if self.faults["p14_c1_spike"]:
            if self.panels["p14_c1"]["state"] == "closed":
                self.p14_c1_spike_duration += dt_seconds
            else:
                self.p14_c1_spike_duration = 0
        else:
            self.p14_c1_spike_duration = 0

        # --- 2. Calculate Active Generation and Loads ---
        # Base currents (Amps) at 11kV:
        # We will add minor noise (+/- 2%)
        noise = lambda: random.uniform(0.98, 1.02)
        
        # Feeder loads (nominal currents in Amps)
        loads = {
            "p14_c2": 68.0 * noise(), # Paint Shop main
            "p13_c2": 45.0 * noise(), # Paint Shop no. 12
            "p13_c3": 38.0 * noise(), # Paint Shop no. 11
            "p12_c2": 52.0 * noise(), # Compressor Panel
            "tlb_plant": 28.0 * noise(),
            "breaker_11kv_730": 34.0 * noise(),
            "vcb_11kv": 12.0 * noise()
        }

        # Handle old compressor P14-C1 overcurrent fault load
        if self.panels["p14_c1"]["state"] == "closed":
            if self.faults["p14_c1_spike"]:
                # High starting/overcurrent spike: 96 A
                loads["p14_c1"] = 96.0 * noise()
                # Trigger alarms
                if "OVERCURRENT ALERT" not in self.panels["p14_c1"]["annunciator_alarms"]:
                    self.panels["p14_c1"]["annunciator_alarms"].append("OVERCURRENT ALERT")
            else:
                # Normal running current: 32 A
                loads["p14_c1"] = 32.0 * noise()
                if "OVERCURRENT ALERT" in self.panels["p14_c1"]["annunciator_alarms"]:
                    self.panels["p14_c1"]["annunciator_alarms"].remove("OVERCURRENT ALERT")
        else:
            loads["p14_c1"] = 0.0

        # Adjust solar output based on system time (simulating diurnal peak around mid-day)
        # Assuming 24-minute system day cycle (1 minute = 1 hour)
        hour = (self.system_time / 60.0) % 24.0
        if self.solar_auto:
            # Solar peak at 12:00 PM (hour = 12)
            solar_factor = max(0.0, math.sin(math.pi * (hour - 6.0) / 12.0)) if 6.0 <= hour <= 18.0 else 0.0
            self.solar_generation_kw = 600.0 * solar_factor
        
        # Tap Changer voltage scaling
        self.bus_11kv_voltage = 11000.0 * (1.0 + (self.tap_position * 0.0125))

        # --- 3. Compute Power Factor and Capacitor compensation ---
        # Base power factor of loads is lagging, around 0.86
        base_pf = 0.86
        active_kw_sum = 0.0
        reactive_kvar_sum = 0.0
        
        # Downstream feeders power calculation
        for pid, current in loads.items():
            panel = self.panels[pid]
            if panel["state"] == "closed":
                panel["voltage"] = self.bus_11kv_voltage
                panel["current"] = current
                panel["power_factor"] = base_pf
                
                # P = sqrt(3) * V * I * PF / 1000 (kW)
                kw = math.sqrt(3) * self.bus_11kv_voltage * current * base_pf / 1000.0
                # Q = P * tan(acos(PF))
                kvar = kw * math.tan(math.acos(base_pf))
                
                panel["active_power"] = kw
                panel["reactive_power"] = kvar
                
                active_kw_sum += kw
                reactive_kvar_sum += kvar
            else:
                panel["voltage"] = self.bus_11kv_voltage
                panel["current"] = 0.0
                panel["active_power"] = 0.0
                panel["reactive_power"] = 0.0

        # Solar Panel generation injects active power (-kW)
        if self.panels["solar_panel"]["state"] == "closed":
            self.panels["solar_panel"]["voltage"] = self.bus_11kv_voltage
            self.panels["solar_panel"]["active_power"] = -self.solar_generation_kw
            self.panels["solar_panel"]["reactive_power"] = 0.0
            # Current generated I = kW * 1000 / (sqrt(3) * V)
            self.panels["solar_panel"]["current"] = self.solar_generation_kw * 1000.0 / (math.sqrt(3) * self.bus_11kv_voltage)
            self.panels["solar_panel"]["power_factor"] = 1.00
            
            # Reduces grid load active demand
            active_kw_sum = max(50.0, active_kw_sum - self.solar_generation_kw)
        else:
            self.panels["solar_panel"]["voltage"] = self.bus_11kv_voltage
            self.panels["solar_panel"]["current"] = 0.0
            self.panels["solar_panel"]["active_power"] = 0.0
            self.panels["solar_panel"]["reactive_power"] = 0.0

        # Capacitor bank compensation
        # If Capacitor Bank 6 is CLOSED, it injects leading reactive power (-kVar)
        cap_kvar_rating = 1050.0 # 1.05 MVar leading compensation
        if self.panels["capacitor_bank_6"]["state"] == "closed":
            self.panels["capacitor_bank_6"]["voltage"] = self.bus_11kv_voltage
            self.panels["capacitor_bank_6"]["active_power"] = 5.0 # Parasitic/heating losses
            self.panels["capacitor_bank_6"]["reactive_power"] = -cap_kvar_rating
            # Current
            self.panels["capacitor_bank_6"]["current"] = cap_kvar_rating * 1000.0 / (math.sqrt(3) * self.bus_11kv_voltage)
            self.panels["capacitor_bank_6"]["power_factor"] = 0.05 # Pure leading (almost 0)
            
            # Compensate reactive sum
            reactive_kvar_sum = max(0.0, reactive_kvar_sum - cap_kvar_rating)
        else:
            self.panels["capacitor_bank_6"]["voltage"] = self.bus_11kv_voltage
            self.panels["capacitor_bank_6"]["current"] = 0.0
            self.panels["capacitor_bank_6"]["active_power"] = 0.0
            self.panels["capacitor_bank_6"]["reactive_power"] = 0.0

        # Calculate combined 11kV busbar power factor
        if active_kw_sum > 0:
            compensated_pf = math.cos(math.atan(reactive_kvar_sum / active_kw_sum))
        else:
            compensated_pf = 1.0

        # --- 4. Distribute load on Incomers (Section A vs Section B) ---
        # Bus coupler status:
        bus_coupler = self.panels["bus_coupler"]
        inc1 = self.panels["incomer_01"]
        inc2 = self.panels["incomer_02"]

        if bus_coupler["state"] == "closed":
            # Shared load if both incomers are closed
            inc1_closed = inc1["state"] == "closed"
            inc2_closed = inc2["state"] == "closed"
            
            if inc1_closed and inc2_closed:
                inc1["active_power"] = active_kw_sum * 0.5
                inc1["reactive_power"] = reactive_kvar_sum * 0.5
                inc2["active_power"] = active_kw_sum * 0.5
                inc2["reactive_power"] = reactive_kvar_sum * 0.5
            elif inc1_closed:
                inc1["active_power"] = active_kw_sum
                inc1["reactive_power"] = reactive_kvar_sum
                inc2["active_power"] = 0.0
                inc2["reactive_power"] = 0.0
            elif inc2_closed:
                inc1["active_power"] = 0.0
                inc1["reactive_power"] = 0.0
                inc2["active_power"] = active_kw_sum
                inc2["reactive_power"] = reactive_kvar_sum
            else:
                inc1["active_power"] = 0.0
                inc1["reactive_power"] = 0.0
                inc2["active_power"] = 0.0
                inc2["reactive_power"] = 0.0
        else:
            # Bus coupler is OPEN. Incomer 1 feeds Section A, Incomer 2 feeds Section B
            # Section A loads: p14_c1, p14_c2, tlb_plant, breaker_11kv_730, solar
            # Section B loads: p13_c2, p12_c2, p13_c3, vcb_11kv, cap_bank_6
            sec_a_kw = 0.0
            sec_a_kvar = 0.0
            sec_b_kw = 0.0
            sec_b_kvar = 0.0
            
            # Accumulate Section A
            for pid in ["p14_c1", "p14_c2", "tlb_plant", "breaker_11kv_730", "solar_panel"]:
                p = self.panels[pid]
                if p["state"] == "closed":
                    sec_a_kw += p["active_power"]
                    sec_a_kvar += p["reactive_power"]
                    
            # Accumulate Section B
            for pid in ["p13_c2", "p12_c2", "p13_c3", "vcb_11kv", "capacitor_bank_6"]:
                p = self.panels[pid]
                if p["state"] == "closed":
                    sec_b_kw += p["active_power"]
                    sec_b_kvar += p["reactive_power"]

            # Set incomers
            if inc1["state"] == "closed":
                inc1["active_power"] = max(0.0, sec_a_kw)
                inc1["reactive_power"] = max(0.0, sec_a_kvar)
            else:
                inc1["active_power"] = 0.0
                inc1["reactive_power"] = 0.0
                
            if inc2["state"] == "closed":
                inc2["active_power"] = max(0.0, sec_b_kw)
                inc2["reactive_power"] = max(0.0, sec_b_kvar)
            else:
                inc2["active_power"] = 0.0
                inc2["reactive_power"] = 0.0

        # Update incomer currents and voltages
        for inc in [inc1, inc2]:
            if inc["state"] == "closed":
                inc["voltage"] = self.bus_11kv_voltage
                inc["power_factor"] = compensated_pf
                # I = P*1000 / (sqrt(3) * V * PF)
                s = inc["active_power"]**2 + inc["reactive_power"]**2
                apparent_kva = math.sqrt(s)
                inc["current"] = apparent_kva * 1000.0 / (math.sqrt(3) * self.bus_11kv_voltage)
            else:
                inc["voltage"] = self.bus_11kv_voltage
                inc["current"] = 0.0
                inc["power_factor"] = 1.0

        # --- 5. Transformer loading and Temperature rise logic ---
        # Transformers T-3 and T-4 feed Incomer-01 and Incomer-02 (through 33kV outgoing panel 1 and 2)
        # Let's map T-4 load directly to Incomer-02 load
        t_4 = self.panels["t_4_panel"]
        t_4["state"] = self.panels["outgoing_2"]["state"] # Tied to outgoing 33kV panel state
        
        if t_4["state"] == "closed":
            # Transformer 4 load active/reactive power matches Incomer 02
            t_4["active_power"] = inc2["active_power"]
            t_4["reactive_power"] = inc2["reactive_power"]
            t_4["voltage"] = 33000.0 # HV side voltage
            
            apparent_kva = math.sqrt(t_4["active_power"]**2 + t_4["reactive_power"]**2)
            t_4["current"] = apparent_kva * 1000.0 / (math.sqrt(3) * 33000.0) # HV side current
            t_4["power_factor"] = inc2["power_factor"]
            
            # Temperature calculations: Winding/Oil temperature based on loading
            # Max capacity is 10MVA (10,000 kVA). Winding temp increases quadratically with load ratio.
            load_ratio = apparent_kva / 10000.0
            
            # WTI and OTI Thermal dynamics
            cooling_factor = 0.6 if self.t4_cooling_fans_on else 1.2
            
            if self.faults["t4_temp_rise"]:
                # Force thermal overload
                target_wti = 118.0
                target_oti = 98.0
            else:
                # WTI normal range: 60 + 35 * load_ratio^2
                target_wti = 60.0 + (35.0 * (load_ratio ** 2))
                target_oti = 50.0 + (25.0 * (load_ratio ** 2))
                
            # Smooth interpolation
            self.t4_wti += (target_wti - self.t4_wti) * 0.05 * dt_seconds
            self.t4_oti += (target_oti - self.t4_oti) * 0.04 * dt_seconds
            
            # WTI Alarms
            if self.t4_wti >= 90.0:
                if "WTI HIGH ALARM" not in t_4["annunciator_alarms"]:
                    t_4["annunciator_alarms"].append("WTI HIGH ALARM")
            else:
                if "WTI HIGH ALARM" in t_4["annunciator_alarms"]:
                    t_4["annunciator_alarms"].remove("WTI HIGH ALARM")
                    
            if self.t4_oti >= 85.0:
                if "OTI HIGH ALARM" not in t_4["annunciator_alarms"]:
                    t_4["annunciator_alarms"].append("OTI HIGH ALARM")
            else:
                if "OTI HIGH ALARM" in t_4["annunciator_alarms"]:
                    t_4["annunciator_alarms"].remove("OTI HIGH ALARM")
                    
            # WTI/OTI Trips
            if self.t4_wti >= 110.0 or self.t4_oti >= 95.0:
                if "WTI TRIP" not in t_4["annunciator_alarms"]:
                    t_4["annunciator_alarms"].append("WTI TRIP")
                    # Trip breaker automatically!
                    self.set_breaker("outgoing_2", "tripped")
                    self.set_breaker("incomer_02", "tripped")
        else:
            t_4["current"] = 0.0
            t_4["active_power"] = 0.0
            t_4["reactive_power"] = 0.0
            t_4["voltage"] = 33000.0
            
            # Cool down
            self.t4_wti += (35.0 - self.t4_wti) * 0.03 * dt_seconds
            self.t4_oti += (30.0 - self.t4_oti) * 0.02 * dt_seconds
            
            if "WTI HIGH ALARM" in t_4["annunciator_alarms"]: t_4["annunciator_alarms"].remove("WTI HIGH ALARM")
            if "OTI HIGH ALARM" in t_4["annunciator_alarms"]: t_4["annunciator_alarms"].remove("OTI HIGH ALARM")

        # Map other transformers (T-2, T-3, T-5, T-6) values to match average currents
        for tid in ["t_2_panel", "t_3_panel", "t_5_panel", "t_6_panel"]:
            trans = self.panels[tid]
            if trans["state"] == "closed":
                trans["voltage"] = 33000.0
                trans["power_factor"] = compensated_pf
                trans["active_power"] = active_kw_sum / 5.0
                trans["reactive_power"] = reactive_kvar_sum / 5.0
                apparent_kva = math.sqrt(trans["active_power"]**2 + trans["reactive_power"]**2)
                trans["current"] = apparent_kva * 1000.0 / (math.sqrt(3) * 33000.0)
            else:
                trans["current"] = 0.0
                trans["active_power"] = 0.0
                trans["reactive_power"] = 0.0

        # --- 6. 33kV Incoming Grid Calculations ---
        grid = self.panels["33kv_incomer"]
        out1 = self.panels["outgoing_1"]
        out2 = self.panels["outgoing_2"]
        
        # Outgoing 1 feeds T-2, T-3
        out1["state"] = "closed" if (self.panels["t_2_panel"]["state"] == "closed" or self.panels["t_3_panel"]["state"] == "closed") else "open"
        out2["state"] = "closed" if (self.panels["t_4_panel"]["state"] == "closed" or self.panels["t_5_panel"]["state"] == "closed" or self.panels["t_6_panel"]["state"] == "closed") else "open"

        for op in [out1, out2]:
            if op["state"] == "closed":
                op["voltage"] = 33000.0
                op["power_factor"] = compensated_pf
                # Sum loads of fed transformers
                t_list = ["t_2_panel", "t_3_panel"] if op["id"] == "outgoing_1" else ["t_4_panel", "t_5_panel", "t_6_panel"]
                op["active_power"] = sum(self.panels[t]["active_power"] for t in t_list)
                op["reactive_power"] = sum(self.panels[t]["reactive_power"] for t in t_list)
                apparent_kva = math.sqrt(op["active_power"]**2 + op["reactive_power"]**2)
                op["current"] = apparent_kva * 1000.0 / (math.sqrt(3) * 33000.0)
            else:
                op["voltage"] = 33000.0
                op["current"] = 0.0
                op["active_power"] = 0.0
                op["reactive_power"] = 0.0

        # Main 33kV Incomer
        if grid["state"] == "closed":
            grid["voltage"] = 33000.0
            grid["power_factor"] = compensated_pf
            grid["active_power"] = out1["active_power"] + out2["active_power"]
            grid["reactive_power"] = out1["reactive_power"] + out2["reactive_power"]
            apparent_kva = math.sqrt(grid["active_power"]**2 + grid["reactive_power"]**2)
            grid["current"] = apparent_kva * 1000.0 / (math.sqrt(3) * 33000.0)
        else:
            grid["voltage"] = 33000.0
            grid["current"] = 0.0
            grid["active_power"] = 0.0
            grid["reactive_power"] = 0.0

        # Tap Changer Panel and Capacitor Panel telemetry sync
        self.panels["remote_tap_changer"]["voltage"] = self.bus_11kv_voltage
        self.panels["remote_tap_changer"]["current"] = 0.0
        self.panels["capacitor_panel"]["voltage"] = self.bus_11kv_voltage
        self.panels["capacitor_panel"]["current"] = self.panels["capacitor_bank_6"]["current"]

        # --- 7. Automatic Safety Interlocks (Trips) ---
        # Anomaly Trip: Old compressor overcurrent Stage 1 curve validation
        if self.p14_c1_spike_duration >= 5: # 5 seconds of sustained spike
            self.set_breaker("p14_c1", "tripped")
            self.panels["p14_c1"]["annunciator_alarms"].append("OVERCURRENT TRIP")
            self.p14_c1_spike_duration = 0

        # --- 8. Append History ---
        self.history.append({
            "timestamp": time.time(),
            "total_active_kw": active_kw_sum,
            "total_reactive_kvar": reactive_kvar_sum,
            "system_pf": compensated_pf,
            "solar_kw": self.solar_generation_kw,
            "t4_wti": self.t4_wti,
            "t4_oti": self.t4_oti,
            "p14_c1_current": self.panels["p14_c1"]["current"],
            "grid_current": grid["current"]
        })
        
        # Maintain history cap of last 30 entries
        if len(self.history) > 30:
            self.history.pop(0)

    def get_state(self):
        return {
            "panels": self.panels,
            "history": self.history,
            "system_time": self.system_time,
            "tap_position": self.tap_position,
            "bus_11kv_voltage": round(self.bus_11kv_voltage, 1),
            "solar_generation_kw": round(self.solar_generation_kw, 2),
            "solar_auto": self.solar_auto,
            "faults": self.faults,
            "t4_wti": round(self.t4_wti, 2),
            "t4_oti": round(self.t4_oti, 2),
            "t4_cooling_fans_on": self.t4_cooling_fans_on
        }

if __name__ == "__main__":
    sim = SubstationSimulator()
    print("Sim initial load values...")
    sim.set_breaker("p14_c1", "closed")
    sim.tick(1)
    state = sim.get_state()
    print(f"P14-C1 Current: {state['panels']['p14_c1']['current']} A")
    print(f"Solar Out: {state['solar_generation_kw']} kW")
    print(f"Voltage: {state['bus_11kv_voltage']} V")
    
    # Spike fault check
    sim.inject_fault("p14_c1_spike", True)
    for _ in range(6):
        sim.tick(1)
    state = sim.get_state()
    print(f"After Overcurrent Fault - P14-C1 State: {state['panels']['p14_c1']['state']}, Alarms: {state['panels']['p14_c1']['annunciator_alarms']}")
