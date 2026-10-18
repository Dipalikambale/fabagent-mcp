"""
fab_agent.py
Agentic Controller executing multi-step pre-flight verification, orientation
correction, and slicing generation for digital fabrication.
"""

from typing import Dict, Any, List
from fab_mcp_server import FabLabMCPServer


class FabPreFlightAgent:
    """
    Autonomous Fab Lab Pre-Flight Agent.
    Interacts with the FabLabMCPServer via MCP tool calls.
    """
    def __init__(self):
        self.mcp = FabLabMCPServer()

    def run_fabrication_pipeline(
        self,
        mesh_path: str,
        material: str = "PETG",
        infill_pct: int = 25,
        max_allowed_time_mins: float = 180.0
    ) -> Dict[str, Any]:
        """
        Executes the closed-loop agentic pre-flight preparation.
        """
        trace: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # STEP 1: Tool Call - Geometric Printability Analysis
        # -------------------------------------------------------------
        analysis = self.mcp.analyze_mesh_printability(mesh_path)
        trace.append({
            "step": 1,
            "action": "analyze_mesh_printability",
            "observation": analysis,
            "agent_thought": (
                f"Mesh is {'ready for fabrication' if analysis['is_printable'] else 'EMPTY/CORRUPT (ERROR)'}. "
                f"Watertight={analysis['is_watertight']}. "
                f"Detected {analysis['overhang_percentage']}% overhang area requiring support structures."
            )
        })

        if not analysis["is_printable"]:
            return {
                "status": "FAILED",
                "reason": "Geometry has zero volume or unrepairable non-manifold faces.",
                "agent_trace": trace
            }

        # -------------------------------------------------------------
        # STEP 2: Agent Reflection & Tool Call - Orientation Optimization
        # -------------------------------------------------------------
        current_support_vol = analysis["estimated_support_volume_cm3"]
        best_orientation_label = "Original (0,0,0)"

        if analysis["overhang_percentage"] > 8.0:
            agent_reflection = (
                f"High support requirement detected ({analysis['overhang_percentage']}%). "
                "Invoking optimize_part_orientation tool to minimize support scarring and waste."
            )
            orientation_res = self.mcp.optimize_part_orientation(mesh_path)
            best_orientation_label = orientation_res["recommended_orientation"]
            
            trace.append({
                "step": 2,
                "action": "optimize_part_orientation",
                "observation": orientation_res,
                "agent_thought": (
                    f"{agent_reflection} Recommended reorientation: '{best_orientation_label}'. "
                    f"Reduced critical overhang contact to {orientation_res['minimized_overhang_area_mm2']} mm2."
                )
            })

            # Update support estimate with optimized orientation
            current_support_vol = round(orientation_res["minimized_overhang_area_mm2"] * 0.2 * 1e-3, 2)
        else:
            trace.append({
                "step": 2,
                "action": "evaluate_orientation",
                "observation": "Orientation is already optimal.",
                "agent_thought": "Overhang area is under acceptable threshold (<8%). Retaining original build posture."
            })

        # -------------------------------------------------------------
        # STEP 3: Tool Call - Configure Slicing Profile
        # -------------------------------------------------------------
        selected_layer_height = 0.20
        slicing_profile = self.mcp.configure_slicing_parameters(
            material=material,
            infill_pct=infill_pct,
            layer_height_mm=selected_layer_height
        )
        trace.append({
            "step": 3,
            "action": "configure_slicing_parameters",
            "observation": slicing_profile,
            "agent_thought": (
                f"Configured thermal profile for {material}: Nozzle={slicing_profile['nozzle_temperature_c']}C, "
                f"Bed={slicing_profile['bed_temperature_c']}C, Infill Pattern={slicing_profile['infill_pattern']}."
            )
        })

        # -------------------------------------------------------------
        # STEP 4: Tool Call - Fabrication Telemetry & Constraint Check
        # -------------------------------------------------------------
        telemetry = self.mcp.estimate_fabrication_telemetry(
            mesh_volume_cm3=analysis["volume_cm3"],
            support_volume_cm3=current_support_vol,
            infill_pct=infill_pct,
            material=material
        )

        # Check production constraints (e.g. print time limits)
        within_time_limit = telemetry["print_time_minutes"] <= max_allowed_time_mins

        # Self-correction if time limit is exceeded: adaptive draft slicing
        if not within_time_limit and selected_layer_height < 0.28:
            agent_reflection = (
                f"Print time ({telemetry['estimated_print_time']}) exceeds target {max_allowed_time_mins} mins. "
                "Switching layer resolution from 0.20mm to 0.28mm (Draft Mode) to accelerate throughput."
            )
            selected_layer_height = 0.28
            slicing_profile = self.mcp.configure_slicing_parameters(
                material=material,
                infill_pct=max(15, infill_pct - 5),
                layer_height_mm=selected_layer_height
            )
            # Re-estimate with faster speed
            telemetry["print_time_minutes"] = round(telemetry["print_time_minutes"] * 0.72, 1)
            h = int(telemetry["print_time_minutes"] // 60)
            m = int(telemetry["print_time_minutes"] % 60)
            telemetry["estimated_print_time"] = f"{h}h {m}m"
            within_time_limit = telemetry["print_time_minutes"] <= max_allowed_time_mins

            trace.append({
                "step": 4,
                "action": "self_correct_slicing_resolution",
                "observation": telemetry,
                "agent_thought": agent_reflection
            })
        else:
            trace.append({
                "step": 4,
                "action": "estimate_fabrication_telemetry",
                "observation": telemetry,
                "agent_thought": (
                    f"Estimated print time: {telemetry['estimated_print_time']} ({telemetry['filament_mass_grams']}g plastic). "
                    f"Cost: INR {telemetry['material_cost_inr']}. "
                    f"Meets time constraint ({max_allowed_time_mins} min limit): {within_time_limit}."
                )
            })

        # -------------------------------------------------------------
        # STEP 5: Final Production Job Package
        # -------------------------------------------------------------
        job_package = {
            "status": "APPROVED_FOR_PRODUCTION" if within_time_limit else "TIME_LIMIT_EXCEEDED",
            "material": material,
            "recommended_orientation": best_orientation_label,
            "mesh_analysis": analysis,
            "slicing_profile": slicing_profile,
            "fabrication_telemetry": telemetry,
            "agent_trace": trace
        }

        return job_package
