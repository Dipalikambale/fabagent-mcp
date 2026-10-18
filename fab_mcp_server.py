"""
fab_mcp_server.py
Model Context Protocol (MCP) Server for Digital Fabrication Operations.
Standardizes tools for 3D mesh printability analysis, support-area
optimization, material-specific slicing profiles, and fabrication telemetry.
"""

import math
from typing import Dict, Any, List, Tuple
import numpy as np
import trimesh

# Material database for digital fabrication (FFF/FDM 3D printing)
FAB_MATERIALS_DB: Dict[str, Dict[str, Any]] = {
    "PLA": {
        "nozzle_temp_c": 210,
        "bed_temp_c": 60,
        "print_speed_mm_s": 60.0,
        "cooling_fan_pct": 100,
        "density_g_cm3": 1.24,
        "cost_per_kg_inr": 1200.0,
        "enclosure_required": False,
        "bed_adhesion": "PEI Sheet / Glue Stick",
        "description": "Standard prototyping polymer, low warping, excellent detail."
    },
    "PETG": {
        "nozzle_temp_c": 240,
        "bed_temp_c": 80,
        "print_speed_mm_s": 45.0,
        "cooling_fan_pct": 50,
        "density_g_cm3": 1.27,
        "cost_per_kg_inr": 1600.0,
        "enclosure_required": False,
        "bed_adhesion": "Textured PEI",
        "description": "High impact resistance and chemical durability for functional parts."
    },
    "ABS": {
        "nozzle_temp_c": 250,
        "bed_temp_c": 105,
        "print_speed_mm_s": 50.0,
        "cooling_fan_pct": 0,
        "density_g_cm3": 1.04,
        "cost_per_kg_inr": 1400.0,
        "enclosure_required": True,
        "bed_adhesion": "ABS Slurry / Smooth PEI",
        "description": "Heat resistant up to 100C, machinable, requires enclosure to prevent warping."
    },
    "TPU": {
        "nozzle_temp_c": 225,
        "bed_temp_c": 50,
        "print_speed_mm_s": 25.0,
        "cooling_fan_pct": 80,
        "density_g_cm3": 1.21,
        "cost_per_kg_inr": 2200.0,
        "enclosure_required": False,
        "bed_adhesion": "Blue Tape / Glass",
        "description": "Flexible elastomeric filament (Shore 95A) for gaskets, seals, and dampers."
    }
}


class FabLabMCPServer:
    """
    Standardized MCP Tool Server providing digital fabrication capabilities.
    """

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Returns JSON-RPC / MCP schema specifications for available tools.
        """
        return [
            {
                "name": "analyze_mesh_printability",
                "description": "Inspects 3D mesh for watertightness, manifold integrity, and critical overhang angles (>45 deg).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mesh_path": {"type": "string", "description": "Path to STL or OBJ mesh file"}
                    },
                    "required": ["mesh_path"]
                }
            },
            {
                "name": "optimize_part_orientation",
                "description": "Tests coordinate orientations to find the minimum support structure contact area.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mesh_path": {"type": "string", "description": "Path to STL mesh"}
                    },
                    "required": ["mesh_path"]
                }
            },
            {
                "name": "configure_slicing_parameters",
                "description": "Generates tuned slicing and thermal parameters based on selected fabrication material.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "material": {"type": "string", "enum": ["PLA", "PETG", "ABS", "TPU"]},
                        "infill_pct": {"type": "integer", "description": "Infill density from 10 to 100"},
                        "layer_height_mm": {"type": "number", "description": "Layer resolution in mm (e.g. 0.16, 0.2, 0.28)"}
                    },
                    "required": ["material"]
                }
            },
            {
                "name": "estimate_fabrication_telemetry",
                "description": "Calculates total print time, required filament mass (g), and material cost.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mesh_volume_cm3": {"type": "number"},
                        "support_volume_cm3": {"type": "number"},
                        "infill_pct": {"type": "integer"},
                        "material": {"type": "string"}
                    },
                    "required": ["mesh_volume_cm3", "support_volume_cm3", "infill_pct", "material"]
                }
            }
        ]

    # --- Tool Execution Implementations ---

    def analyze_mesh_printability(self, mesh_path: str) -> Dict[str, Any]:
        """
        Tool 1: Evaluates geometric printability, runs automated repair on unmerged
        boundaries, and calculates overhang angles against gravity vector.
        """
        mesh = trimesh.load(mesh_path)
        
        # Run automated mesh hygiene repairs
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_inversion(mesh)
        trimesh.repair.fill_holes(mesh)

        is_watertight = bool(mesh.is_watertight)
        is_printable = len(mesh.faces) > 4 and abs(float(mesh.volume)) > 1.0
        volume_cm3 = abs(float(mesh.volume)) * 1e-3  # mm3 to cm3
        extents_mm = [round(float(x), 2) for x in mesh.extents]

        # Overhang detection: Face normal vs build plate normal (0, 0, -1)
        # Overhangs steeper than 45 degrees require sacrificial support material
        face_normals = mesh.face_normals
        down_vector = np.array([0.0, 0.0, -1.0])
        dot_products = np.dot(face_normals, down_vector)

        # angle with horizontal plate: dot > sin(45 deg) = 0.707
        overhang_faces = dot_products > 0.707
        overhang_area_mm2 = float(np.sum(mesh.area_faces[overhang_faces]))
        total_area_mm2 = float(mesh.area)
        overhang_pct = round((overhang_area_mm2 / max(1.0, total_area_mm2)) * 100.0, 1)

        # Estimated support volume (approximate downward projection of overhangs)
        estimated_support_cm3 = round((overhang_area_mm2 * 0.2) * 1e-3, 2)

        return {
            "is_watertight": is_watertight,
            "is_printable": is_printable,
            "bounding_box_mm": {"x": extents_mm[0], "y": extents_mm[1], "z": extents_mm[2]},
            "volume_cm3": round(volume_cm3, 2),
            "overhang_area_mm2": round(overhang_area_mm2, 1),
            "overhang_percentage": overhang_pct,
            "requires_supports": overhang_pct > 3.0,
            "estimated_support_volume_cm3": estimated_support_cm3
        }

    def optimize_part_orientation(self, mesh_path: str) -> Dict[str, Any]:
        """
        Tool 2: Evaluates 6 primary canonical face-down rotations to minimize support area.
        """
        base_mesh = trimesh.load(mesh_path)
        rotations = [
            ("Original (0,0,0)", np.eye(4)),
            ("Rotate X 90 deg", trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])),
            ("Rotate X 180 deg", trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])),
            ("Rotate Y 90 deg", trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])),
            ("Rotate Y -90 deg", trimesh.transformations.rotation_matrix(-math.pi / 2, [0, 1, 0])),
            ("Rotate X -90 deg", trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
        ]

        best_label = "Original (0,0,0)"
        lowest_overhang_area = float("inf")
        best_transform = np.eye(4)
        down_vector = np.array([0.0, 0.0, -1.0])

        for label, transform in rotations:
            m_copy = base_mesh.copy()
            m_copy.apply_transform(transform)
            dots = np.dot(m_copy.face_normals, down_vector)
            overhangs = dots > 0.707
            area = float(np.sum(m_copy.area_faces[overhangs]))

            if area < lowest_overhang_area:
                lowest_overhang_area = area
                best_label = label
                best_transform = transform

        return {
            "recommended_orientation": best_label,
            "minimized_overhang_area_mm2": round(lowest_overhang_area, 1),
            "reduction_in_support_needed": lowest_overhang_area < 500.0,
            "transform_matrix": best_transform.tolist()
        }

    def configure_slicing_parameters(
        self,
        material: str = "PLA",
        infill_pct: int = 20,
        layer_height_mm: float = 0.20
    ) -> Dict[str, Any]:
        """
        Tool 3: Configures production slicer variables based on polymer properties.
        """
        mat = FAB_MATERIALS_DB.get(material.upper(), FAB_MATERIALS_DB["PLA"])

        return {
            "material": material.upper(),
            "nozzle_temperature_c": mat["nozzle_temp_c"],
            "bed_temperature_c": mat["bed_temp_c"],
            "cooling_fan_speed_pct": mat["cooling_fan_pct"],
            "print_speed_mm_s": mat["print_speed_mm_s"],
            "layer_height_mm": layer_height_mm,
            "infill_density_pct": infill_pct,
            "infill_pattern": "gyroid" if infill_pct >= 25 else "grid",
            "enclosure_required": mat["enclosure_required"],
            "bed_adhesion_method": mat["bed_adhesion"]
        }

    def estimate_fabrication_telemetry(
        self,
        mesh_volume_cm3: float,
        support_volume_cm3: float,
        infill_pct: int,
        material: str
    ) -> Dict[str, Any]:
        """
        Tool 4: Computes print duration, filament mass, and material consumption costs.
        """
        mat = FAB_MATERIALS_DB.get(material.upper(), FAB_MATERIALS_DB["PLA"])
        density = mat["density_g_cm3"]

        # Effective material volume: perimeter shells + infill + support material
        shell_vol = mesh_volume_cm3 * 0.35  # ~3 solid perimeters
        infill_vol = (mesh_volume_cm3 * 0.65) * (infill_pct / 100.0)
        total_plastic_vol_cm3 = shell_vol + infill_vol + support_volume_cm3

        # Mass in grams
        filament_mass_g = total_plastic_vol_cm3 * density

        # Printing duration estimation (Empirical FDM print speed model)
        extrusion_rate_cm3_per_min = 0.48
        estimated_minutes = total_plastic_vol_cm3 / extrusion_rate_cm3_per_min
        hours = math.floor(estimated_minutes / 60.0)
        mins = int(estimated_minutes % 60.0)

        # Cost in INR
        cost_inr = (filament_mass_g / 1000.0) * mat["cost_per_kg_inr"]

        return {
            "filament_mass_grams": round(filament_mass_g, 1),
            "estimated_print_time": f"{hours}h {mins}m",
            "print_time_minutes": round(estimated_minutes, 1),
            "material_cost_inr": round(cost_inr, 2)
        }
