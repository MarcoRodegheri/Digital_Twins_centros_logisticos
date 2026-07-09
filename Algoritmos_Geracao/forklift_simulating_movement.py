from datetime import datetime, timezone

FORKLIFT_ID = "forklift-1"
BASE_AREA_ID = "base-area"
PICKING_AREA_ID = "picking-area"
GROUND_AREA_ID = "ground-area"
STEP = 1
DOCK_TOLERANCE = 0.25


# =====================================================
# GET BUILDING BY UUID
# =====================================================
def get_building_by_uuid(context, building_uuid):

    buildings = (context["get_instances_by_template"]("building") or [])

    for building in buildings:
        if building.get("id") == building_uuid:
            return building
    return None

# =====================================================
# GET NEXT STACK Z
# =====================================================
def get_next_stack_z(context,building_id):
    building = (context["get_instance"](building_id) or {})
    building_uuid = (building.get("id"))
    containers = (context["get_instances_by_template"]("container") or [])
    max_z = -1
    for container in containers:
        if (container.get("parent_id")==building_uuid):
            pos = (container.get("manual_position") or {})
            z = pos.get("z", 0)
            if z > max_z:
                max_z = z

    return max_z + 1

# =====================================================
# MAIN
# =====================================================
def generate_data(context):

    # =====================================================
    # FORKLIFT
    # =====================================================
    forklift = (context["get_instance"](FORKLIFT_ID) or {})
    forklift_state = (forklift.get("consolidated_state") or {})
    status = (forklift_state.get("status","idle"))
    forklift_pos = (forklift.get("manual_position") or {})
    fx = forklift_pos.get("x", 0)
    fy = forklift_pos.get("y", 0)

    # =====================================================
    # WAITING
    # =====================================================
    if status == "idle":
        return {
            "event_type":"idle",
            "state": forklift_state,
            "forklift_position": {
                "x": fx,
                "y": fy,
                "z": 0
            },
        }
    if status == "relocation_completed":
        context["update_instance_state"](
            FORKLIFT_ID,
            {
                "status": "check_excess_containers"
            }
        )
        return {
            "event_type": "relocation_completed",
            "state": forklift_state,
            "forklift_position": {
                "x": fx,
                "y": fy,
                "z": 0
            },
        }
    if status == "docked":
        return {
            "event_type": "waiting_rfid_validation",
            "state": forklift_state,
            "forklift_position": {
                "x": fx,
                "y": fy,
                "z": 0
            },
        }

    # ---------------------------------------------
    # SOURCE BUILDING
    # ---------------------------------------------
    target_building_id = None
    if status in ["moving_to_source", "returning_to_source"]:
        target_container = (context["get_instance"](forklift_state.get("target_container_id")) or {})
        parent_uuid = (target_container.get("parent_id"))
        source_building = (get_building_by_uuid(context,parent_uuid) or {})
        target_building_id = (source_building.get("instance_id"))

    # ---------------------------------------------
    # EXCESS CONTAINER SOURCE
    # ---------------------------------------------
    elif status == ("moving_to_excess_container"):
        relocation_container = (
            context["get_instance"](
                forklift_state.get("relocation_container_id")
            )
            or {}
        )
        parent_uuid = (relocation_container.get("parent_id"))
        source_building = (get_building_by_uuid(context,parent_uuid) or {})
        target_building_id = (source_building.get("instance_id"))

    # ---------------------------------------------
    # REHANDLING BUFFER
    # ---------------------------------------------
    elif status == ("moving_rehandling_container"):
        target_building_id = (forklift_state.get("buffer_building_id"))

    # ---------------------------------------------
    # EXCESS CONTAINER BUFFER
    # ---------------------------------------------
    elif status == ("moving_excess_container"):
        target_building_id = (forklift_state.get("buffer_building_id"))

    # ---------------------------------------------
    # PICKING AREA
    # ---------------------------------------------
    elif status == ("moving_target_to_picking"):
        target_building_id = (PICKING_AREA_ID)

    # ---------------------------------------------
    # GROUND AREA
    # ---------------------------------------------
    elif status == ("moving_target_to_ground"):
        target_building_id = (GROUND_AREA_ID)

    # ---------------------------------------------
    # TARGET ON GROUND
    # ---------------------------------------------
    elif status == ("moving_to_target_on_ground"):
        target_building_id = (GROUND_AREA_ID)

    # ---------------------------------------------
    # BASE AREA
    # ---------------------------------------------
    elif status == ("returning_to_base"):
        target_building_id = (BASE_AREA_ID)

    # =====================================================
    # TARGET INSTANCE
    # =====================================================
    building = (context["get_instance"](target_building_id) or {})

    if not building:
        return {
            "event_type": "target_not_found",
            "state": forklift_state,
            "forklift_position": {
                "x": fx,
                "y": fy,
                "z": 0
            },
        }

    # =====================================================
    # TARGET POSITION
    # =====================================================
    building_pos = (building.get("manual_position") or {})
    bx = building_pos.get("x", 0)
    by = building_pos.get("y", 0)
    target_x = bx - 1
    target_y = by

    # =====================================================
    # MOVEMENT
    # =====================================================
    next_x = fx
    next_y = fy

    if abs(fx - target_x) > DOCK_TOLERANCE:
        if fx < target_x:
            next_x = min(fx + STEP,target_x)
        else:
            next_x = max(fx - STEP,target_x)

    elif abs(fy - target_y) > DOCK_TOLERANCE:
        if fy < target_y:
            next_y = min(fy + STEP,target_y)
        else:
            next_y = max(fy - STEP,target_y)

    fx = next_x
    fy = next_y

    context["update_instance_position"](
        FORKLIFT_ID,
        x=round(fx, 2),
        y=round(fy, 2),
        z=0
    )

    # =====================================================
    # MOVE CARRIED CONTAINER
    # =====================================================
    carried_container_id = None

    if status == "moving_rehandling_container":
        carried_container_id = (forklift_state.get("temporary_container_id"))

    elif status == "moving_excess_container":
        carried_container_id = (forklift_state.get("relocation_container_id"))

    elif status == "moving_target_to_picking":
        carried_container_id = (forklift_state.get("target_container_id"))

    elif status == "moving_target_to_ground":
        carried_container_id = (forklift_state.get("target_container_id"))

    if carried_container_id:
        context["update_instance_position"](
            carried_container_id,
            x=round(fx, 2),
            y=round(fy, 2),
            z=0
        )

    # =====================================================
    # DOCKING
    # =====================================================
    docked = (
        abs(fx - target_x) <= DOCK_TOLERANCE
        and
        abs(fy - target_y) <= DOCK_TOLERANCE
    )

    # =====================================================
    # ACTIONS WHEN DOCKED
    # =====================================================
    if docked:

        # -----------------------------------------
        # ARRIVED SOURCE
        # -----------------------------------------
        if status in [ "moving_to_source", "returning_to_source"]:
            context["update_instance_state"](FORKLIFT_ID, { "status":"docked"})

        # -----------------------------------------
        # ARRIVED EXCESS CONTAINER
        # -----------------------------------------
        elif status == ("moving_to_excess_container"):
            container_id = (forklift_state.get("relocation_container_id"))
            context["update_instance_parent"](container_id,FORKLIFT_ID)
            context["update_instance_state"](FORKLIFT_ID,{"status":"moving_excess_container"})

        # -----------------------------------------
        # REHANDLING
        # -----------------------------------------
        elif status == ("moving_rehandling_container"):
    
            next_z = get_next_stack_z(context,target_building_id)
            container_id = (forklift_state.get("temporary_container_id"))
            context["update_instance_parent"](container_id,target_building_id)
            context["update_instance_position"](container_id,x=bx,y=by,z=next_z)
            context["update_instance_state"](FORKLIFT_ID,{"status":"returning_to_source"})

        # -----------------------------------------
        # EXCESS CONTAINER
        # -----------------------------------------
        elif status == ("moving_excess_container"):

            next_z = get_next_stack_z(context,target_building_id)
            container_id = (forklift_state.get("relocation_container_id"))
            context["update_instance_parent"](container_id,target_building_id)
            context["update_instance_position"](container_id,x=bx,y=by,z=next_z)
            context["update_instance_state"](FORKLIFT_ID,{"status":"relocation_completed"})

        # -----------------------------------------
        # PICKING
        # -----------------------------------------
        elif status == ("moving_target_to_picking"):
            container_id = (forklift_state.get("target_container_id"))
            context[ "update_instance_parent"](container_id,PICKING_AREA_ID)
            context[ "update_instance_position"](container_id, x=bx, y=by, z=0)
            context[ "update_instance_state"](FORKLIFT_ID,{"status":"returning_to_base"})

        # -----------------------------------------
        # GROUND
        # -----------------------------------------
        elif status == ("moving_target_to_ground"):
            container_id = (forklift_state.get("target_container_id"))
            context["update_instance_parent"](container_id,GROUND_AREA_ID)
            context["update_instance_position"](container_id,x=bx,y=by,z=0)
            context["update_instance_state"](FORKLIFT_ID,
                {   "status": "check_excess_containers",
                    "current_building": None,
                    "building_rfid_validated": False,
                    "container_rfid_validated": False,
                    "temporary_container_id": None,
                    "buffer_building_id": None
                })

        # -----------------------------------------
        # TARGET ON GROUND
        # -----------------------------------------
        elif status == ("moving_to_target_on_ground"):
            container_id = (forklift_state.get("target_container_id"))
            context["update_instance_parent"](container_id,FORKLIFT_ID)
            context["update_instance_state"](FORKLIFT_ID,{"status":"moving_target_to_picking"})

        # -----------------------------------------
        # RETURN BASE
        # -----------------------------------------
        elif status == ("returning_to_base"):
            context[ "update_instance_state"](FORKLIFT_ID,
                {   "status": "idle",
                    "current_building": None,
                    "building_rfid_validated": False,
                    "container_rfid_validated": False,
                    "temporary_container_id": None,
                    "buffer_building_id": None
                })

    # =====================================================
    # RETURN
    # =====================================================
    return {
        "event_type": "forklift_navigation",
        "state": forklift_state,
        "target_building": target_building_id,
        "forklift_position": {
            "x": fx,
            "y": fy,
            "z": 0
        },
        "target_position": {
            "x": target_x,
            "y": target_y,
            "z": 0
        }
    }
