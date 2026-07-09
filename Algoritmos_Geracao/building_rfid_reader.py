from datetime import datetime, timezone
import math

FORKLIFT_ID = "forklift-1"
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
# GET BUILDING BY UUID
# =========================================================
def get_building_by_uuid(context, uuid):

    buildings = (
        context["get_instances_by_template"](
            "building"
        ) or []
    )

    for building in buildings:
        if building.get("id") == uuid:
            return building

    return None

# =========================================================
# GET BUILDING OCCUPANCY
# =========================================================
def get_building_occupancy(context, building_uuid):

    all_containers = (context["get_instances_by_template"]("container") or [])

    count = 0

    for container in all_containers:
        if container.get("parent_id") == building_uuid:
            count += 1

    return count

# =========================================================
# MAIN
# =========================================================
def generate_data(context):

    # =====================================================
    # FORKLIFT
    # =====================================================
    forklift = context["get_instance"](FORKLIFT_ID) or {}
    forklift_pos = forklift.get("manual_position") or {}
    fx = forklift_pos.get("x", 0)
    fy = forklift_pos.get("y", 0)
    reader_x = fx + READER_OFFSET_X
    reader_y = fy + READER_OFFSET_Y

    forklift_state = forklift.get("consolidated_state") or {}
    status = forklift_state.get("status")
    target_container = forklift_state.get("target_container_id")
    target_container = context["get_instance"](target_container) or {}
    building = get_building_by_uuid(context,target_container.get("parent_id"))
    target_building = (building.get("instance_id") if building else None)
    
    # =====================================================
    # ALL BUILDINGS
    # =====================================================
    all_buildings = context["get_instances_by_template"]("building") or []
    detected_buildings = []

    # =====================================================
    # SCAN BUILDINGS
    # =====================================================
    for building in all_buildings:

        building_id = building.get("instance_id")
        building_pos = building.get("manual_position") or {}
        dimensions = building.get("physical_dimensions") or {}

        bx = building_pos.get("x", 0)
        by = building_pos.get("y", 0)

        width = dimensions.get("width",1)
        depth = dimensions.get("depth",1)

        distance = math.sqrt(
            (reader_x - bx) ** 2 +
            (reader_y - by) ** 2
        )

        signal_strength = calculate_signal(
            distance
        )

        rfid_tag = building.get("consolidated_state",{}).get("rfid_tag","UNKNOWN")

        # =============================================
        # SOMENTE PRÉDIOS DETECTADOS
        # =============================================
        if signal_strength > 0:
            detected_buildings.append({
                "building_id": building_id,
                "rfid_tag": rfid_tag,
                "building_center_position": { 
                    "x": bx,
                    "y": by
                },
                "distance": round(distance, 2),
                "signal_strength": signal_strength
            })

    # =====================================================
    # VALIDATION
    # =====================================================
    building_validated = False
    current_building = None

    for building in detected_buildings:

        if (
            building["building_id"]
            == target_building
            and
            building["signal_strength"] == 100
        ):
            building_validated = True
            current_building = target_building
            break
    
    # =====================================================
    # BUFFER BUILDING
    # =====================================================
    buffer_building_id = forklift_state.get("buffer_building_id")

    if ( status == "moving_rehandling_container" and current_building):

        best_count = 999999

        for building in detected_buildings:
            
            building_id = building["building_id"]
            
            # ignora prédio atual
            if (building_id == current_building):
                continue

            neighbor = context["get_instance"](building_id) or {}
            occupancy = (get_building_occupancy(context,neighbor.get("id")))

            if occupancy < best_count:
                best_count = occupancy
                buffer_building_id = building_id

    if (status == "moving_excess_container" and not buffer_building_id):

        relocation_container = (
            context["get_instance"](
                forklift_state.get("relocation_container_id")
            )
            or {}
        )

        source_building = (
            get_building_by_uuid(
                context,
                relocation_container.get("parent_id")
            )
            or {}
        )

        source_building_id = source_building.get("instance_id")
        best_count = 999999

        for building in all_buildings:

            building_id = building.get("instance_id")

            if building_id == source_building_id:
                continue

            occupancy = (
                get_building_occupancy(
                    context,
                    building.get("id")
                )
            )

            if occupancy < best_count:
                best_count = occupancy
                buffer_building_id = building_id

        if buffer_building_id:
            context["update_instance_state"](
                FORKLIFT_ID,
                {
                    "buffer_building_id":
                        buffer_building_id
                }
            )

    # =====================================================
    # UPDATE FORKLIFT STATE
    # =====================================================
    if building_validated:
        context["update_instance_state"](FORKLIFT_ID,
            {
                "current_building": current_building,
                "building_rfid_validated":True,
                "buffer_building_id":buffer_building_id
            }
        )
    else:
        context["update_instance_state"](FORKLIFT_ID,
            {
                "current_building": None,
                "building_rfid_validated":False
            }
        )

    # =====================================================
    # EVENT TYPE
    # =====================================================
    if len(detected_buildings) == 0:
        event_type = "detecting_buildings"
    elif building_validated:
        event_type = "building_detected"
    else:
        event_type = "building_scan"

    # =====================================================
    # WAITING FOR DOCKING
    # =====================================================
    if status != "docked":
        return {
            "event_type": "waiting_docking",
            "buildings_detected_count": len(detected_buildings),
            "detected_buildings": detected_buildings
        }
    
    # =====================================================
    # RETURN
    # =====================================================
    return {
        "event_type": event_type,
        "buildings_detected_count": len(detected_buildings),
        "detected_buildings": detected_buildings,
        "building_rfid_validated": building_validated,
        "target_id": target_building,
        "buffer_building_id": buffer_building_id,
        "current_building": current_building,
        #"reader_id": context["device_id"],
        "reader_position": {
            "x": reader_x,
            "y": reader_y,
        }
    }
