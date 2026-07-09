from datetime import datetime, timezone
import math

FORKLIFT_ID = "forklift-1"
READER_DEVICE_ID = "e74e5cae-50ae-49a0-804d-4dc795a57490"

# =========================================================
# READER OFFSET RELATIVE TO FORKLIFT
# =========================================================
READER_OFFSET_X = 1
READER_OFFSET_Y = 0

# =========================================================
# RSSI
# =========================================================
def calculate_signal(distance):
    
    MIN_DISTANCE = 0.5
    MAX_DISTANCE = 5.0
    if distance <= MIN_DISTANCE:
        return 100
    if distance >= MAX_DISTANCE:
        return 0
    signal = 100 * (MAX_DISTANCE - distance) / (MAX_DISTANCE - MIN_DISTANCE)
    return round(signal, 2)

# =========================================================
# DISTANCE
# =========================================================
def calculate_distance(a, b):

    return math.sqrt(
        (a["x"] - b["x"]) ** 2 +
        (a["y"] - b["y"]) ** 2 +
        (a["z"] - b["z"]) ** 2
    )

# =========================================================
# MAIN
# =========================================================
def generate_data(context):

    # =====================================================
    # FORKLIFT
    # =====================================================
    forklift = context["get_instance"](FORKLIFT_ID) or {}
    forklift_state = forklift.get("consolidated_state") or {}
    #Position
    forklift_pos = forklift.get("manual_position") or {}
    forklift_x = forklift_pos.get("x", 0)
    forklift_y = forklift_pos.get("y", 0)

    # =====================================================
    # FILTER BUILDING CONTAINERS
    # =====================================================
    all_containers = context["get_instances_by_template"]("container") or []
    current_building = forklift_state.get("current_building")
    current_building_instance = context["get_instance"](current_building) or {}
    current_building_uuid = (current_building_instance.get("id"))
    building_containers = []
    for container in all_containers:
        if (container.get("parent_id") == current_building_uuid):
            building_containers.append(container)

    # =====================================================
    # READER DEVICE
    # =====================================================
    reader_device = context["get_device"](READER_DEVICE_ID) or {}
    geometry = reader_device.get("geometry") or {}
    current_reader_z = geometry.get("z",0)
    reader_position = {
        "x": forklift_x + READER_OFFSET_X,
        "y": forklift_y + READER_OFFSET_Y,
        "z": current_reader_z
    }
    # =====================================================
    # RFID SCAN
    # =====================================================
    detected_containers = []
    for container in all_containers:

        container_id = container.get("instance_id")
        pos = container.get("manual_position") or {}
        
        container_position = {
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "z": pos.get("z", 0)
        }
        
        distance = calculate_distance(reader_position,container_position)
        signal_strength = calculate_signal(distance)
        rfid_tag = container.get("consolidated_state",{}).get("rfid_tag","UNKNOWN")
        parent_id = container.get("parent_id")

        if signal_strength > 0:
            detected_containers.append({
                "container_id": container_id,
                "rfid_tag": rfid_tag,
                "container_z": container_position["z"],
                "distance": round(
                    distance,
                    2
                ),
                "signal_strength": signal_strength,
                "parent_id": parent_id
            })

    # =====================================================
    # VALIDATIONS
    # =====================================================
    if not forklift_state.get("building_rfid_validated",False):
        return {
            "event_type": "waiting_building_validation",
            "containers_detected_count": len(detected_containers),
            "detected_containers": detected_containers,
        }
    
    # =====================================================
    # SCAN DA PILHA
    # =====================================================
    target_container = forklift_state.get("target_container_id")
    target_found = False
    target_z = None
    top_z = -1
    top_container_id = None

    for container in building_containers:
        
        container_id = container.get("instance_id")
        pos = container.get("manual_position") or {}
        
        container_position = {
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "z": pos.get("z", 0)
        }

        container_z = container_position["z"]

        # =============================================
        # TOPO DA PILHA
        # =============================================
        if container_z > top_z:
            top_z = container_z
            top_container_id = container_id

        # =============================================
        # TARGET
        # =============================================
        if container_id == target_container:
            target_found = True
            target_z = container_z

    # =====================================================
    # BUSINESS VALIDATION
    # =====================================================
    containers_above_target = 0

    if target_found:
        containers_above_target = (top_z - target_z)

    rehandling_required = (containers_above_target > 0)

    pickup_ready = (target_found and containers_above_target == 0)

    expected_container = (
        top_container_id
        if rehandling_required
        else target_container
    )

    # =====================================================
    # CONTAINER VALIDATED
    # =====================================================
    container_validated = False
    container_rfid_validated = forklift_state.get("container_rfid_validated",False)

    for container in detected_containers:

        if (
            container["container_id"] == expected_container
            and
            container["signal_strength"] == 100
        ):
            container_validated = True
            if expected_container == target_container:
                container_rfid_validated = True
            break

    context["update_instance_state"](FORKLIFT_ID,
        {
            "container_rfid_validated": container_rfid_validated
        }
    )

    # =====================================================
    # UPDATE FORKLIFT STATE
    # =====================================================
    if pickup_ready and container_rfid_validated:
        context["update_instance_parent"](target_container,FORKLIFT_ID)
        context["update_instance_state"](FORKLIFT_ID,
            {
                "status": "capacity_validation",
                "temporary_container_id": None
            }
        )
    elif rehandling_required and container_validated:
        context["update_instance_parent"](top_container_id,FORKLIFT_ID)
        context["update_instance_state"](FORKLIFT_ID,
            {
                "status": "moving_rehandling_container",
                "temporary_container_id": top_container_id
            }
        )

    # =====================================================
    # MOVE READER ATÉ O TOPO
    # =====================================================
    if top_z == -1:
        current_reader_z = 0
    elif current_reader_z < top_z:
        current_reader_z += 1
    else:
        current_reader_z = top_z

    # =====================================================
    # ABSOLUTE POSITION
    # =====================================================
    reader_position = {
        "x": forklift_x + READER_OFFSET_X,
        "y": forklift_y + READER_OFFSET_Y,
        "z": current_reader_z
    }

    # =====================================================
    # UPDATE GEOMETRY
    # =====================================================
    context["set_geometry"](
        READER_DEVICE_ID,
        {
            "x": reader_position["x"],
            "y": reader_position["y"],
            "z": reader_position["z"]
        }
    )  

    # =====================================================
    # EVENT TYPE
    # =====================================================
    if not target_found:
        event_type = "container_not_found"
    elif current_reader_z < top_z:
        event_type = "container_scan"
    elif rehandling_required:
        event_type = "rehandling_required"
    else:
        event_type = "pickup_ready"
        
    # =====================================================
    # RETURN
    # =====================================================
    return {
        "event_type": event_type,
        "containers_detected_count": len(detected_containers),
        "detected_containers": detected_containers,
        "container_rfid_validated": container_rfid_validated,
        "target_id": target_container,
        "target_found": target_found,
        "target_z": target_z,
        "top_container_id": top_container_id,
        "containers_above_target": containers_above_target,
        "rehandling_required": rehandling_required,
        "pickup_ready": pickup_ready,
        #"reader_id": context["device_id"],
        "current_building": current_building,
        "reader_position": reader_position
    }