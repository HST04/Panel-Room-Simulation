import os
import sys

# Ensure backend folder is in path
sys.path.append(os.path.dirname(__file__))

from simulator import SubstationSimulator
from rag_data import SubstationRAG

def test_telemetry_flow():
    print("Testing electrical load calculations...")
    sim = SubstationSimulator()
    
    # Enable P14-C1 breaker
    sim.set_breaker("p14_c1", "closed")
    sim.tick(1)
    
    state = sim.get_state()
    p14_c1 = state["panels"]["p14_c1"]
    
    # Check baseline currents are computed
    assert p14_c1["current"] > 25.0 and p14_c1["current"] < 40.0, f"Unexpected P14-C1 current: {p14_c1['current']}"
    assert p14_c1["active_power"] > 0, "Active power should be positive"
    
    # Check Incomer 1 & 2 currents are shared (coupler closed)
    inc1 = state["panels"]["incomer_01"]
    inc2 = state["panels"]["incomer_02"]
    assert inc1["current"] > 0, "Incomer 1 should draw current"
    assert inc2["current"] > 0, "Incomer 2 should draw current"
    print("Telemetry calculations OK!")

def test_overcurrent_trip():
    print("Testing overcurrent trip safety interlock...")
    sim = SubstationSimulator()
    sim.set_breaker("p14_c1", "closed")
    sim.inject_fault("p14_c1_spike", True)
    
    # Tick 4 seconds - warning should be active, but not tripped yet
    for _ in range(4):
        sim.tick(1)
    state = sim.get_state()
    assert state["panels"]["p14_c1"]["state"] == "closed"
    assert "OVERCURRENT ALERT" in state["panels"]["p14_c1"]["annunciator_alarms"]
    
    # Tick 5th second - breaker should trip!
    sim.tick(1)
    state = sim.get_state()
    assert state["panels"]["p14_c1"]["state"] == "tripped"
    assert "OVERCURRENT TRIP" in state["panels"]["p14_c1"]["annunciator_alarms"]
    print("Overcurrent safety trip interlock OK!")

def test_rag_retrieval():
    print("Testing RAG text search indexing...")
    rag = SubstationRAG()
    assert len(rag.chunks) > 0, "RAG should load chunks"
    
    # Search for T-4 trip winding
    res = rag.search("T-4 winding trip", top_k=1)
    assert len(res) > 0
    assert "T-4" in res[0]["source"] or "transformer" in res[0]["content"].lower()
    
    # Search for battery bank charging
    res2 = rag.search("battery charger fuse DC fail", top_k=1)
    assert len(res2) > 0
    assert "DC Fail" in res2[0]["source"] or "battery" in res2[0]["content"].lower()
    print("RAG search indexing OK!")

if __name__ == "__main__":
    print("==========================================")
    print("RUNNING AUTOMATED SUBSTATION SIMULATOR TESTS")
    print("==========================================")
    try:
        test_telemetry_flow()
        test_overcurrent_trip()
        test_rag_retrieval()
        print("\nAll automated verification tests PASSED successfully!")
    except AssertionError as e:
        print(f"\nAssertion Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during execution: {e}")
        sys.exit(1)
