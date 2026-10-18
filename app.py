"""
app.py
Interactive Streamlit Dashboard for FabAgent-MCP.
Visualizes digital fabrication pre-flight analysis, 3D mesh orientations,
MCP tool traces, and slicing profiles.
"""

import os
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import trimesh
from fab_agent import FabPreFlightAgent
from fab_mcp_server import FAB_MATERIALS_DB

st.set_page_config(
    page_title="FabAgent-MCP | Digital Fabrication Agent",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; }
    .subtitle { font-size: 1.05rem; color: #4B5563; margin-bottom: 25px; }
    .thought-card { background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
    .mcp-pill { background-color: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">FabAgent-MCP: Autonomous Digital Fabrication Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Model Context Protocol (MCP) powered pre-flight verification, 3D printing orientation optimization, and automated slicing profiles</p>', unsafe_allow_html=True)

# Sidebar
st.sidebar.header("Fabrication Job Setup")

current_dir = os.path.dirname(os.path.abspath(__file__))
default_mesh_path = os.path.join(current_dir, "sample_bracket.stl")

uploaded_file = st.sidebar.file_uploader("Upload 3D Model (STL)", type=["stl"])
if uploaded_file is not None:
    temp_path = os.path.join(current_dir, "user_upload.stl")
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    target_mesh = temp_path
else:
    target_mesh = default_mesh_path

material_choice = st.sidebar.selectbox("Fabrication Polymer", list(FAB_MATERIALS_DB.keys()), index=1)
infill_pct = st.sidebar.slider("Infill Density (%)", min_value=10, max_value=100, value=25, step=5)
max_time_hours = st.sidebar.slider("Max Allowed Duration (Hours)", min_value=1.0, max_value=8.0, value=3.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.markdown("### Polymer Specifications")
mat_spec = FAB_MATERIALS_DB[material_choice]
st.sidebar.write(f"- **Nozzle Temp:** {mat_spec['nozzle_temp_c']} C")
st.sidebar.write(f"- **Bed Temp:** {mat_spec['bed_temp_c']} C")
st.sidebar.write(f"- **Adhesion:** {mat_spec['bed_adhesion']}")
st.sidebar.caption(mat_spec["description"])

def create_3d_mesh_fig(mesh_path: str, title: str = "3D Build Plate Preview"):
    if not os.path.exists(mesh_path):
        return None
    mesh = trimesh.load(mesh_path)
    vertices = mesh.vertices
    faces = mesh.faces

    fig = go.Figure(data=[
        go.Mesh3d(
            x=vertices[:, 0],
            y=vertices[:, 1],
            z=vertices[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            color="#3B82F6",
            opacity=0.9,
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.2)
        )
    ])

    fig.update_layout(
        title=title,
        margin=dict(l=0, r=0, b=0, t=30),
        scene=dict(
            xaxis=dict(title='X (mm)', backgroundcolor="#F9FAFB"),
            yaxis=dict(title='Y (mm)', backgroundcolor="#F9FAFB"),
            zaxis=dict(title='Z (mm)', backgroundcolor="#F9FAFB"),
            aspectmode='data'
        ),
        height=480
    )
    return fig

# Run Button
if st.sidebar.button("Run Pre-Flight Agent", type="primary"):
    with st.spinner("Agent querying MCP tools and optimizing fabrication parameters..."):
        agent = FabPreFlightAgent()
        res = agent.run_fabrication_pipeline(
            mesh_path=target_mesh,
            material=material_choice,
            infill_pct=infill_pct,
            max_allowed_time_mins=max_time_hours * 60.0
        )
        st.session_state["fab_results"] = res
        st.session_state["fab_mesh"] = target_mesh

if "fab_results" in st.session_state:
    res = st.session_state["fab_results"]
    telemetry = res["fabrication_telemetry"]
    slicing = res["slicing_profile"]
    analysis = res["mesh_analysis"]

    # KPI Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Status", res["status"])
    with c2:
        st.metric("Estimated Time", telemetry["estimated_print_time"])
    with c3:
        st.metric("Filament Mass", f"{telemetry['filament_mass_grams']} g")
    with c4:
        st.metric("Job Cost", f"INR {telemetry['material_cost_inr']}")
    with c5:
        st.metric("Build Posture", res["recommended_orientation"])

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "3D Geometry & Overhangs",
        "Agent Reflection & MCP Trace",
        "Slicing & Thermal Profiles",
        "Fabrication Job Ticket"
    ])

    with tab1:
        st.subheader("3D Build Volume & Geometry Analysis")
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            fig = create_3d_mesh_fig(st.session_state["fab_mesh"])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with col_m2:
            st.markdown("#### Dimensional Attributes")
            bb = analysis["bounding_box_mm"]
            st.write(f"- **Bounding Box:** {bb['x']} x {bb['y']} x {bb['z']} mm")
            st.write(f"- **Displaced Volume:** {analysis['volume_cm3']} cm3")
            st.write(f"- **Overhang Area:** {analysis['overhang_area_mm2']} mm2 ({analysis['overhang_percentage']}%)")
            st.write(f"- **Support Structures Required:** {'Yes' if analysis['requires_supports'] else 'No'}")
            st.write(f"- **Manifold / Printable:** {'Yes' if analysis['is_printable'] else 'No'}")

    with tab2:
        st.subheader("Model Context Protocol (MCP) Execution Trace")
        for step in res["agent_trace"]:
            with st.expander(f"Step {step['step']}: Tool Call `{step['action']}`", expanded=True):
                st.markdown(f"<span class='mcp-pill'>MCP Tool</span> `{step['action']}`", unsafe_allow_html=True)
                st.markdown(f"**Agent Thought & Reasoning:**\n> {step['agent_thought']}")
                st.json(step["observation"])

    with tab3:
        st.subheader("Machine Slicing Parameters")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("#### Thermal & Speed Settings")
            st.write(f"- **Target Polymer:** {slicing['material']}")
            st.write(f"- **Extruder Temperature:** {slicing['nozzle_temperature_c']} C")
            st.write(f"- **Heatbed Temperature:** {slicing['bed_temperature_c']} C")
            st.write(f"- **Part Cooling Fan:** {slicing['cooling_fan_speed_pct']}%")
            st.write(f"- **Print Speed:** {slicing['print_speed_mm_s']} mm/s")
            st.write(f"- **Enclosure Mandatory:** {'Yes' if slicing['enclosure_required'] else 'No'}")

        with col_s2:
            st.markdown("#### Structural Infill Settings")
            st.write(f"- **Layer Resolution:** {slicing['layer_height_mm']} mm")
            st.write(f"- **Infill Density:** {slicing['infill_density_pct']}%")
            st.write(f"- **Infill Pattern:** {slicing['infill_pattern']}")
            st.write(f"- **Build Plate Adhesion:** {slicing['bed_adhesion_method']}")

    with tab4:
        st.subheader("Production Job Ticket Summary")
        st.code(f"""
; FABLAB PRODUCTION G-CODE JOB HEADER
; Generated by FabAgent-MCP
; -----------------------------------------
; Job Status: {res['status']}
; Material: {res['material']}
; Build Orientation: {res['recommended_orientation']}
; Estimated Print Time: {telemetry['estimated_print_time']}
; Filament Usage: {telemetry['filament_mass_grams']} g
; Calculated Job Cost: INR {telemetry['material_cost_inr']}
; M104 S{slicing['nozzle_temperature_c']} ; Set Extruder Temp
; M140 S{slicing['bed_temperature_c']} ; Set Bed Temp
; M109 S{slicing['nozzle_temperature_c']} ; Wait for Extruder Temp
; M190 S{slicing['bed_temperature_c']} ; Wait for Bed Temp
; G28 ; Home all axes
; G29 ; Mesh Bed Leveling
; -----------------------------------------
        """, language="gcode")
else:
    st.info("Select parameters in the sidebar and click 'Run Pre-Flight Agent' to begin.")
