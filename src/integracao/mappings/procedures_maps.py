from typing import List, Dict, Optional

V1_POLOTRIAL_PROCEDURES_MAP: List[Dict[str, Optional[str]]] = [
    {
        #1
        "procedure_name": r"Termo de Consentimento Livre e Esclarecido",
        "redcap_check_field": "tcle_q6",
        "redcap_date_field": "tcle_q6"
    },
    {
        #2
        "procedure_name": r"Avaliação dos critérios de elegibilidade",
        "redcap_check_field": "elegibilidade_q1",
        "redcap_date_field": "elegibilidade_dt"
    },
     {
        #3
        "procedure_name": r"Revisão dos critérios de elegibilidade",
        "redcap_check_field": "elegibilidade_q1",
        "redcap_date_field": "elegibilidade_dt"
    },
     {
        #4
        "procedure_name": r"Randomização",
        "redcap_check_field": "randomizacao_q1",
        "redcap_date_field": "randomizacao_q2"
    },
     {
        #5
        "procedure_name": r"Registro de dados de histórico médico e estado menopausal",
        "redcap_check_field": "historico_medico_dt",
        "redcap_date_field": "historico_medico_dt"
    },
     {
        #6
        "procedure_name": r"Registro de dados demográficos",
        "redcap_check_field": "dados_sociodemograficos_dt",
        "redcap_date_field": "dados_sociodemograficos_dt"
    },
     {
        #7
        "procedure_name": r"Exame clínico/físico",
        "redcap_check_field": "exame_fisico_dt",
        "redcap_date_field": "exame_fisico_dt"
    },
     {
        #8
        "procedure_name": r"Exame de gravidez \(urina\)",
        "redcap_check_field": "teste_gravidez_q2",
        "redcap_date_field": "teste_gravidez_dt"
    },
     {
        #9
        "procedure_name": r"Orientações sobre a utilização do\(s\) cosmético\(s\)",
        "redcap_check_field": "revisao_dados_q8",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #10
        "procedure_name": r"Registro de eventos adversos",
        "redcap_check_field": "revisao_dados_q13",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #11
        "procedure_name": r"Registro de medicações prévias/concomitantes e uso de terapia hormonal da menopausa",
        "redcap_check_field": "revisao_dados_q5",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #12
        "procedure_name": r"Questionário Sensorial",
        "redcap_check_field": "sensorial_dt",
        "redcap_date_field": "sensorial_dt"
    },
     {
        #13
        "procedure_name": r"Questionário SF-36",
        "redcap_check_field": "sf36_dt",
        "redcap_date_field": "sf36_dt"
    },
     {
        #14
        "procedure_name": r"Questionário GAD-7",
        "redcap_check_field": "gad7_dt",
        "redcap_date_field": "gad7_dt"
    },
     {
        #15
        "procedure_name": r"Questionário PHQ-9",
        "redcap_check_field": "phq9_dt",
        "redcap_date_field": "phq9_dt"
    },
     {
        #16
        "procedure_name": r"Questionário WPAI-GH",
        "redcap_check_field": "wpai_dt",
        "redcap_date_field": "wpai_dt"
    },
     {
        #17
        "procedure_name": r"Questionário WHOQOL",
        "redcap_check_field": "whoqol_dt",
        "redcap_date_field": "whoqol_dt"
    },
     {
        #18
        "procedure_name": r"Questionário referente à Escala de Rosenberg adaptada",
        "redcap_check_field": "autoestima_dt",
        "redcap_date_field": "autoestima_dt"
    },
     {
        #19
        "procedure_name": r"Corneometria",
        "redcap_check_field": "aval_dermato_q1",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #20
        "procedure_name": r"Cutometria",
        "redcap_check_field": "aval_dermato_q2",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #21
        "procedure_name": r"Evaporimetria",
        "redcap_check_field": "aval_dermato_q3",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #22
        "procedure_name": r"Avaliação fotográfica",
        "redcap_check_field": "aval_dermato_q0",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #23
        "procedure_name": r"Avaliação de satisfação da participante \(Escala Likert de 5 pontos\)",
        "redcap_check_field": "satisfacao_iniciais_q1",
        "redcap_date_field": "satisfacao_iniciais_dt"
    },
     {
        #24-Sérum Ultra Repositor
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "sur_q2",
        "redcap_date_field": "sur_dt"
    },
    {
        #24 - Tratamento Intensivo Noturno
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "tin_q2",
        "redcap_date_field": "tin_dt"
    },
    {
        #25
        "procedure_name": r"Tape Stripping para avaliação por lipidômica",
        "redcap_check_field": "sur_q5",
        "redcap_date_field": "sur_dt"
    },
     {
        #26
        "procedure_name": r"Biópsia para histopatologia e imunohistoquímica/imunofluorescência",
        "redcap_check_field": "sur_q4",
        "redcap_date_field": "sur_dt"
    },
     {
        #27
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s+\(escala IGA para\s+pigmentação\)",
        "redcap_check_field": "hurhi_q2",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #28
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador \(escala visual para ressecamento\)",
        "redcap_check_field": "hurhi_q3",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #29
        "procedure_name": r"Avaliação clínica subjetiva realizada pela participante \(escala visual analógica para ressecamento\)",
        "redcap_check_field": "hurhi_q5",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #30
        "procedure_name": r"Consulta médica",
        "redcap_check_field": "consulta_nome_medico",
        "redcap_date_field": "consulta_dt"
    },
     {
        #31
        "procedure_name": r"Reconsentimento",
        "redcap_check_field": "tcle_q1",
        "redcap_date_field": "reconsentimento_dt"
    },
    

]

V2_POLOTRIAL_PROCEDURES_MAP: List[Dict[str, Optional[str]]] = [
    {
        #1
        "procedure_name": r"Termo de Consentimento Livre e Esclarecido",
        "redcap_check_field": "tcle_q6",
        "redcap_date_field": "tcle_q6"
    },
    {
        #2
        "procedure_name": r"Avaliação dos critérios de elegibilidade",
        "redcap_check_field": "",
        "redcap_date_field": ""
    },
     {
        #3
        "procedure_name": r"Revisão dos critérios de elegibilidade",
        "redcap_check_field": "elegibilidade_q1",
        "redcap_date_field": "elegibilidade_dt"
    },
     {
        #4
        "procedure_name": r"Randomização",
        "redcap_check_field": "randomizacao_q1",
        "redcap_date_field": "randomizacao_q2"
    },
     {
        #5
        "procedure_name": r"Registro de dados de histórico médico e estado menopausal",
        "redcap_check_field": "historico_medico_dt",
        "redcap_date_field": "historico_medico_dt"
    },
     {
        #6
        "procedure_name": r"Registro de dados demográficos",
        "redcap_check_field": "dados_sociodemograficos_dt",
        "redcap_date_field": "dados_sociodemograficos_dt"
    },
     {
        #7
        "procedure_name": r"Exame clínico/físico",
        "redcap_check_field": "exame_fisico_dt",
        "redcap_date_field": "exame_fisico_dt"
    },
     {
        #8 — ESCAPAR parênteses
        "procedure_name": r"Exame de gravidez \(urina\)",
        "redcap_check_field": "teste_gravidez_q2",
        "redcap_date_field": "teste_gravidez_dt"
    },
     {
        #9 — ESCAPAR parênteses
        "procedure_name": r"Orientações sobre a utilização do\(s\) cosmético\(s\)",
        "redcap_check_field": "revisao_dados_q8",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #10
        "procedure_name": r"Registro de eventos adversos",
        "redcap_check_field": "revisao_dados_q13",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #11
        "procedure_name": r"Registro de medicações prévias/concomitantes e uso de terapia hormonal da menopausa",
        "redcap_check_field": "revisao_dados_q5",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #12
        "procedure_name": r"Questionário Sensorial",
        "redcap_check_field": "sensorial_dt",
        "redcap_date_field": "sensorial_dt"
    },
     {
        #13
        "procedure_name": r"Questionário SF-36",
        "redcap_check_field": "sf36_dt",
        "redcap_date_field": "sf36_dt"
    },
     {
        #14
        "procedure_name": r"Questionário GAD-7",
        "redcap_check_field": "gad7_dt",
        "redcap_date_field": "gad7_dt"
    },
     {
        #15
        "procedure_name": r"Questionário PHQ-9",
        "redcap_check_field": "phq9_dt",
        "redcap_date_field": "phq9_dt"
    },
     {
        #16
        "procedure_name": r"Questionário WPAI-GH",
        "redcap_check_field": "wpai_dt",
        "redcap_date_field": "wpai_dt"
    },
     {
        #17
        "procedure_name": r"Questionário WHOQOL",
        "redcap_check_field": "whoqol_dt",
        "redcap_date_field": "whoqol_dt"
    },
     {
        #18
        "procedure_name": r"Questionário referente à Escala de Rosenberg adaptada",
        "redcap_check_field": "autoestima_dt",
        "redcap_date_field": "autoestima_dt"
    },
     {
        #19
        "procedure_name": r"Corneometria",
        "redcap_check_field": "aval_dermato_q1",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #20
        "procedure_name": r"Cutometria",
        "redcap_check_field": "aval_dermato_q2",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #21
        "procedure_name": r"Evaporimetria",
        "redcap_check_field": "aval_dermato_q3",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #22
        "procedure_name": r"Avaliação fotográfica",
        "redcap_check_field": "aval_dermato_q0",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #23 — ESCAPAR parênteses
        "procedure_name": r"Avaliação de satisfação da participante \(Escala Likert de 5 pontos\)",
        "redcap_check_field": "satisfacao_iniciais_q1",
        "redcap_date_field": "satisfacao_iniciais_dt"
    },
     {
        #24-Sérum Ultra Repositor — ESCAPAR parênteses
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "sur_q2",
        "redcap_date_field": "sur_dt"
    },
    {
        #24 - Tratamento Intensivo Noturno — ESCAPAR parênteses
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "tin_q2",
        "redcap_date_field": "tin_dt"
    },
    {
        #25
        "procedure_name": r"Tape Stripping para avaliação por lipidômica",
        "redcap_check_field": "sur_q5",
        "redcap_date_field": "sur_dt"
    },
     {
        #26
        "procedure_name": r"Biópsia para histopatologia e imunohistoquímica/imunofluorescência",
        "redcap_check_field": "sur_q4",
        "redcap_date_field": "sur_dt"
    },
     {
        #27 — ESCAPAR parênteses + \s+ para espaços duplos
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s+\(escala IGA para\s+pigmentação\)",
        "redcap_check_field": "hurhi_q2",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #28 — ESCAPAR parênteses + \s+ para espaços duplos
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s+\(escala visual para\s+ressecamento\)",
        "redcap_check_field": "hurhi_q3",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #29 — ESCAPAR parênteses + \s+ para espaços duplos
        "procedure_name": r"Avaliação clínica subjetiva realizada pela participante\s+\(escala visual\s+analógica para ressecamento\)",
        "redcap_check_field": "hurhi_q5",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #30
        "procedure_name": r"Consulta médica",
        "redcap_check_field": "consulta_nome_medico",
        "redcap_date_field": "consulta_dt"
    },
     {
        #31
        "procedure_name": r"Reconsentimento",
        "redcap_check_field": "tcle_q1",
        "redcap_date_field": "reconsentimento_dt"
    },
    
]

V3_PROCEDURES_MAP: List[Dict[str, Optional[str]]] = [
    {
        #1
        "procedure_name": r"Termo de Consentimento Livre e Esclarecido",
        "redcap_check_field": "tcle_q6",
        "redcap_date_field": "tcle_q6"
    },
    # {
    #     #2
    #     "procedure_name": r"Avaliação dos critérios de elegibilidade",
    #     "redcap_check_field": "",
    #     "redcap_date_field": ""
    # },
     {
        #3
        "procedure_name": r"Revisão dos critérios de elegibilidade",
        "redcap_check_field": "elegibilidade_q1",
        "redcap_date_field": "elegibilidade_dt"
    },
     {
        #4
        "procedure_name": r"Randomização",
        "redcap_check_field": "randomizacao_q1",
        "redcap_date_field": "randomizacao_q2"
    },
     {
        #5
        "procedure_name": r"Registro de dados de histórico médico e estado menopausal",
        "redcap_check_field": "historico_medico_dt",
        "redcap_date_field": "historico_medico_dt"
    },
     {
        #6
        "procedure_name": r"Registro de dados demográficos",
        "redcap_check_field": "dados_sociodemograficos_dt",
        "redcap_date_field": "dados_sociodemograficos_dt"
    },
     {
        #7
        "procedure_name": r"Exame clínico/físico",
        "redcap_check_field": "exame_fisico_dt",
        "redcap_date_field": "exame_fisico_dt"
    },
     {
        #8
        "procedure_name": r"Exame de gravidez \(urina\)",
        "redcap_check_field": "teste_gravidez_q2",
        "redcap_date_field": "teste_gravidez_dt"
    },
     {
        #9
        "procedure_name": r"Orientações sobre a utilização do\(s\) cosmético\(s\)",
        "redcap_check_field": "revisao_dados_q8",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #10
        "procedure_name": r"Registro de eventos adversos",
        "redcap_check_field": "ea_evento",
        "redcap_date_field": "ea_dt_inicio"
    },
     {
        #11
        "procedure_name": r"Registro de medicações prévias/concomitantes e uso de terapia hormonal da menopausa",
        "redcap_check_field": "medicacao_dt",
        "redcap_date_field": "medicacao_dt"
    },
     {
        #12
        "procedure_name": r"Questionário Sensorial",
        "redcap_check_field": "sensorial_dt",
        "redcap_date_field": "sensorial_dt"
    },
     {
        #13
        "procedure_name": r"Questionário SF-36",
        "redcap_check_field": "sf36_dt",
        "redcap_date_field": "sf36_dt"
    },
     {
        #14
        "procedure_name": r"Questionário GAD-7",
        "redcap_check_field": "gad7_dt",
        "redcap_date_field": "gad7_dt"
    },
     {
        #15
        "procedure_name": r"Questionário PHQ-9",
        "redcap_check_field": "phq9_dt",
        "redcap_date_field": "phq9_dt"
    },
     {
        #16
        "procedure_name": r"Questionário WPAI-GH",
        "redcap_check_field": "wpai_dt",
        "redcap_date_field": "wpai_dt"
    },
     {
        #17
        "procedure_name": r"Questionário WHOQOL",
        "redcap_check_field": "whoqol_dt",
        "redcap_date_field": "whoqol_dt"
    },
     {
        #18
        "procedure_name": r"Questionário referente à Escala de Rosenberg adaptada",
        "redcap_check_field": "autoestima_dt",
        "redcap_date_field": "autoestima_dt"
    },
     {
        #19
        "procedure_name": r"Corneometria",
        "redcap_check_field": "aval_dermato_q1",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #20
        "procedure_name": r"Cutometria",
        "redcap_check_field": "aval_dermato_q2",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #21
        "procedure_name": r"Evaporimetria",
        "redcap_check_field": "aval_dermato_q3",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #22
        "procedure_name": r"Avaliação fotográfica",
        "redcap_check_field": "aval_dermato_q0",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #23
        "procedure_name": r"Avaliação de satisfação da participante \(Escala Likert de 5 pontos\)",
        "redcap_check_field": "satisfacao_iniciais_q1",
        "redcap_date_field": "satisfacao_iniciais_dt"
    },
     {
        #24-Sérum Ultra Repositor
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "sur_q2",
        "redcap_date_field": "sur_dt"
    },
    {
        #24 - Tratamento Intensivo Noturno
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "tin_q2",
        "redcap_date_field": "tin_dt"
    },
    {
        #25
        "procedure_name": r"Tape Stripping para avaliação por lipidômica",
        "redcap_check_field": "sur_q5",
        "redcap_date_field": "sur_dt"
    },
     {
        #26
        "procedure_name": r"Biópsia para histopatologia e imunohistoquímica/imunofluorescência",
        "redcap_check_field": "sur_q4",
        "redcap_date_field": "sur_dt"
    },
     {
        #27
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s+\(escala IGA para\s+pigmentação\)",
        "redcap_check_field": "hurhi_q2",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #28
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador \(escala visual para ressecamento\)",
        "redcap_check_field": "hurhi_q3",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #29
        "procedure_name": r"Avaliação clínica subjetiva realizada pela participante \(escala visual analógica para ressecamento\)",
        "redcap_check_field": "hurhi_q5",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #30
        "procedure_name": r"Consulta médica",
        "redcap_check_field": "consulta_nome_medico",
        "redcap_date_field": "consulta_dt"
    },
     {
        #31
        "procedure_name": r"Reconsentimento",
        "redcap_check_field": "tcle_q1",
        "redcap_date_field": "reconsentimento_dt"
    },
    
]
    
VISITA_NAO_PROGRAMADA_PROCEDURES_MAP: List[Dict[str, Optional[str]]] = [
    {
        #1
        "procedure_name": r"Termo de Consentimento Livre e Esclarecido",
        "redcap_check_field": "tcle_q6",
        "redcap_date_field": "tcle_q6"
    },
    {
        #2
        "procedure_name": r"Avaliação dos critérios de elegibilidade",
        "redcap_check_field": "",
        "redcap_date_field": ""
    },
     {
        #3
        "procedure_name": r"Revisão dos critérios de elegibilidade",
        "redcap_check_field": "elegibilidade_q1",
        "redcap_date_field": "elegibilidade_dt"
    },
     {
        #4
        "procedure_name": r"Randomização",
        "redcap_check_field": "randomizacao_q1",
        "redcap_date_field": "randomizacao_q2"
    },
     {
        #5
        "procedure_name": r"Registro de dados de histórico médico e estado menopausal",
        "redcap_check_field": "historico_medico_dt",
        "redcap_date_field": "historico_medico_dt"
    },
     {
        #6
        "procedure_name": r"Registro de dados demográficos",
        "redcap_check_field": "dados_sociodemograficos_dt",
        "redcap_date_field": "dados_sociodemograficos_dt"
    },
     {
        #7
        "procedure_name": r"Exame clínico/físico",
        "redcap_check_field": "exame_fisico_dt",
        "redcap_date_field": "exame_fisico_dt"
    },
     {
        #8
        "procedure_name": r"Exame de gravidez\(urina\)",
        "redcap_check_field": "teste_gravidez_q2",
        "redcap_date_field": "teste_gravidez_dt"
    },
     {
        #9
        "procedure_name": r"Orientações sobre a utilização do\(s\) cosmético\(s\)",
        "redcap_check_field": "revisao_dados_q8",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #10
        "procedure_name": r"Registro de eventos adversos",
        "redcap_check_field": "revisao_dados_q13",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #11
        "procedure_name": r"Registro de medicações prévias/concomitantes e uso de terapia hormonal da menopausa",
        "redcap_check_field": "revisao_dados_q5",
        "redcap_date_field": "revisao_dados_dt"
    },
     {
        #12
        "procedure_name": r"Questionário Sensorial",
        "redcap_check_field": "sensorial_dt",
        "redcap_date_field": "sensorial_dt"
    },
     {
        #13
        "procedure_name": r"Questionário SF-36",
        "redcap_check_field": "sf36_dt",
        "redcap_date_field": "sf36_dt"
    },
     {
        #14
        "procedure_name": r"Questionário GAD-7",
        "redcap_check_field": "gad7_dt",
        "redcap_date_field": "gad7_dt"
    },
     {
        #15
        "procedure_name": r"Questionário PHQ-9",
        "redcap_check_field": "phq9_dt",
        "redcap_date_field": "phq9_dt"
    },
     {
        #16
        "procedure_name": r"Questionário WPAI-GH",
        "redcap_check_field": "wpai_dt",
        "redcap_date_field": "wpai_dt"
    },
     {
        #17
        "procedure_name": r"Questionário WHOQOL",
        "redcap_check_field": "whoqol_dt",
        "redcap_date_field": "whoqol_dt"
    },
     {
        #18
        "procedure_name": r"Questionário referente à Escala de Rosenberg adaptada",
        "redcap_check_field": "autoestima_dt",
        "redcap_date_field": "autoestima_dt"
    },
     {
        #19
        "procedure_name": r"Corneometria",
        "redcap_check_field": "aval_dermato_q1",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #20
        "procedure_name": r"Cutometria",
        "redcap_check_field": "aval_dermato_q2",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #21
        "procedure_name": r"Evaporimetria",
        "redcap_check_field": "aval_dermato_q3",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #22
        "procedure_name": r"Avaliação fotográfica",
        "redcap_check_field": "aval_dermato_q0",
        "redcap_date_field": "aval_dermato_dt"
    },
     {
        #23
        "procedure_name": r"Avaliação de satisfação da participante \(Escala Likert de 5 pontos\)",
        "redcap_check_field": "satisfacao_iniciais_q1",
        "redcap_date_field": "satisfacao_iniciais_dt"
    },
     {
        #24-Sérum Ultra Repositor
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "sur_q2",
        "redcap_date_field": "sur_dt"
    },
    {
        #24 - Tratamento Intensivo Noturno
        "procedure_name": r"Gravidade de fotoenvelhecimento \(Escala de Glogau\)",
        "redcap_check_field": "tin_q2",
        "redcap_date_field": "tin_dt"
    },
    {
        #25
        "procedure_name": r"Tape Stripping para avaliação por lipidômica",
        "redcap_check_field": "sur_q5",
        "redcap_date_field": "sur_dt"
    },
     {
        #26
        "procedure_name": r"Biópsia para histopatologia e imunohistoquímica/imunofluorescência",
        "redcap_check_field": "sur_q4",
        "redcap_date_field": "sur_dt"
    },
     {
        #27
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s*\(escala IGA para pigmentação\)",
        "redcap_check_field": "hurhi_q2",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #28
        "procedure_name": r"Avaliação clínica subjetiva realizada pelo pesquisador\s*\(escala visual para ressecamento\)",
        "redcap_check_field": "hurhi_q3",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #29
        "procedure_name": r"Avaliação clínica subjetiva realizada pela participante\s*\(escala visual analógica para ressecamento\)",
        "redcap_check_field": "hurhi_q5",
        "redcap_date_field": "hurhi_dt"
    },
     {
        #30
        "procedure_name": r"Consulta médica",
        "redcap_check_field": "consulta_nome_medico",
        "redcap_date_field": "consulta_dt"
    },
     {
        #31
        "procedure_name": r"Reconsentimento",
        "redcap_check_field": "tcle_q1",
        "redcap_date_field": "reconsentimento_dt"
    },
    
]