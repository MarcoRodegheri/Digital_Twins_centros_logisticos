# Generation Algorithm - Creates synthetic data
from datetime import datetime
import random

FORKLIFT_ID = "forklift-1"
CONTAINER_ID = "container-1"


def generate_data(context):
    forklift = (context["get_instance"](FORKLIFT_ID) or {})
    context["update_instance_state"](FORKLIFT_ID,
                                                {"status":"moving_to_source",  
                                                "target_container_id": CONTAINER_ID
                                                })

    return forklift