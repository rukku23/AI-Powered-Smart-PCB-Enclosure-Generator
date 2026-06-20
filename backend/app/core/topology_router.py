"""
EnclosureAI — Topology Router (Phase 9)

Routes strategy names to their respective procedural OpenSCAD generator functions.
"""

from app.core.topology_generators import (
    generate_rectangular_scad,
    generate_chimney_scad,
    generate_dinrail_scad,
    generate_wearable_scad,
    generate_clamshell_scad,
)

def route_topology(strategy_name: str, params: dict) -> str:
    """
    Given a strategy name and deterministic constraints, returns
    the fully generated base OpenSCAD string.
    """
    generators = {
        "CHIMNEY_THERMAL":        generate_chimney_scad,
        "DIN_RAIL_CLIP":          generate_dinrail_scad,
        "WEARABLE_ROUNDED":       generate_wearable_scad,
        "CLAMSHELL_HORIZONTAL":   generate_clamshell_scad,
        "RECTANGULAR_FLAT_LID":   generate_rectangular_scad,
        "RECTANGULAR_RIBBED":     generate_rectangular_scad,
        "SEALED_IP_RATED":        generate_rectangular_scad,
        "CLAMSHELL_HINGED":       generate_clamshell_scad,
        "SEALED_OUTDOOR":         generate_rectangular_scad,
    }
    
    generator_fn = generators.get(strategy_name, generate_rectangular_scad)
    return generator_fn(params)
