"""
EnclosureAI — Constraint Engine
CRITICAL: All deterministic geometry math lives here.

The LLM never computes dimensions — only this engine does.
Every numeric value in the generated OpenSCAD code originates from
the ConstraintSchema produced by this engine.

Architecture: EnclosureRequest → ConstraintEngine.compute() → ConstraintSchema → LLM Prompt

Sub-functions:
  1. compute_outer_dimensions — outer/inner box dimensions
  2. compute_standoffs       — PCB mounting standoff positions
  3. compute_cutouts         — connector cutout face positions
  4. compute_thermal_zones   — thermal vent zones for hot components
  5. compute_snap_fit        — snap-fit tab positions around perimeter
"""

from __future__ import annotations

import math
from typing import Optional

from app.core.constants import (
    PCB_TO_WALL_CLEARANCE,
    STANDOFF_CORNER_OFFSET,
    CONNECTOR_CUTOUT_MARGIN,
    THERMAL_VENT_MIN_WATTAGE,
    THERMAL_VENT_RADIUS,
    NATURAL_CONVECTION_H,
    DELTA_T,
    SNAP_FIT_TAB_SPACING,
    SNAP_FIT_MIN_TABS,
    DFM_RULES,
)
from app.schemas.input_schemas import (
    EnclosureRequest,
    PCBSpec,
    ComponentSpec,
    FaceAccess,
    LidStyle,
    PRESETS,
)
from app.schemas.constraint_schemas import (
    ConstraintSchema,
    EnclosureDimensions,
    StandoffSpec,
    CutoutSpec,
    ThermalZone,
    SnapFitSpec,
    VentSpec,
)


class ConstraintEngine:
    """
    Deterministic constraint computation engine.
    
    Computes all geometric, standoff, cutout, thermal zone, and snap-fit
    parameters from PCB specifications and material constraints.
    
    Every value produced here is exact — the LLM uses these numbers
    verbatim in the OpenSCAD code it writes.
    """

    def compute(self, request: EnclosureRequest) -> ConstraintSchema:
        """
        Primary entry point. Transforms an EnclosureRequest into a fully
        validated ConstraintSchema with all dimensions pre-computed.
        
        If a preset is specified, merges preset values into the request.
        """
        # Resolve preset if specified
        request = self._resolve_preset(request)

        material = request.material.value
        components = request.components

        # Compute max component height
        max_component_height = (
            max(c.height for c in components) if components else 15.0
        )

        # Total board wattage
        total_wattage = sum(c.wattage for c in components)

        # 1. Outer dimensions
        enclosure = self.compute_outer_dimensions(
            request.pcb, material, components
        )

        # 2. Standoffs
        standoffs = self.compute_standoffs(request.pcb, enclosure)

        # 3. Cutouts
        standoff_height = standoffs[0].height if standoffs else 5.0
        cutouts = self.compute_cutouts(
            components, enclosure, request.pcb, standoff_height
        )

        # 4. Thermal zones
        thermal_zones = self.compute_thermal_zones(
            components, enclosure
        )

        # 5. Snap-fit (only if lid_style is SNAP_FIT)
        snap_fit: Optional[SnapFitSpec] = None
        if request.lid_style == LidStyle.SNAP_FIT:
            snap_fit = self.compute_snap_fit(enclosure, material)

        # 6. Vent spec (computed by thermal engine — placeholder here)
        vent_spec: Optional[VentSpec] = None

        return ConstraintSchema(
            pcb=request.pcb,
            enclosure=enclosure,
            standoffs=standoffs,
            cutouts=cutouts,
            thermal_zones=thermal_zones,
            snap_fit=snap_fit,
            vent_spec=vent_spec,
            material=material,
            print_technology=request.print_technology.value,
            lid_style=request.lid_style.value,
            total_wattage=total_wattage,
            max_component_height=max_component_height,
            ventilation_enabled=request.ventilation,
        )

    # ───────────────────────────────────────────────────────────
    # 1. Outer Dimensions
    # ───────────────────────────────────────────────────────────

    def compute_outer_dimensions(
        self,
        pcb: PCBSpec,
        material: str,
        components: list[ComponentSpec],
    ) -> EnclosureDimensions:
        """
        Compute enclosure outer and inner dimensions from PCB specs.
        
        Formula:
          wall = max(DFM_RULES[material]["min_wall_thickness"], 1.2)
          clearance = PCB_TO_WALL_CLEARANCE (3.0mm)
          outer_length = pcb.length + 2*clearance + 2*wall
          outer_width  = pcb.width  + 2*clearance + 2*wall
          outer_height = pcb.thickness + max_comp_height + clearance + wall + lid_thickness
        """
        rules = DFM_RULES.get(material, DFM_RULES["PETG"])
        wall = max(rules["min_wall_thickness"], 1.2)
        clearance = PCB_TO_WALL_CLEARANCE

        max_component_height = (
            max(c.height for c in components) if components else 15.0
        )

        lid_thickness = round(wall * 1.2, 2)

        outer_length = pcb.length + (2 * clearance) + (2 * wall)
        outer_width = pcb.width + (2 * clearance) + (2 * wall)
        outer_height = (
            pcb.thickness
            + max_component_height
            + clearance
            + wall
            + lid_thickness
        )

        inner_length = outer_length - (2 * wall)
        inner_width = outer_width - (2 * wall)
        inner_height = outer_height - wall - lid_thickness

        return EnclosureDimensions(
            outer_length=round(outer_length, 2),
            outer_width=round(outer_width, 2),
            outer_height=round(outer_height, 2),
            wall=round(wall, 2),
            clearance=clearance,
            lid_thickness=round(lid_thickness, 2),
            inner_length=round(inner_length, 2),
            inner_width=round(inner_width, 2),
            inner_height=round(inner_height, 2),
        )

    # ───────────────────────────────────────────────────────────
    # 2. Standoffs
    # ───────────────────────────────────────────────────────────

    def compute_standoffs(
        self,
        pcb: PCBSpec,
        enclosure: EnclosureDimensions,
    ) -> list[StandoffSpec]:
        """
        Compute standoff positions in enclosure coordinate space.
        
        - If pcb.mounting_hole_positions provided: use those
        - Else: auto-generate 4 corners at STANDOFF_CORNER_OFFSET inset
        - Translate PCB coordinates → enclosure coordinates (add clearance + wall)
        """
        # Determine fastener type
        fastener_type = "M3" if pcb.mounting_hole_diameter >= 3.2 else "M2"
        inner_diameter = pcb.mounting_hole_diameter
        outer_diameter = inner_diameter * 2
        height = 5.0 if fastener_type == "M3" else 4.0

        # Get PCB-space hole positions
        if pcb.mounting_hole_positions:
            pcb_positions = pcb.mounting_hole_positions
        else:
            # Auto-generate 4 corners with STANDOFF_CORNER_OFFSET inset
            offset = STANDOFF_CORNER_OFFSET
            pcb_positions = [
                (offset, offset),
                (pcb.length - offset, offset),
                (offset, pcb.width - offset),
                (pcb.length - offset, pcb.width - offset),
            ]

        # Translate PCB coords → enclosure coords
        x_offset = enclosure.clearance + enclosure.wall
        y_offset = enclosure.clearance + enclosure.wall

        standoffs = []
        for px, py in pcb_positions:
            standoffs.append(StandoffSpec(
                x=round(px + x_offset, 2),
                y=round(py + y_offset, 2),
                inner_diameter=inner_diameter,
                outer_diameter=round(outer_diameter, 2),
                height=height,
                fastener_type=fastener_type,
            ))

        return standoffs

    # ───────────────────────────────────────────────────────────
    # 3. Cutouts
    # ───────────────────────────────────────────────────────────

    def compute_cutouts(
        self,
        components: list[ComponentSpec],
        enclosure: EnclosureDimensions,
        pcb: PCBSpec,
        standoff_height: float,
    ) -> list[CutoutSpec]:
        """
        Compute connector cutout positions on enclosure faces.
        
        For each component with face_access != NONE:
          - Map component PCB position → enclosure face position
          - Width = connector_width + 2 * CONNECTOR_CUTOUT_MARGIN
          - Height = connector_height + 2 * CONNECTOR_CUTOUT_MARGIN  
          - z_start based on standoff height + PCB thickness
        """
        cutouts = []
        margin = CONNECTOR_CUTOUT_MARGIN
        wall = enclosure.wall

        for comp in components:
            if comp.face_access == FaceAccess.NONE:
                continue

            face = comp.face_access.value

            # Determine cutout width and height
            cw = (comp.connector_width or comp.height) + (2 * margin)
            ch = (comp.connector_height or comp.height) + (2 * margin)

            # Z position: wall (bottom) + standoff + PCB thickness
            # Centre the cutout around the component height
            z_base = wall + standoff_height + pcb.thickness
            z_start = z_base - margin
            z_end = z_base + (comp.connector_height or comp.height) + margin

            # Clamp z values to enclosure bounds
            z_start = max(0, z_start)
            z_end = min(enclosure.outer_height, z_end)

            # Compute x_start/x_end based on face orientation
            if face in ("FRONT", "BACK"):
                # X runs along enclosure length
                comp_enc_x = comp.position_x + enclosure.clearance + wall
                x_start = comp_enc_x - cw / 2
                x_end = comp_enc_x + cw / 2

                # Clamp to face width (outer_length)
                x_start = max(0, x_start)
                x_end = min(enclosure.outer_length, x_end)

            elif face in ("LEFT", "RIGHT"):
                # X runs along enclosure width
                comp_enc_y = comp.position_y + enclosure.clearance + wall
                x_start = comp_enc_y - cw / 2
                x_end = comp_enc_y + cw / 2

                x_start = max(0, x_start)
                x_end = min(enclosure.outer_width, x_end)

            elif face == "TOP":
                # X runs along length, z is depth into the top face
                comp_enc_x = comp.position_x + enclosure.clearance + wall
                x_start = comp_enc_x - cw / 2
                x_end = comp_enc_x + cw / 2

                # For top cutouts, z represents y-axis position
                comp_enc_y = comp.position_y + enclosure.clearance + wall
                z_start = comp_enc_y - ch / 2
                z_end = comp_enc_y + ch / 2

                x_start = max(0, x_start)
                x_end = min(enclosure.outer_length, x_end)
                z_start = max(0, z_start)
                z_end = min(enclosure.outer_width, z_end)
            else:
                continue

            cutouts.append(CutoutSpec(
                face=face,
                x_start=round(x_start, 2),
                x_end=round(x_end, 2),
                z_start=round(z_start, 2),
                z_end=round(z_end, 2),
                label=comp.label,
                component_type=comp.component_type.value,
            ))

        return cutouts

    # ───────────────────────────────────────────────────────────
    # 4. Thermal Zones
    # ───────────────────────────────────────────────────────────

    def compute_thermal_zones(
        self,
        components: list[ComponentSpec],
        enclosure: EnclosureDimensions,
    ) -> list[ThermalZone]:
        """
        Compute thermal vent zones for high-wattage components.
        
        - Filter: wattage >= THERMAL_VENT_MIN_WATTAGE (1.0W)
        - Map PCB coords → enclosure coords
        - Sort by wattage descending (priority)
        - All zones default to TOP face (hot air rises)
        """
        zones = []
        for comp in components:
            if comp.wattage < THERMAL_VENT_MIN_WATTAGE:
                continue

            # Map PCB coordinates to enclosure coordinates
            enc_x = comp.position_x + enclosure.clearance + enclosure.wall
            enc_y = comp.position_y + enclosure.clearance + enclosure.wall

            # Required vent area for this component (m²)
            required_area = comp.wattage / (NATURAL_CONVECTION_H * DELTA_T)

            zones.append(ThermalZone(
                centre_x=round(enc_x, 2),
                centre_y=round(enc_y, 2),
                radius=THERMAL_VENT_RADIUS,
                face="TOP",
                priority=comp.wattage,
                required_vent_area=round(required_area, 6),
            ))

        # Sort by priority (wattage) descending
        zones.sort(key=lambda z: z.priority, reverse=True)
        return zones

    # ───────────────────────────────────────────────────────────
    # 5. Snap-Fit
    # ───────────────────────────────────────────────────────────

    def compute_snap_fit(
        self,
        enclosure: EnclosureDimensions,
        material: str,
    ) -> SnapFitSpec:
        """
        Compute snap-fit tab positions distributed uniformly around perimeter.
        
        - perimeter = 2 * (outer_length + outer_width)
        - tab_count = max(SNAP_FIT_MIN_TABS, floor(perimeter / SNAP_FIT_TAB_SPACING))
        - cantilever_length = max(DFM_RULES[material]["snap_fit_min_length"], 15.0)
        - gap = cantilever_length * DFM_RULES[material]["snap_fit_gap_per_mm"]
        - Distribute tabs uniformly around perimeter
        """
        rules = DFM_RULES.get(material, DFM_RULES["PETG"])
        
        perimeter = 2 * (enclosure.outer_length + enclosure.outer_width)
        tab_count = max(SNAP_FIT_MIN_TABS, math.floor(perimeter / SNAP_FIT_TAB_SPACING))
        cantilever_length = max(rules["snap_fit_min_length"], 15.0)
        gap = round(cantilever_length * rules["snap_fit_gap_per_mm"], 2)

        # Distribute tabs uniformly around perimeter
        positions = self._distribute_tabs_around_perimeter(
            tab_count, enclosure.outer_length, enclosure.outer_width
        )

        return SnapFitSpec(
            tab_count=tab_count,
            cantilever_length=cantilever_length,
            gap=gap,
            positions=positions,
        )

    # ───────────────────────────────────────────────────────────
    # Internal helpers
    # ───────────────────────────────────────────────────────────

    def _resolve_preset(self, request: EnclosureRequest) -> EnclosureRequest:
        """Merge preset values into the request if preset is specified."""
        if not request.preset:
            return request

        preset_key = request.preset.upper()
        if preset_key not in PRESETS:
            return request

        preset_data = PRESETS[preset_key]
        
        # Build merged request
        merged = request.model_copy(update={
            "pcb": PCBSpec(**preset_data["pcb"]),
            "components": [
                ComponentSpec(**comp)
                for comp in preset_data.get("components", [])
            ],
        })
        return merged

    def _distribute_tabs_around_perimeter(
        self,
        tab_count: int,
        outer_length: float,
        outer_width: float,
    ) -> list[dict]:
        """
        Distribute snap-fit tabs uniformly around the rectangular perimeter.
        
        Walks the perimeter: FRONT → RIGHT → BACK → LEFT
        Returns list of {face, offset_from_start} dicts.
        """
        perimeter = 2 * (outer_length + outer_width)
        spacing = perimeter / tab_count

        # Define face edges in order: FRONT, RIGHT, BACK, LEFT
        faces = [
            ("FRONT", outer_length),
            ("RIGHT", outer_width),
            ("BACK", outer_length),
            ("LEFT", outer_width),
        ]

        positions = []
        for i in range(tab_count):
            distance = (i + 0.5) * spacing  # Centre each tab in its segment
            
            # Walk the perimeter to find which face this distance falls on
            cumulative = 0.0
            for face_name, face_length in faces:
                if distance < cumulative + face_length:
                    offset = distance - cumulative
                    positions.append({
                        "face": face_name,
                        "offset_from_start": round(offset, 2),
                    })
                    break
                cumulative += face_length
            else:
                # Wrap around to first face
                offset = distance - cumulative
                positions.append({
                    "face": "FRONT",
                    "offset_from_start": round(offset, 2),
                })

        return positions
