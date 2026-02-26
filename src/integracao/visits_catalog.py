from __future__ import annotations

from typing import Dict, Any, Optional

# Importing procedure mapping from sync_engine to avoid circular dependency
from integracao.mappings.procedures_maps import (
    V3_PROCEDURES_MAP,
    VISITA_NAO_PROGRAMADA_PROCEDURES_MAP,
)

class VisitConfig:
    """
    Configuring an generic visit
    """
    
    def __init__(
        self,
        *,
        redcap_event_name:str,
        polotrial_visit_name:str,
        date_field: str,
        procedures_map: list,
        requires_pk: Optional[Dict[str, Any]] = None,
        executor_config: Optional[Dict[str, Any]] = None
    ):
        self.redcap_event_name = redcap_event_name
        self.polotrial_visit_name = polotrial_visit_name
        self.date_field = date_field
        self.procedures_map = procedures_map
        self.requires_pk = requires_pk or {}
        self.executor_config = executor_config or {} # {field, date_field, procedure_pattern}
    
    
# Visits catalog
VISITS_CATALOG = {
    #V3
    # This code snippet is defining a specific configuration for a visit in the `VISITS_CATALOG`
    # dictionary within the `VisitConfig` class.
    "v3vf_arm_1": VisitConfig(
        redcap_event_name = 'v3vf_arm_1',
        polotrial_visit_name = "V3",
        date_field = "revisao_dt_visita",
        procedures_map = V3_PROCEDURES_MAP,
        requires_pk=None,
        executor_config={
            "field": "consulta_nome_medico",
            'date_field': 'consulta_dt',
            "procedure_pattern": r"^Consulta M[eéEÉ]dica$"
        },        
    ),
    # Unscheduled Visit
    "visita_no_programa_arm_1": VisitConfig(
        redcap_event_name = 'visita_no_programa_arm_1',
        polotrial_visit_name= "Não Programada",
        date_field = "form_medico_dt_visita",
        procedures_map = VISITA_NAO_PROGRAMADA_PROCEDURES_MAP,
        requires_pk=None,
        executor_config={
            "field": "consulta_nome_medico",
            'date_field': 'consulta_dt',
            "procedure_pattern": r"^Consulta M[eéEÉ]dica$"
        },        
    )
}
