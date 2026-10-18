"""
main.py
CLI test runner for FabAgent-MCP.
Demonstrates the end-to-end autonomous digital fabrication workflow.
"""

import os
from fab_agent import FabPreFlightAgent

def main():
    print("================================================================")
    print("      FabAgent-MCP: Autonomous Digital Fabrication Pipeline     ")
    print("================================================================\n")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    mesh_path = os.path.join(current_dir, "sample_bracket.stl")

    if not os.path.exists(mesh_path):
        print(f"Error: Mesh file not found at {mesh_path}")
        return

    agent = FabPreFlightAgent()
    
    print("Running autonomous pre-flight analysis for PETG FDM printing...")
    result = agent.run_fabrication_pipeline(
        mesh_path=mesh_path,
        material="PETG",
        infill_pct=30,
        max_allowed_time_mins=180.0
    )

    print("\n--- AGENT EXECUTION TRACE ---")
    for step in result["agent_trace"]:
        print(f"Step {step['step']} [{step['action']}]:")
        print(f"  Thought: {step['agent_thought']}\n")

    print("--- FINAL FABRICATION JOB TICKET ---")
    print(f"Status: {result['status']}")
    print(f"Material: {result['material']}")
    print(f"Recommended Build Posture: {result['recommended_orientation']}")
    print(f"Estimated Duration: {result['fabrication_telemetry']['estimated_print_time']}")
    print(f"Filament Consumed: {result['fabrication_telemetry']['filament_mass_grams']} g")
    print(f"Material Cost: INR {result['fabrication_telemetry']['material_cost_inr']}")
    print(f"Extruder Temperature: {result['slicing_profile']['nozzle_temperature_c']} C")
    print(f"Bed Temperature: {result['slicing_profile']['bed_temperature_c']} C")
    print(f"Infill Pattern: {result['slicing_profile']['infill_pattern']}")
    print("================================================================")

if __name__ == "__main__":
    main()
