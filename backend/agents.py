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


import os
from dotenv import load_dotenv
import google.generativeai as genai

class DiagnosticAgent:
    def __init__(self):
        self.rag = SubstationRAG()
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key != "INSERT_YOUR_GEMINI_API_KEY_HERE":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.model = None

    def query(self, user_question):
        # 1. Search manuals via ChromaDB
        matches = self.rag.search(user_question, top_k=2)
        
        if not matches:
            return "I couldn't find specific instructions in the manuals for your question. Please verify your query keywords (e.g. 'T-4 trip', 'DC Fail', 'P14-C1 overcurrent')."

        # 2. Build context from retrieved documents
        context_text = "\n\n".join([
            f"--- Source: {m['source']} ---\n{m['content']}" for m in matches
        ])

        if not self.model:
            # Fallback if API key is not configured
            return f"**[GEMINI API KEY MISSING]** Please add your GEMINI_API_KEY to backend/.env.\n\nRetrieved Context:\n{context_text}"

        # 3. Call Gemini
        prompt = f"""
You are the Substation Diagnostic RAG Agent for an 11kV electrical panel room.
Use the following context from technical manuals to answer the user's question. Provide a professional, concise, and structured recommended action plan for the operator. If the context does not contain the answer, say you don't know based on the manuals.

Context:
{context_text}

Operator Question: {user_question}
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error contacting Gemini API: {str(e)}"
