from __future__ import annotations

import logging
import os

from integracao.events.v1_screening import sync_v1_screening
from integracao.events.v2_randomizacao import sync_v2_randomization
from integracao.events.generic_visit import sync_generic_visit
from integracao.events.status_atualization import PARTICIPANT_STATUS_EVENT, sync_participant_status_update
from integracao.visits_catalog import VISITS_CATALOG
from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient


logger = logging.getLogger(__name__)

PARTICIPANT_STATUS_EVENT = os.getenv("PARTICIPANT_STATUS_EVENT_NAME")

def dispatch_event(
    *,
    record_id: str,
    event_name: str,
    redcap: RedcapClient,
    polotrial: PoloTrialClient,
    protocol_nickname: str
) -> None:
    """
    

    Args:
        record_id (str): _description_
        event_name (str): _description_
        redcap (RedcapClient): _description_
        polotrial (PoloTrialClient): _description_
        protocol_nickname (str): _description_

    Raises:
        RuntimeError: _description_
    """
    if event_name == "vsv1_arm_1":
        logger.info("Dispatching to V1 handler: %s", event_name)
        sync_v1_screening(
            record_id = record_id,
            event_name = event_name,
            redcap=redcap,
            polotrial=polotrial,
            protocol_nickname=protocol_nickname,
        )
        
        
        return
    

    if event_name == "vrv2_arm_1":
        logger.info("Dispatching to V2 handler: %s", event_name)
        sync_v2_randomization(
            record_id = record_id,
            event_name = event_name,
            redcap=redcap,
            polotrial=polotrial,
            protocol_nickname=protocol_nickname,
            v2_date_field="revisao_dt_visita",
        )
        
        return
    if event_name == PARTICIPANT_STATUS_EVENT:
        logger.info("Dispatching to participant status update handler: %s", event_name)
        sync_participant_status_update(
            record_id=record_id,
            event_name=event_name,
            redcap=redcap,
            polotrial=polotrial,
            protocol_nickname=protocol_nickname,
        )
        return
    
    if event_name in VISITS_CATALOG:
        visit_config = VISITS_CATALOG[event_name]
        logger.info("Dispatching to generic handler: %s (task=%s)", event_name, visit_config.polotrial_visit_name)
        sync_generic_visit(
            record_id=record_id,
            event_name=event_name,
            visit_config=visit_config,
            redcap=redcap,
            polotrial=polotrial,
            protocol_nickname=protocol_nickname,
        )
        return
    
    logger.warning("No handlers implemented for event: %s", event_name)
    raise RuntimeError(f"No handler implemented for event: {event_name}")
