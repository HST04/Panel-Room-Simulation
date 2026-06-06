import asyncio
import os
import sys

# Ensure backend directory is in python module search path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from simulator import SubstationSimulator
from agents import AnomalyAgent, OptimizationAgent, DiagnosticAgent

app = FastAPI(title="Agentic Substation Digital Twin API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins in local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
simulator = SubstationSimulator()
anomaly_agent = AnomalyAgent()
optimization_agent = OptimizationAgent()
diagnostic_agent = DiagnosticAgent()

# Background task for real-time simulation ticking
async def simulation_loop():
    while True:
        try:
            simulator.tick(1)
        except Exception as e:
            print(f"Error in simulator tick: {e}")
        await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    # Start background task
    asyncio.create_task(simulation_loop())

# Request Models
class BreakerControlRequest(BaseModel):
    panel_id: str
    state: str # closed, open, tripped, manual_open, manual_closed

class FaultInjectionRequest(BaseModel):
    fault_name: str
    enable: bool

class TapRequest(BaseModel):
    direction: str # up, down, reset

class ChatRequest(BaseModel):
    message: str

class PanelResetRequest(BaseModel):
    panel_id: str

@app.get("/api/state")
def get_state():
    # Get current electrical metrics
    sim_state = simulator.get_state()
    
    # Run Agents on the current state
    active_alerts = anomaly_agent.analyze(sim_state)
    optimization_data = optimization_agent.analyze(sim_state)
    
    # Merge agents data into response
    response = {
        "simulator": sim_state,
        "agents": {
            "alerts": active_alerts,
            "recommendations": optimization_data["recommendations"],
            "schedule": optimization_data["schedule"]
        }
    }
    return response

@app.post("/api/breaker")
def control_breaker(req: BreakerControlRequest):
    success = simulator.set_breaker(req.panel_id, req.state)
    if not success:
        # Check if DC fail is the cause
        if simulator.faults["dc_fail"] and not req.state.startswith("manual_"):
            raise HTTPException(
                status_code=400, 
                detail="DC FAIL: Control electrical power lost. Breakers cannot be operated electrically. Use mechanical hand-trip override."
            )
        raise HTTPException(
            status_code=400, 
            detail="Action rejected by interlocks or panel in tripped state. Clear and Reset panel first."
        )
    return {"status": "success", "panel_id": req.panel_id, "state": req.state}

@app.post("/api/reset")
def reset_panel(req: PanelResetRequest):
    success = simulator.reset_panel_alarms(req.panel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Panel ID not found")
    return {"status": "success", "panel_id": req.panel_id}

@app.post("/api/fault")
def toggle_fault(req: FaultInjectionRequest):
    success = simulator.inject_fault(req.fault_name, req.enable)
    if not success:
        raise HTTPException(status_code=404, detail="Fault type not recognized")
    return {"status": "success", "fault_name": req.fault_name, "enabled": req.enable}

@app.post("/api/tap")
def adjust_tap(req: TapRequest):
    if req.direction == "up":
        if simulator.tap_position < 5:
            simulator.tap_position += 1
    elif req.direction == "down":
        if simulator.tap_position > -5:
            simulator.tap_position -= 1
    elif req.direction == "reset":
        simulator.tap_position = 0
    else:
        raise HTTPException(status_code=400, detail="Invalid tap direction")
        
    return {"status": "success", "tap_position": simulator.tap_position}

@app.post("/api/solar-mode")
def toggle_solar_mode(req: BaseModel):
    simulator.solar_auto = not simulator.solar_auto
    return {"status": "success", "solar_auto": simulator.solar_auto}

@app.post("/api/chat")
def diagnostic_chat(req: ChatRequest):
    answer = diagnostic_agent.query(req.message)
    return {"status": "success", "response": answer}

@app.post("/api/optimize")
def apply_optimization(req: BreakerControlRequest):
    # Triggers recommendation action (e.g. engage capacitor bank)
    success = simulator.set_breaker(req.panel_id, req.state)
    if not success:
         raise HTTPException(status_code=400, detail="Failed to apply optimization recommendation.")
    return {"status": "success", "action_applied": req.state, "panel": req.panel_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
