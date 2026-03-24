from __future__ import annotations

import logging
import json
from typing import Any, Dict, Optional

import pandas as pd
import re
from datetime import datetime
import time

# from integracao.events.v2_randomizacao import CENTER_FIELD
from integracao.mappings.site_code_maps import SITE_CODE_MAPPING
from integracao.polotrial_client import PoloTrialClient
from integracao.redcap_client import RedcapClient

from integracao.mappings.status_maps import STATUS_CODE_MAPPING 

from integracao.sync_engine import V1_EVENT
from integracao.utils import get_date_from_redcap
import os
import dotenv


dotenv.load_dotenv(override=True)

logger = logging.getLogger(__name__)


#====================================================================================================
# V3 MAPPING
#====================================================================================================

V3_VISITA_NAME_BY_GROUP: Dict[int, str] = {
    1: "VF/V3 - Grupo Sérum Ultra Repositor",
    2: "VF/V3 - Grupo Hidra. Ultra. Refres. e Hidra. Intimo",
    3: "VF/V3 - Grupo Trat. Intensivo Noturno",
}


ARM_MAPPING: Dict[str, int] = {
    "1" : 1,
    "Grupo 1 - Sérum Ultra Repositor" : 1,
    "2" : 2,
    "Grupo 2 - Hidratante Ultra Refrescante e Hidratante Íntimo" : 2,
    "3" : 3,
    "Grupo 3 - Tratamento Intensivo Noturno" : 3,
}

def parse_randomziation_group(value) -> Optional[int]:


    if value is None:
        return None
    
    s = str(value).strip().lower()
    if not s:
        return None
    
    arm_mapping_lower = {k.lower(): v for k, v in ARM_MAPPING.items()}
    return arm_mapping_lower.get(s)