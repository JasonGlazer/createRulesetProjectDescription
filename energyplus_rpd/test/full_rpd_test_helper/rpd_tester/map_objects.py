from energyplus_rpd.test.full_rpd_test_helper.rpd_tester.utils import (
    find_one,
    find_all,
    find_all_with_filters,
    find_all_with_field_value,
    get_zones_from_json,
    get_dict_of_surfaces_with_construction_assigned,
    get_dict_of_zones_and_terminals_served_by_hvac_sys,
    compare_attributes,
    find_best_match
)


def get_mapping(
    match_type,
    generated_values,
    reference_values,
    generated_zone_id=None,
    reference_zone_id=None,
    object_id_map=None,
):
    """Find matches for a key in the generated and reference JSON based on the json path in the spec."""

    if len(generated_values) != len(reference_values):
        print(
            f"{match_type} count mismatch. Expected: {len(reference_values)}; "
            f"got: {len(generated_values)}. Verify the object mapping."
        )
    mapping = {}
    if match_type == "Constructions":
        mapping = match_constructions_by_surfaces_assigned(
            generated_values, reference_values, object_id_map
        )

    elif match_type == "Materials":
        mapping = match_by_attributes_with_excess_generated(
            generated_values,
            reference_values,
            attrs=["thickness", "conductivity", "density", "specific_heat", "r_value"],
        )

    elif match_type == "Surfaces":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["area", "azimuth"],
        )

    elif match_type == "Subsurfaces":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["area", "azimuth", "classification"],
        )

    elif match_type == "HVAC Systems":
        mapping = match_sys_by_zones_served(
            generated_values, reference_values, object_id_map
        )
        if not mapping:
            mapping = match_by_attributes(
                generated_values,
                reference_values,
                generated_zone_id,
                reference_zone_id,
                ["cooling_system.type", "heating_system.type"],
            )

    elif match_type == "Terminals":
        mapping = match_terminals_by_references(
            generated_values, reference_values, object_id_map
        )

    elif match_type == "Boilers":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["draft_type", "energy_source_type"],
        )

    elif match_type == "Chillers":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["compressor_type", "energy_source_type"],
        )

    elif match_type == "Heat Rejections":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["type", "fan_type", "fan_speed_control"],
        )

    elif match_type == "Loops":
        mapping = match_by_attributes(
            generated_values,
            reference_values,
            generated_zone_id,
            reference_zone_id,
            ["type", "child_loops"],
        )

    elif match_type == "Pumps":
        mapping = match_pumps_by_references(
            generated_values, reference_values, object_id_map
        )

    if not mapping:
        mapping = match_by_id(generated_values, reference_values)

    # TODO: Expand capabilities when length of mapping is less than length of generated_values -e.g. unmatched objects
    if len(mapping) < len(generated_values):
        if isinstance(generated_values, dict):
            unmatched_objects = [
                generated_object_id
                for generated_object_id in generated_values
                if generated_object_id not in mapping
            ]
        elif isinstance(generated_values, list):
            unmatched_objects = [
                generated_object.get("id")
                for generated_object in generated_values
                if generated_object.get("id") not in mapping
            ]
        else:
            unmatched_objects = []
            raise TypeError(
                f"Unsupported type for generated_values: {type(generated_values)}"
            )
        print(f"Unmatched {match_type} objects: {','.join(unmatched_objects)}")

    return mapping


def define_construction_map(generated_json, reference_json, object_id_map):
    errors = []
    construction_map = {}

    generated_constructions = get_dict_of_surfaces_with_construction_assigned(
        generated_json
    )
    reference_constructions = get_dict_of_surfaces_with_construction_assigned(
        reference_json
    )

    if (
        len(generated_constructions) == len(reference_constructions)
        and len(generated_constructions) == 1
    ):
        generated_hvac_id, generated_hvac_data = next(
            iter(generated_constructions.items())
        )
        reference_hvac_id, reference_hvac_data = next(
            iter(reference_constructions.items())
        )
        construction_map[generated_hvac_id] = reference_hvac_id
        return construction_map, errors

    else:
        construction_map = get_mapping(
            "Constructions",
            generated_constructions,
            reference_constructions,
            object_id_map=object_id_map,
        )

    return construction_map, errors


def define_materials_map(generated_json, reference_json, object_id_map):
    errors = []
    materials_map = {}

    generated_materials = find_all(
        "$.ruleset_model_descriptions[0].materials[*]", generated_json
    )
    reference_materials = find_all(
        "$.ruleset_model_descriptions[0].materials[*]", reference_json
    )

    primary_layer_ids = find_all(
        "$.ruleset_model_descriptions[0].constructions[*].primary_layers[*]",
        generated_json,
    )
    framing_layer_ids = find_all(
        "$.ruleset_model_descriptions[0].constructions[*].framing_layers[*]",
        generated_json,
    )

    # Combine both lists into a set for faster lookup
    referenced_ids = set(primary_layer_ids + framing_layer_ids)

    # Filter generated_materials to only include those whose id is referenced in primary_layer_ids or framing_layer_ids
    filtered_generated_materials = [
        mat for mat in generated_materials if mat.get("id") in referenced_ids
    ]

    if (
        len(filtered_generated_materials) == len(reference_materials)
        and len(filtered_generated_materials) == 1
    ):
        generated_material_data = filtered_generated_materials[0]
        reference_material_data = reference_materials[0]
        materials_map[generated_material_data["id"]] = reference_material_data["id"]
        return materials_map, errors

    else:
        materials_map = get_mapping(
            "Materials",
            filtered_generated_materials,
            reference_materials,
            object_id_map=object_id_map,
        )

    return materials_map, errors


def define_surface_map(generated_zone, reference_zone, generated_json, reference_json):
    generated_zone_id = generated_zone["id"]
    reference_zone_id = reference_zone["id"]
    surface_map = {}
    errors = []

    surface_types = [
        ("Exterior Wall", {"classification": "WALL", "adjacent_to": "EXTERIOR"}),
        ("Interior Wall", {"classification": "WALL", "adjacent_to": "INTERIOR"}),
        ("Ground Floor", {"classification": "FLOOR", "adjacent_to": "GROUND"}),
        ("Roof", {"classification": "CEILING", "adjacent_to": "EXTERIOR"}),
    ]

    for surface_type, filters in surface_types:
        generated_surfaces = find_all_with_filters(
            "$.surfaces[*]", filters, generated_zone
        )
        reference_surfaces = find_all_with_filters(
            "$.surfaces[*]", filters, reference_zone
        )

        if surface_type == "Interior Wall":
            # Extend with surfaces from other zones where this zone is the adjacent_zone
            generated_surfaces.extend(
                find_all_with_field_value(
                    "$.ruleset_model_descriptions[0].buildings[0].building_segments[0].zones[*].surfaces[*]",
                    "adjacent_zone",
                    generated_zone_id,
                    generated_json,
                )
            )
            reference_surfaces.extend(
                find_all_with_field_value(
                    "$.ruleset_model_descriptions[0].buildings[0].building_segments[0].zones[*].surfaces[*]",
                    "adjacent_zone",
                    reference_zone_id,
                    reference_json,
                )
            )

        local_surface_map, local_surface_map_errors = define_local_surface_map(
            generated_zone_id,
            reference_zone_id,
            surface_type,
            generated_surfaces,
            reference_surfaces,
        )

        surface_map.update(local_surface_map)
        errors.extend(local_surface_map_errors)

    return surface_map, errors


def define_local_surface_map(
    generated_zone_id,
    reference_zone_id,
    surface_type,
    generated_surfaces,
    reference_surfaces,
):
    errors = []
    local_surface_map = {}

    if len(generated_surfaces) != len(reference_surfaces):
        errors.append(
            f"{surface_type} surface count mismatch in zone id '{generated_zone_id}'. "
            f"Expected: {len(reference_surfaces)}; got: {len(generated_surfaces)}"
        )
        return local_surface_map, errors

    elif len(generated_surfaces) == 1:
        local_surface_map[generated_surfaces[0]["id"]] = reference_surfaces[0]["id"]
        return local_surface_map, errors

    else:
        local_surface_map = get_mapping(
            "Surfaces",
            generated_surfaces,
            reference_surfaces,
            generated_zone_id=generated_zone_id,
            reference_zone_id=reference_zone_id,
        )
        return local_surface_map, errors


def define_local_subsurface_map(surface_map, generated_json, reference_json):
    errors = []
    subsurface_map = {}

    for generated_surface_id, reference_surface_id in surface_map.items():
        generated_surface = find_one(
            f"...surfaces[?(@.id=='{generated_surface_id}')]",
            generated_json,
        )
        reference_surface = find_one(
            f"...surfaces[?(@.id=='{reference_surface_id}')]",
            reference_json,
        )

        generated_subsurfaces = find_all("$.subsurfaces[*]", generated_surface)
        reference_subsurfaces = find_all("$.subsurfaces[*]", reference_surface)

        if len(generated_subsurfaces) != len(reference_subsurfaces):
            errors.append(...)
            continue

        if len(generated_subsurfaces) == 1:
            subsurface_map[generated_subsurfaces[0]["id"]] = reference_subsurfaces[0]["id"]
        else:
            subsurface_map.update(
                get_mapping("Subsurfaces", generated_subsurfaces, reference_subsurfaces)
            )

    return subsurface_map, errors


def define_hvac_map(generated_json, reference_json, object_id_map):
    errors = []
    hvac_map = {}

    generated_hvacs = get_dict_of_zones_and_terminals_served_by_hvac_sys(generated_json)
    reference_hvacs = get_dict_of_zones_and_terminals_served_by_hvac_sys(reference_json)

    if len(generated_hvacs) != len(reference_hvacs):
        errors.append(
            f"HVAC system count mismatch. Expected: {len(reference_hvacs)}; got: {len(generated_hvacs)}"
        )
        return hvac_map, errors

    if len(generated_hvacs) == 1:
        generated_hvac_id, generated_hvac_data = next(iter(generated_hvacs.items()))
        reference_hvac_id, reference_hvac_data = next(iter(reference_hvacs.items()))
        hvac_map[generated_hvac_id] = reference_hvac_id
        return hvac_map, errors

    else:
        hvac_map = get_mapping(
            "HVAC Systems",
            generated_hvacs,
            reference_hvacs,
            object_id_map=object_id_map,
        )

    return hvac_map, errors


def define_terminal_map(object_id_map, generated_zone, reference_zone):
    errors = []
    terminal_map = {}

    generated_terminals = find_all(
        "$.terminals[*]",
        generated_zone,
    )
    reference_terminals = find_all(
        "$.terminals[*]",
        reference_zone,
    )

    generated_zone_id = generated_zone.get("id")

    if len(generated_terminals) != len(reference_terminals):
        errors.append(
            f"Terminal count mismatch in zone id '{generated_zone_id}'. "
            f"Expected: {len(reference_terminals)}; got: {len(generated_terminals)}"
        )
        return terminal_map, errors

    if len(generated_terminals) == 1:
        terminal_map[generated_terminals[0]["id"]] = reference_terminals[0]["id"]
        return terminal_map, errors

    else:
        terminal_map = get_mapping(
            "Terminals",
            generated_terminals,
            reference_terminals,
            generated_zone_id=generated_zone_id,
            reference_zone_id=reference_zone["id"],
            object_id_map=object_id_map,
        )
    return terminal_map, errors


def define_boiler_map(generated_json, reference_json, object_id_map):
    errors = []
    boiler_map = {}

    generated_boilers = find_all(
        "$.ruleset_model_descriptions[0].boilers[*]",
        generated_json,
    )
    reference_boilers = find_all(
        "$.ruleset_model_descriptions[0].boilers[*]",
        reference_json,
    )

    if len(generated_boilers) != len(reference_boilers):
        errors.append(
            f"Boiler count mismatch. Expected: {len(reference_boilers)}; got: {len(generated_boilers)}"
        )
        return boiler_map, errors

    if len(generated_boilers) == 1:
        generated_boiler_data = generated_boilers[0]
        reference_boiler_data = reference_boilers[0]
        boiler_map[generated_boiler_data["id"]] = reference_boiler_data["id"]
        return boiler_map, errors

    else:
        boiler_map = get_mapping(
            "Boilers",
            generated_boilers,
            reference_boilers,
            object_id_map=object_id_map,
        )

    return boiler_map, errors


def define_chiller_map(generated_json, reference_json, object_id_map):
    errors = []
    chiller_map = {}

    generated_chillers = find_all(
        "$.ruleset_model_descriptions[0].chillers[*]",
        generated_json,
    )
    reference_chillers = find_all(
        "$.ruleset_model_descriptions[0].chillers[*]",
        reference_json,
    )

    if len(generated_chillers) != len(reference_chillers):
        errors.append(
            f"Chiller count mismatch. Expected: {len(reference_chillers)}; got: {len(generated_chillers)}"
        )
        return chiller_map, errors

    if len(generated_chillers) == 1:
        generated_chiller_data = generated_chillers[0]
        reference_chiller_data = reference_chillers[0]
        chiller_map[generated_chiller_data["id"]] = reference_chiller_data["id"]
        return chiller_map, errors

    else:
        chiller_map = get_mapping(
            "Chillers",
            generated_chillers,
            reference_chillers,
            object_id_map=object_id_map,
        )

    return chiller_map, errors


def define_heat_rejection_map(generated_json, reference_json, object_id_map):
    errors = []
    heat_rejection_map = {}

    generated_heat_rejections = find_all(
        "$.ruleset_model_descriptions[0].heat_rejections[*]",
        generated_json,
    )
    reference_heat_rejections = find_all(
        "$.ruleset_model_descriptions[0].heat_rejections[*]",
        reference_json,
    )

    if len(generated_heat_rejections) != len(reference_heat_rejections):
        errors.append(
            f"Heat Rejection count mismatch. Expected: {len(reference_heat_rejections)}; "
            f"got: {len(generated_heat_rejections)}"
        )
        return heat_rejection_map, errors

    if len(generated_heat_rejections) == 1:
        generated_heat_rejection_data = generated_heat_rejections[0]
        reference_heat_rejection_data = reference_heat_rejections[0]
        heat_rejection_map[
            generated_heat_rejection_data["id"]
        ] = reference_heat_rejection_data["id"]
        return heat_rejection_map, errors

    else:
        heat_rejection_map = get_mapping(
            "Heat Rejections",
            generated_heat_rejections,
            reference_heat_rejections,
            object_id_map=object_id_map,
        )

    return heat_rejection_map, errors


def define_loop_map(generated_json, reference_json, object_id_map):
    errors = []
    loop_map = {}

    generated_loops = find_all(
        "$.ruleset_model_descriptions[0].fluid_loops[*]",
        generated_json,
    )
    generated_loops.extend(
        find_all(
            "$.ruleset_model_descriptions[0].fluid_loops[*].child_loops[*]",
            generated_json,
        )
    )
    reference_loops = find_all(
        "$.ruleset_model_descriptions[0].fluid_loops[*]",
        reference_json,
    )
    reference_loops.extend(
        find_all(
            "$.ruleset_model_descriptions[0].fluid_loops[*].child_loops[*]",
            reference_json,
        )
    )

    if len(generated_loops) != len(reference_loops):
        errors.append(
            f"Loop count mismatch. Expected: {len(reference_loops)}; got: {len(generated_loops)}"
        )
        return loop_map, errors

    if len(generated_loops) == 1:
        generated_loop_data = generated_loops[0]
        reference_loop_data = reference_loops[0]
        loop_map[generated_loop_data["id"]] = reference_loop_data["id"]
        return loop_map, errors

    else:
        loop_map = get_mapping(
            "Loops",
            generated_loops,
            reference_loops,
            object_id_map=object_id_map,
        )

    return loop_map, errors


def define_pump_map(generated_json, reference_json, object_id_map):
    errors = []
    pump_map = {}

    generated_pumps = find_all(
        "$.ruleset_model_descriptions[0].pumps[*]",
        generated_json,
    )
    reference_pumps = find_all(
        "$.ruleset_model_descriptions[0].pumps[*]",
        reference_json,
    )

    if len(generated_pumps) != len(reference_pumps):
        errors.append(
            f"Pump count mismatch. Expected: {len(reference_pumps)}; got: {len(generated_pumps)}"
        )
        return pump_map, errors

    if len(generated_pumps) == 1:
        generated_pump_data = generated_pumps[0]
        reference_pump_data = reference_pumps[0]
        pump_map[generated_pump_data["id"]] = reference_pump_data["id"]
        return pump_map, errors

    else:
        pump_map = get_mapping(
            "Pumps",
            generated_pumps,
            reference_pumps,
            object_id_map=object_id_map,
        )

    return pump_map, errors


def map_objects(generated_json, reference_json):
    warnings = []
    errors = []

    generated_zones = get_zones_from_json(generated_json)
    reference_zones = get_zones_from_json(reference_json)

    # Define a map for Zones. ! Maps for other objects will depend on this map !
    object_id_map = get_mapping("Zones", generated_zones, reference_zones)

    if len(object_id_map) != len(reference_zones):
        errors.append(
            f"Could not match zones between the generated and reference files. "
            f"Try to better align your modeled zone names with the correct answer file's zone naming conventions."
            f"""\n{chr(10).join(f"- {zone['id']}" for zone in reference_zones)}"""
        )  # chr(10) is a newline character
        # Return early if zones could not be matched
        return object_id_map, warnings, errors

    # Define maps for HVAC systems
    hvac_map, hvac_map_errors = define_hvac_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(hvac_map)
    errors.extend(hvac_map_errors)

    reference_zone_ids = [zone["id"] for zone in reference_zones]

    for i, generated_zone in enumerate(generated_zones):
        generated_zone_id = generated_zone["id"]
        reference_zone_id = object_id_map[generated_zone_id]
        reference_zone = reference_zones[reference_zone_ids.index(reference_zone_id)]

        # Define maps for surfaces
        surface_map, surface_map_errors = define_surface_map(
            generated_zone, reference_zone, generated_json, reference_json
        )
        object_id_map.update(surface_map)
        errors.extend(surface_map_errors)

        subsurface_map, subsurface_map_errors = define_local_subsurface_map(
            surface_map, generated_json, reference_json
        )
        object_id_map.update(subsurface_map)
        errors.extend(subsurface_map_errors)

        # Define maps for terminals
        terminal_map, terminal_map_errors = define_terminal_map(
            object_id_map,
            generated_zone,
            reference_zone,
        )
        object_id_map.update(terminal_map)
        errors.extend(terminal_map_errors)

    construction_map, construction_map_errors = define_construction_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(construction_map)
    errors.extend(construction_map_errors)

    materials_map, materials_map_errors = define_materials_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(materials_map)
    errors.extend(materials_map_errors)

    boiler_map, boiler_map_errors = define_boiler_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(boiler_map)
    errors.extend(boiler_map_errors)

    chiller_map, chiller_map_errors = define_chiller_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(chiller_map)
    errors.extend(chiller_map_errors)

    heat_rejection_map, heat_rejection_map_errors = define_heat_rejection_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(heat_rejection_map)
    errors.extend(heat_rejection_map_errors)

    loop_map, loop_map_errors = define_loop_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(loop_map)
    errors.extend(loop_map_errors)

    pump_map, pump_map_errors = define_pump_map(
        generated_json, reference_json, object_id_map
    )
    object_id_map.update(pump_map)
    errors.extend(pump_map_errors)

    print(object_id_map)

    return object_id_map, warnings, errors


def match_by_id(generated_values, reference_values):
    """Matches generated and reference objects by ID."""
    mapping, used_ids = {}, set()
    for generated_object in generated_values:
        best_match = find_best_match(
            generated_object.get("id"), [ref.get("id") for ref in reference_values]
        )
        if best_match and best_match not in used_ids:
            mapping[generated_object.get("id")] = best_match
            used_ids.add(best_match)
    return mapping


def match_by_attributes(
    generated_values, reference_values, generated_zone_id, reference_zone_id, attrs
):
    """Matches generated and reference objects based on specified attributes."""
    mapping = {}
    used_reference_ids = set()

    for generated_object in generated_values:
        best_match = get_best_match_attrs(
            generated_object,
            reference_values,
            attrs,
            generated_zone_id,
            reference_zone_id,
            used_reference_ids,
        )
        if best_match:
            mapping[generated_object.get("id")] = best_match.get("id")
            used_reference_ids.add(best_match.get("id"))

    return mapping


def match_by_attributes_with_excess_generated(
    generated_values, reference_values, attrs
):
    """Matches generated and reference objects based on specified attributes.

    Handles cases where generated list is longer than reference list.
    Each reference object is used at most once. Unmatched generated objects are excluded.
    """
    all_matches = []

    # Generate all possible (gen_id, ref_id, score) tuples
    for gen_obj in generated_values:
        gen_id = gen_obj.get("id")
        for ref_obj in reference_values:
            ref_id = ref_obj.get("id")
            score = sum(compare_attributes(gen_obj, ref_obj, attr) for attr in attrs)
            all_matches.append((gen_id, ref_id, score))

    # Sort all potential matches by descending score
    all_matches.sort(key=lambda x: -x[2])

    mapping = {}
    used_gen_ids = set()
    used_ref_ids = set()

    # Greedily select highest-scoring matches without reusing any IDs
    for gen_id, ref_id, score in all_matches:
        if gen_id not in used_gen_ids and ref_id not in used_ref_ids:
            mapping[gen_id] = ref_id
            used_gen_ids.add(gen_id)
            used_ref_ids.add(ref_id)

    return mapping


def match_constructions_by_surfaces_assigned(
    generated_values, reference_values, object_id_map
):
    # Convert to list-of-dict format with `id` key for compatibility
    generated_list = [
        {"id": generated_id, **generated_data}
        for generated_id, generated_data in generated_values.items()
    ]
    reference_list = [
        {"id": reference_id, **reference_data}
        for reference_id, reference_data in reference_values.items()
    ]

    # Attributes to compare (numeric + counts)
    attrs = [
        "exterior_walls",
        "rooves",
        "below_grade_surfaces",
        "interior_surfaces",
        "primary_layers_length",
        "framing_layers_length",
        "u_factor",
        "c_factor",
        "f_factor",
    ]

    return match_by_attributes_with_excess_generated(
        generated_list,
        reference_list,
        attrs=attrs,
    )


def match_sys_by_zones_served(generated_values, reference_values, object_id_map):
    mapping = {}

    # Create a dictionary to map sets of reference zones served to their corresponding HVAC IDs
    reference_zones_map = {
        frozenset(zone for zone in data["zone_list"]): ref_hvac_id
        for ref_hvac_id, data in reference_values.items()
    }

    for gen_hvac_id, gen_data in generated_values.items():
        generated_zones = gen_data["zone_list"]

        corresponding_reference_zones = [
            object_id_map.get(zone) for zone in generated_zones
        ]

        if None in corresponding_reference_zones:
            continue

        key = frozenset(corresponding_reference_zones)
        if key in reference_zones_map:
            mapping[gen_hvac_id] = reference_zones_map[key]

    return mapping


def match_terminals_by_references(generated_values, reference_values, object_id_map):
    """Matches generated and reference terminal objects based on references to the HVAC systems that serve them."""
    mapping = {}
    used_reference_ids = set()

    for generated_object in generated_values:
        generated_hvac_id = generated_object.get(
            "served_by_heating_ventilating_air_conditioning_system"
        )
        best_match = None

        if generated_hvac_id:
            reference_hvac_id = object_id_map.get(generated_hvac_id)
            if reference_hvac_id:
                best_match = next(
                    (
                        terminal
                        for terminal in reference_values
                        if terminal.get("id") not in used_reference_ids
                        and terminal.get(
                            "served_by_heating_ventilating_air_conditioning_system"
                        )
                        == reference_hvac_id
                    ),
                    None,
                )

        if not best_match:
            best_match = get_best_match_attrs(
                generated_object,
                reference_values,
                [
                    "type",
                    "is_supply_ducted",
                    "heating_source",
                    "heating_capacity",
                    "cooling_capacity",
                    "primary_airflow",
                    "minimum_outdoor_airflow",
                ],
                None,
                None,
                used_reference_ids,
            )

        if best_match:
            mapping[generated_object.get("id")] = best_match.get("id")
            used_reference_ids.add(best_match.get("id"))

    return mapping


def match_pumps_by_references(generated_values, reference_values, object_id_map):
    """Match generated and reference pumps based on references to the loops that they serve."""
    mapping = {}
    for generated_object in generated_values:
        generated_loop_id = generated_object.get("loop_or_piping")
        if generated_loop_id:
            reference_loop_id = object_id_map.get(generated_loop_id)
            if reference_loop_id:
                best_match = next(
                    (
                        reference_value
                        for reference_value in reference_values
                        if reference_value.get("loop_or_piping") == reference_loop_id
                    ),
                    None,
                )
                if best_match:
                    mapping[generated_object.get("id")] = best_match.get("id")
                    reference_values.remove(best_match)

    return mapping


def get_best_match_attrs(
    target, candidates, attrs, generated_zone_id, reference_zone_id, used_reference_ids
):
    """Finds the best match for a target object based on specified attributes,
    prioritizing unused candidates when scores are tied.
    """
    best_match_found = None
    highest_qty_matched = -1

    for candidate in candidates:
        qty_matched = sum(
            compare_attributes(
                target, candidate, attr, generated_zone_id, reference_zone_id
            )
            for attr in attrs
        )

        if qty_matched > highest_qty_matched:
            highest_qty_matched = qty_matched
            best_match_found = candidate
        elif qty_matched == highest_qty_matched:
            if (
                best_match_found
                and best_match_found.get("id") in used_reference_ids
                and candidate.get("id") not in used_reference_ids
            ):
                best_match_found = candidate

    return best_match_found
