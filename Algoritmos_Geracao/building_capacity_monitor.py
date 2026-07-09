from datetime import datetime, timezone

FORKLIFT_ID = "forklift-1"

# =====================================================
# GET BUILDING OCCUPANCY
# =====================================================
def get_building_occupancy(context, building_uuid):

    containers = (
        context["get_instances_by_template"]("container")
        or []
    )

    count = 0

    for container in containers:

        if container.get("parent_id") == building_uuid:
            count += 1

    return count

# =====================================================
# GET EXCESS CONTAINERS
# =====================================================
def get_excess_containers(
    context,
    building_uuid,
    max_height
):

    containers = (
        context["get_instances_by_template"]("container")
        or []
    )

    building_containers = []

    for container in containers:

        if container.get("parent_id") == building_uuid:

            pos = (
                container.get("manual_position")
                or {}
            )

            building_containers.append({
                "container_id":
                    container.get("instance_id"),
                "z":
                    pos.get("z", 0)
            })

    # ordena por altura
    building_containers.sort(
        key=lambda c: c["z"]
    )

    excess = (
        len(building_containers)
        - max_height
    )

    if excess <= 0:
        return []

    return [
        container["container_id"]
        for container in building_containers[-excess:]
    ]

# =====================================================
# MAIN
# =====================================================
def generate_data(context):

    forklift = (
        context["get_instance"](FORKLIFT_ID)
        or {}
    )

    forklift_state = (
        forklift.get("consolidated_state")
        or {}
    )

    forklift_status = forklift_state.get("status")

    buildings = (
        context["get_instances_by_template"]("building")
        or []
    )

    violations = []

    for building in buildings:

        building_uuid = building.get("id")
        building_id = building.get("instance_id")

        state = (
            building.get("consolidated_state")
            or {}
        )

        max_height = state.get("max_height", 0)

        occupancy = get_building_occupancy(
            context,
            building_uuid
        )

        excess = occupancy - max_height

        if excess > 0:

            containers_to_relocate = (
                get_excess_containers(
                    context,
                    building_uuid,
                    max_height
                )
            )

            violations.append({
                "building_id": building_id,
                "building_uuid": building_uuid,
                "occupancy": occupancy,
                "max_height": max_height,
                "excess": excess,
                "containers_to_relocate":
                containers_to_relocate
            })

    violations_count = len(violations)

    if forklift_status == "capacity_validation":

        next_status = (
            "moving_target_to_ground"
            if violations_count > 0
            else "moving_target_to_picking"
        )

        context["update_instance_state"](
            FORKLIFT_ID,
            {
                "status": next_status,
                "capacity_violations_count":
                    violations_count,
                "capacity_violations":
                    violations
            }
        )

    elif forklift_status == "check_excess_containers":

        next_status = (
            "excess_containers_detected"
            if violations_count > 0
            else "moving_to_target_on_ground"
        )

        context["update_instance_state"](
            FORKLIFT_ID,
            {
                "status": next_status,
                "capacity_violations_count":
                    violations_count,
                "capacity_violations":
                    violations
            }
        )

    elif forklift_status == "excess_containers_detected":

        relocation_container_id = None

        if violations_count > 0:

            containers_to_relocate = (
                violations[0].get("containers_to_relocate")
                or []
            )

            if len(containers_to_relocate) > 0:
                relocation_container_id = containers_to_relocate[0]

        if relocation_container_id:

            context["update_instance_state"](
                FORKLIFT_ID,
                {
                    "status": "moving_to_excess_container",
                    "relocation_container_id":
                        relocation_container_id,
                    "capacity_violations_count":
                        violations_count,
                    "capacity_violations":
                        violations
                }
            )

    return {
        "event_type":
            (
                "building_capacity_exceeded"
                if violations_count > 0
                else "building_capacity_ok"
            ),

        "violations_count":
            violations_count,

        "violations":
            violations,
    }
