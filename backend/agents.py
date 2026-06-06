import time
from rag_data import SubstationRAG

class AnomalyAgent:
    def __init__(self):
        pass

    def analyze(self, state):
        alerts = []
        panels = state["panels"]
        
        # 1. Check Old Compressor Feeder (P14-C1)
        p14_c1 = panels["p14_c1"]
        if p14_c1["state"] == "closed" and p14_c1["current"] > 80.0:
            alerts.append({
                "id": "p14_c1_overcurrent_warning",
                "severity": "CRITICAL",
                "panel": "p14_c1",
                "title": "Old Compressor Load Spike Detected",
                "message": f"Feeder P14-C1 current has spiked to {round(p14_c1['current'], 1)}A (nominal 32A). Vacuum circuit breaker (VCB) will trip on IDMT overcurrent curve in less than 5 seconds if condition persists.",
                "action_suggestion": "Verify compressor head loading valve status or isolate non-critical air lines."
            })
        elif p14_c1["state"] == "tripped":
            alerts.append({
                "id": "p14_c1_tripped_alarm",
                "severity": "ERROR",
                "panel": "p14_c1",
                "title": "P14-C1 Breaker Tripped on Overcurrent",
                "message": "Feeder P14-C1 circuit breaker tripped (CSAD-F-170 Protection Relay flagged Stage 1/2 overcurrent).",
                "action_suggestion": "Query Diagnostic Agent (RAG) for 'P14-C1 overcurrent trip recovery' before attempting a reset."
            })

        # 2. Check Transformer T-4 Thermal limits
        t4_panel = panels["t_4_panel"]
        if t4_panel["state"] == "closed":
            wti = state["t4_wti"]
            oti = state["t4_oti"]
            if wti >= 110.0 or oti >= 95.0:
                alerts.append({
                    "id": "t4_thermal_trip_alarm",
                    "severity": "ERROR",
                    "panel": "t_4_panel",
                    "title": "T-4 Transformer Winding Thermal Trip",
                    "message": f"T-4 Winding Temperature ({wti}°C) or Oil Temperature ({oti}°C) has exceeded trip limits. Outgoing 2 and Incomer 2 have been tripped automatically.",
                    "action_suggestion": "Inspect cooling fan Contactor, verify radiator obstructions, and run insulation Megger test."
                })
            elif wti >= 90.0:
                alerts.append({
                    "id": "t4_wti_high_warning",
                    "severity": "WARNING",
                    "panel": "t_4_panel",
                    "title": "T-4 High Winding Temperature Warning",
                    "message": f"T-4 Winding Temperature is critical: {wti}°C (Alarm threshold: 90.0°C).",
                    "action_suggestion": "Activate additional ONAF Cooling Fans immediately or transfer loads via Bus Coupler."
                })
            elif oti >= 85.0:
                alerts.append({
                    "id": "t4_oti_high_warning",
                    "severity": "WARNING",
                    "panel": "t_4_panel",
                    "title": "T-4 High Oil Temperature Warning",
                    "message": f"T-4 Oil Temperature is high: {oti}°C (Alarm threshold: 85.0°C).",
                    "action_suggestion": "Inspect radiator heat dissipation, switch fans to MANUAL, and verify oil levels."
                })

        # 3. Check DC Power supply Failures
        if state["faults"]["dc_fail"]:
            alerts.append({
                "id": "dc_fail_emergency",
                "severity": "CRITICAL",
                "panel": "remote_tap_changer",
                "title": "DC CONTROL POWER SYSTEM FAILURE",
                "message": "Substation 110V DC auxiliary power is LOST! All protective relays cannot trip breakers electrically during grid short-circuit faults.",
                "action_suggestion": "EMERGENCY: If grid faults occur, you must trip circuit breakers physically using the mechanical TRIP levers inside the VCB panel housings."
            })

        return alerts


class OptimizationAgent:
    def __init__(self):
        # Mock production schedule
        self.schedule = [
            {"time": "14:00 - 17:00", "event": "Paint Shop peak spray run (Heavy current P14-C2)", "status": "Upcoming"},
            {"time": "12:00 - 15:00", "event": "Peak Solar Grid feed-in window (High efficiency)", "status": "Ongoing"},
            {"time": "18:00 - 21:00", "event": "Peak Utility Tariff window (Reduce incoming drawing)", "status": "Upcoming"}
        ]

    def analyze(self, state):
        recommendations = []
        panels = state["panels"]
        
        # 1. Power Factor Optimization (Capacitor Bank-6)
        system_pf = state["history"][-1]["system_pf"] if state["history"] else 0.90
        cap_bank = panels["capacitor_bank_6"]
        
        if cap_bank["state"] == "open" and system_pf < 0.90:
            recommendations.append({
                "id": "engage_cap_bank_6",
                "agent": "Optimization Agent",
                "type": "POWER_FACTOR",
                "title": "Engage Capacitor Bank-6",
                "message": f"Current system power factor is low ({round(system_pf, 2)}). Engaging Capacitor Bank-6 will inject 1050 kVar leading compensation, boosting the power factor to ~0.98, avoiding reactive demand charges from the grid utility.",
                "action": "close_breaker",
                "target": "capacitor_bank_6"
            })
        elif cap_bank["state"] == "closed" and system_pf > 0.99 and panels["p14_c2"]["state"] == "open":
            # If loads are very low and cap bank is on, we might overcompensate (leading power factor is also bad)
            recommendations.append({
                "id": "disengage_cap_bank_6",
                "agent": "Optimization Agent",
                "type": "POWER_FACTOR",
                "title": "Disengage Capacitor Bank-6 (Over-correction)",
                "message": f"System loads are low, and Capacitor Bank-6 is over-correcting the power factor (leading PF). Disengage Capacitor Bank-6 to restore balance.",
                "action": "open_breaker",
                "target": "capacitor_bank_6"
            })

        # 2. Solar Peak Shaving Optimization
        solar_panel = panels["solar_panel"]
        solar_gen = state["solar_generation_kw"]
        
        if solar_panel["state"] == "open" and solar_gen > 100.0:
            recommendations.append({
                "id": "engage_solar",
                "agent": "Optimization Agent",
                "type": "PEAK_SHAVING",
                "title": "Synchronize Solar Panel (11kV)",
                "message": f"Active solar grid generation is available ({round(solar_gen, 1)} kW). Synchronize the solar feeder panel to shave off Peak Grid demand charges.",
                "action": "close_breaker",
                "target": "solar_panel"
            })

        # 3. Transformer Load Balancing
        # If Bus Coupler is closed, and T-4 is running hot, we can open the Bus Coupler or transfer loads
        bus_coupler = panels["bus_coupler"]
        t4_wti = state["t4_wti"]
        if bus_coupler["state"] == "closed" and t4_wti > 95.0 and panels["incomer_01"]["state"] == "closed":
            recommendations.append({
                "id": "open_bus_coupler_load_shed",
                "agent": "Optimization Agent",
                "type": "LOAD_BALANCE",
                "title": "Isolate Bus Sections (Open Bus Coupler)",
                "message": f"Transformer T-4 is operating at a critical winding temperature of {round(t4_wti, 1)}°C under shared busbar loads. Open the Bus Coupler to isolate section A from section B, shifting section B loads to Transformer T-3.",
                "action": "open_breaker",
                "target": "bus_coupler"
            })

        return {
            "recommendations": recommendations,
            "schedule": self.schedule
        }


class DiagnosticAgent:
    def __init__(self):
        self.rag = SubstationRAG()

    def query(self, user_question):
        # 1. Search manuals
        matches = self.rag.search(user_question, top_k=2)
        
        if not matches:
            return "I couldn't find specific instructions in the manuals for your question. Please verify your query keywords (e.g. 'T-4 trip', 'DC Fail', 'P14-C1 overcurrent')."

        # 2. Format a professional diagnostic response
        response = f"### Substation Diagnostic System Analysis\n\n"
        response += f"Based on your query: *\"{user_question}\"*, I retrieved relevant documents from the electrical panel library:\n\n"
        
        for i, match in enumerate(matches):
            response += f"#### Source Document {i+1}: {match['source']} (Match Score: {match['score']})\n"
            response += f"```text\n{match['content']}\n```\n\n"
            
        response += "---\n"
        response += "#### Recommended Action Plan for Operator:\n"
        
        # Add quick summary steps depending on query keywords
        lower_q = user_question.lower()
        if "t-4" in lower_q or "transformer" in lower_q:
            response += "1. **Check Relay Display flags**: Verify if WTI (winding) or OTI (oil) or Buchholz trip is active.\n"
            response += "2. **Inspect Cooling Contactor**: Check if fans are running or if control fuses (F1-F4) in tap cabinet are blown.\n"
            response += "3. **Do not force close**: If a Buchholz trip is registered, test gas combustibility first; arcing might have occurred.\n"
            response += "4. **Acknowledge and Reset**: Clean alarms, rotate 86 Lockout switch back, and close the VCB."
        elif "dc fail" in lower_q or "battery" in lower_q:
            response += "1. **AC Input check**: Confirm AC incoming power to battery charger is ON (MCCB DB-2).\n"
            response += "2. **Fuse Check**: Test Battery Charger DC output fuses and battery link fuses (32A).\n"
            response += "3. **Ground Fault test**: Verify leakages on positive or negative lines at DCDB.\n"
            response += "4. **Trip Safely**: With DC failed, safety relays are DEAD. Trip breakers mechanically using front panel red push levers if load rises."
        elif "p14" in lower_q or "compressor" in lower_q:
            response += "1. **Log Current Peak**: Read Ia, Ib, Ic fault registers on protection relay CSAD-F-170.\n"
            response += "2. **Verify Load Friction**: Inspect compressor flywheel, verify it rotates freely.\n"
            response += "3. **Reset Relay**: Press reset button on CSAD relay face plate, reset 86 Lockout relay, check spring charged blue LED, then CLOSE."
        else:
            response += "1. Identify and isolate the tripped panel feeder circuit.\n2. Consult the specific manual text above for diagnostic values (trip limits, curves, fuse ratings).\n3. Clear the physical fault, reset the relay lockouts, verify spring charge, and re-close."
            
        return response
