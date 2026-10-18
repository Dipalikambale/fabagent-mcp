# FabAgent-MCP: Autonomous Digital Fabrication Pre-Flight and Slicing Optimization Agent

> An Agentic AI workflow utilizing Anthropic's Model Context Protocol (MCP) to automate 3D printing pre-flight analysis, build orientation optimization, thermal slicing configurations, and G-code production verification.

---

## Why This Project Matters
In digital fabrication labs (Fab Labs, makerspaces, rapid prototyping facilities), unoptimized 3D CAD files cause operational bottlenecks:
* Excessive sacrificial support material and surface scarring.
* Inappropriate thermal and speed parameters leading to warping or delamination.
* Inefficient build orientations multiplying print duration and plastic consumption.

**FabAgent-MCP** introduces an autonomous pre-flight agent that uses **Model Context Protocol (MCP)** tool servers to inspect geometries, evaluate overhang vectors, rotate parts to minimize support contact, and configure verified manufacturing job tickets.

---

## System Architecture

```
User Input: STL Model, Material (PETG/PLA/ABS), Infill %, Max Duration
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  FabPreFlightAgent                           │
│        (Multi-Step Reflection and Constraint Loop)           │
└──────────────┬────────────────────────────────▲──────────────┘
               │ JSON-RPC / MCP Protocol        │ Tool Telemetry
               ▼                                │
┌──────────────────────────────────────────────────────────────┐
│                    FabLabMCPServer                           │
│                                                              │
│  Tool 1: analyze_mesh_printability                           │
│  - Checks watertightness and manifold geometry              │
│  - Integrates overhang faces steeper than 45 degrees         │
│                                                              │
│  Tool 2: optimize_part_orientation                           │
│  - Evaluates coordinate rotations against gravity vector     │
│  - Minimizes projected support structure contact area        │
│                                                              │
│  Tool 3: configure_slicing_parameters                        │
│  - Sets nozzle/bed temperatures, fan speeds, infill pattern   │
│                                                              │
│  Tool 4: estimate_fabrication_telemetry                      │
│  - Computes filament mass (g), duration, and job cost        │
└──────────────────────────────────────────────────────────────┘
```

---

## Model Context Protocol (MCP) Tools Implemented
1. **`analyze_mesh_printability`**: Evaluates geometric manifoldness, displacement volume, and calculates surface overhang area ($>45^\circ$).
2. **`optimize_part_orientation`**: Computes build posture transforms that yield the lowest downward-facing overhang area.
3. **`configure_slicing_parameters`**: Maps target polymer properties (PLA, PETG, ABS, TPU) to calibrated nozzle temperatures, heatbed temperatures, cooling fan percentages, and infill patterns.
4. **`estimate_fabrication_telemetry`**: Employs an empirical volumetric extrusion model to calculate filament mass ($g$), print duration, and material cost.

---

## Quickstart Guide

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/Dipalikambale/fabagent-mcp.git
cd fabagent-mcp
pip install -r requirements.txt
```

### 2. Run CLI Pipeline
```bash
python main.py
```

### 3. Launch Interactive Web Dashboard
```bash
streamlit run app.py
```
Open `http://localhost:8501` to:
* Upload any 3D STL mesh.
* Inspect dimensional attributes and critical overhang percentages.
* Review the step-by-step MCP execution trace.
* Generate production G-code initialization routines.

---

## Repository Structure
```
fabagent-mcp/
├── app.py              # Interactive Streamlit Web Dashboard
├── fab_agent.py        # Agentic pre-flight controller with reflection logic
├── fab_mcp_server.py   # Model Context Protocol (MCP) digital fabrication tool server
├── main.py             # CLI test runner
├── sample_bracket.stl  # Sample 3D mechanical model
├── requirements.txt    # Open-source dependencies
└── README.md           # Engineering documentation
```
