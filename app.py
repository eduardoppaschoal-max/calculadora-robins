import streamlit as st
from docx import Document
from docx.shared import Pt, RGBColor
from fpdf import FPDF
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="ROBINS-I V2 Calculator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNÇÕES DE RELATÓRIO (PDF e WORD) ---
def generate_docx(data):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading(f"Relatório ROBINS-I V2: {data['study_id']}", 0)
    doc.add_paragraph(f"Desfecho: {data['outcome']}")
    doc.add_paragraph(f"Resultado Numérico: {data['numeric_result']}")
    
    # Risco Geral
    doc.add_heading("Julgamento Geral de Risco", level=1)
    p = doc.add_paragraph()
    runner = p.add_run(f"Sugestão do Algoritmo: {data['algo_risk']}")
    runner.bold = True
    
    doc.add_paragraph(f"Decisão Final do Pesquisador: {data['manual_risk']}")
    doc.add_paragraph(f"Justificativa Final: {data['manual_justification']}")

    # Detalhes por Domínio
    doc.add_heading("Detalhamento por Domínio", level=1)
    
    for domain, details in data['domains'].items():
        doc.add_heading(domain, level=2)
        doc.add_paragraph(f"Risco Calculado: {details['risk']}")
        doc.add_paragraph(f"Justificativa do Algoritmo: {details['reason']}")
        doc.add_paragraph("Respostas Selecionadas:")
        for q, a in details['answers'].items():
            doc.add_paragraph(f"  - {q}: {a}", style='List Bullet')

    # Salvar em memória
    bio = io.BytesIO()
    doc.save(bio)
    return bio

def generate_pdf(data):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, f"Relatorio ROBINS-I V2: {data['study_id']}", 0, 1, 'C')
            self.ln(10)

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def clean_text(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    # Cabeçalho Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text(f"Desfecho: {data['outcome']}"), 0, 1)
    pdf.cell(0, 10, clean_text(f"Resultado: {data['numeric_result']}"), 0, 1)
    pdf.ln(5)

    # Risco Geral
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_text("Julgamento Geral"), 0, 1)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, clean_text(f"Algoritmo: {data['algo_risk']}"))
    pdf.multi_cell(0, 10, clean_text(f"Decisao Pesquisador: {data['manual_risk']}"))
    pdf.multi_cell(0, 10, clean_text(f"Justificativa: {data['manual_justification']}"))
    pdf.ln(5)

    # Domínios
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_text("Detalhamento por Dominio"), 0, 1)
    
    pdf.set_font("Arial", '', 11)
    for domain, details in data['domains'].items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, clean_text(domain), 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, clean_text(f"Risco: {details['risk']}"), 0, 1)
        pdf.multi_cell(0, 8, clean_text(f"Motivo: {details['reason']}"))
        pdf.ln(2)

    return pdf.output(dest="S").encode("latin-1")

# --- FUNÇÕES AUXILIARES DE UI ---
def get_risk_color(risk):
    if "LOW" in risk: 
        return "#D4AC0D"  # Amarelo escuro
    elif "MODERATE" in risk: 
        return "#E67E22"  # Laranja
    elif "SERIOUS" in risk: 
        return "#C0392B"  # Vermelho
    elif "CRITICAL" in risk: 
        return "#000000"  # Preto
    return "gray"

def display_risk_card(domain, risk, justification):
    color = get_risk_color(risk)
    st.markdown(f"""
    <div style="padding: 10px; border-left: 5px solid {color}; background-color: #f0f2f6; margin-bottom: 10px;">
        <strong>{domain}:</strong> <span style="color: {color}; font-weight: bold;">{risk}</span><br>
        <em style="font-size: 0.9em;">{justification}</em>
    </div>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Dados do Estudo")
    study_id = st.text_input("ID do Estudo / Autor", value="Estudo Exemplo")
    outcome = st.text_input("Desfecho Avaliado", value="Mortalidade")
    numeric_result = st.text_input("Resultado Numérico", value="RR 1.5")
    st.divider()
    st.info("Ferramenta baseada no ROBINS-I V2 (Nov 2025).")

st.title("ROBINS-I V2: Calculadora de Risco de Viés")
if study_id:
    st.subheader(f"Avaliando: {study_id}")

# --- 1. TRIAGEM E CONTEXTO ---
st.header("1. Considerações Preliminares (Triagem)")
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1: b1 = st.selectbox("B1. Os autores fizeram alguma tentativa de controlar fatores de confusão no resultado avaliado?", ["Selecione...", "Y", "PY", "PN", "N"])
with col_b2: b2 = st.selectbox("B2. Se N/PN para B1: Existe potencial suficiente para fatores de confusão que impeçam a consideração deste resultado posteriormente?", ["Selecione...", "N", "PN", "Y", "PY"])
with col_b3: b3 = st.selectbox("B3. O método de medição do resultado foi inadequado?", ["Selecione...", "N", "PN", "Y", "PY"])

# TRAVA DE SEGURANÇA
if b2 in ["Y", "PY"] or b3 in ["Y", "PY"]:
    st.error("🚨 RISCO CRÍTICO DETECTADO NA TRIAGEM (B2 ou B3). Pare a avaliação aqui.")
    st.stop()
st.divider()

# SELEÇÃO DE VARIANTE (C4)
st.markdown("### Contexto da Análise")
c4 = st.radio(
    "C4. A análise levou em consideração as mudanças entre as estratégias de intervenção comparadas durante o acompanhamento, ou outros desvios de protocolo durante o acompanhamento?", 
    ["Não (Intention-to-treat / Atribuição)", "Sim (Per-protocol / Adesão)"]
)
is_variant_a = "Não" in c4

# Inicialização de variáveis globais
report_data = {
    "study_id": study_id,
    "outcome": outcome,
    "numeric_result": numeric_result,
    "domains": {}
}
risks = {}
reasons = {}

# --- DOMÍNIO 1: CONFUSÃO ---
st.header("Domínio 1: Viés devido a Confusão")

if is_variant_a:
    st.caption("Variante A (Intention-to-treat): Foco na atribuição da intervenção.")
    c1, c2 = st.columns(2)

    # COLUNA 1
    with c1:
        help_1_1 = """
        CONTEXTO: Fatores da avaliação preliminar.
        - Y / PY: Todos fatores importantes foram controlados adequadamente.
        - WN (Não, não substancial): A maioria foi controlada. Viés residual provável é pequeno.
        - SN (Não, substancial): Fator importante NÃO controlado com provável impacto no resultado.
        """
        q1_1 = st.selectbox(
            "1.1 Os autores controlaram todos os importantes fatores de confusão que isso se mostrou necessário?", 
            ["Selecione...", "Y", "PY", "WN", "SN", "NI"], 
            help=help_1_1
        )
        
        # 1.4 SEMPRE visível
        help_1_4 = """
        CONTEXTO: Controles Negativos.
        - Y / PY (Alerta): Controle negativo mostrou associação (viés).
        - N / PN (Neutro): Sem problemas detectados.
        - NA: Não foram usados controles negativos.
        """
        q1_4 = st.selectbox(
            "1.4 O uso de controles negativos sugeriu a presença de fatores de confusão não controlados?", 
            ["Selecione...", "Y", "PY", "N", "PN", "NA"],
            help=help_1_4
        )

    # COLUNA 2
    with c2:
        # Visibilidade dinâmica: 1.2 e 1.3 só aparecem se houve tentativa de controle
        enable_details = q1_1 in ["Y", "PY", "WN"]
        
        if enable_details:
            help_1_2 = """
            CONTEXTO: Validade das medidas usadas.
            - Y / PY: Medidas válidas/confiáveis usadas.
            - WN / SN: Medidas com problemas de validade ou confiabilidade.
            - NA: Se não havia fatores de confusão.
            """
            q1_2 = st.selectbox(
                "1.2 Os fatores de confusão que foram controlados foram medidos de forma válida e confiável?", 
                ["Selecione...", "Y", "PY", "WN", "SN", "NI", "NA"],
                help=help_1_2
            )
            
            help_1_3 = """
            CONTEXTO: Ajuste Excessivo (Over-adjustment).
            - Y / PY (Risco): Controlaram mediadores ou colisores.
            - N / PN (Ideal): Não controlaram variáveis indevidas.
            """
            q1_3 = st.selectbox(
                "1.3 Os autores controlaram alguma variável pós-intervenção que poderia ter sido afetada pela intervenção?", 
                ["Selecione...", "Y", "PY", "N", "PN", "NI", "NA"],
                help=help_1_3
            )
        else:
            q1_2 = "NA"
            q1_3 = "NA"

    d1_risk = "PENDENTE"
    d1_reason = "Aguardando respostas..."
    
    # --- ALGORITMO OTIMIZADO DOMÍNIO 1 (Early Exit) ---
    # Prioridade para riscos CRÍTICOS e SÉRIOS sem exigir preenchimento total se não necessário.

    # 1. ATALHO CRÍTICO A: Falha Controle (SN/NI) + Viés Confirmado (1.4 Y/PY)
    if (q1_1 in ["SN", "NI"]) and (q1_4 in ["Y", "PY"]):
        d1_risk = "CRITICAL"
        d1_reason = "Determinante: Falha no controle (1.1) confirmada por controles negativos (1.4)."

    # 2. ATALHO CRÍTICO B: Ajuste Excessivo (1.3 Y/PY) + Viés Confirmado (1.4 Y/PY)
    elif (q1_1 in ["Y", "PY", "WN"]) and (q1_3 in ["Y", "PY"]) and (q1_4 in ["Y", "PY"]):
        d1_risk = "CRITICAL"
        d1_reason = "Determinante: Ajuste excessivo (1.3) confirmado por controles negativos (1.4)."

    # 3. ATALHO SÉRIO: Erro de Medição Grave (Sem Ajuste Excessivo)
    elif (q1_1 in ["Y", "PY", "WN"]) and (q1_3 in ["N", "PN", "NI", "NA"]) and (q1_2 in ["SN", "NI"]):
        d1_risk = "SERIOUS"
        d1_reason = "Determinante: Erro substancial na medição dos fatores (1.2)."

    # 4. CÁLCULO DETALHADO (Se não caiu nos atalhos)
    else:
        can_calculate = False
        
        # Se Falha Controle: Precisa de 1.4
        if q1_1 in ["SN", "NI"] and q1_4 != "Selecione...":
            can_calculate = True
            
        # Se Controle OK: Precisa de 1.2, 1.3 e 1.4
        elif q1_1 in ["Y", "PY", "WN"] and (q1_2 != "Selecione...") and (q1_3 != "Selecione...") and (q1_4 != "Selecione..."):
            can_calculate = True

        if can_calculate:
            # CAMINHO A: FALHA NO CONTROLE (1.1 = SN/NI)
            if q1_1 in ["SN", "NI"]:
                # Se não caiu no Atalho Crítico A, 1.4 é N/PN/NA -> Sério
                d1_risk = "SERIOUS"
                d1_reason = "Falha substancial no controle (1.1). Controles negativos não agravaram para crítico."

            # CAMINHO B: CONTROLE TENTADO (1.1 = Y/PY/WN)
            else:
                is_critical = False
                is_serious = False

                # --- ANÁLISE DE AJUSTE EXCESSIVO (1.3 = Y/PY) ---
                if q1_3 in ["Y", "PY"]:
                    # Já testamos 1.4=Y/PY no Atalho Crítico B.
                    # Resta testar Medição Ruim.
                    if q1_2 in ["SN", "WN", "NI"]:
                        d1_risk = "CRITICAL"
                        d1_reason = "Ajuste excessivo (1.3) agravado por medição insuficiente (1.2)."
                        is_critical = True
                    else:
                        d1_risk = "SERIOUS"
                        d1_reason = "Ajuste excessivo de variáveis (1.3), mitigado por boa medição."
                        is_serious = True
                
                # --- SEM AJUSTE EXCESSIVO (1.3 = N/PN/NA) ---
                else:
                    # Controles Negativos Apitando
                    if q1_4 in ["Y", "PY"]:
                        d1_risk, d1_reason = "SERIOUS", "Controles negativos sugerem viés, apesar do bom controle inicial."
                        is_serious = True
                    
                    # Erro de Medição Grave (Já tratado no Atalho 3, mas reforço lógica aqui)
                    elif q1_2 in ["SN", "NI"]:
                        d1_risk, d1_reason = "SERIOUS", "Erro substancial na medição dos fatores (1.2)."
                        is_serious = True
                
                if not is_critical and not is_serious:
                    # MODERADO
                    if q1_2 == "WN" or q1_1 == "WN":
                        d1_risk = "MODERATE"
                        d1_reason = "Preocupações menores com confusão residual ou erro de medição."
                    # BAIXO
                    else:
                        d1_risk = "LOW"
                        d1_reason = "Baixo risco de viés devido a confusão."

    risks["D1"] = d1_risk
    reasons["D1"] = d1_reason
    
    report_data["domains"]["Domínio 1"] = {
        "risk": d1_risk, 
        "reason": d1_reason, 
        "answers": {"1.1": q1_1, "1.2": q1_2, "1.3": q1_3, "1.4": q1_4}
    }
    
    display_risk_card("Domínio 1", d1_risk, d1_reason)

else:
    else:
    # --- VARIANTE B (Quando C4 = Sim / Per-protocol) ---
    st.caption("Variante B (Efeito da adesão à intervenção): Foco em confusão variável no tempo.")
    
    c1, c2 = st.columns(2)

    with c1:
        # PERGUNTA 1.1
        help_1_1 = """
        Métodos apropriados para controlar fatores de confusão variáveis no tempo ('métodos g') incluem aqueles baseados na ponderação por probabilidade inversa. 
        Modelos de regressão padrão que incluem fatores de confusão variáveis no tempo podem ser problemáticos quando esses fatores são afetados por intervenções anteriores (fenômeno também conhecido como retroalimentação tratamento-fator de confusão).
        """
        q1_1 = st.selectbox(
            "1.1 Os autores utilizaram um método de análise apropriado para controlar os fatores de confusão variáveis ao longo do tempo, bem como os fatores de confusão basais?", 
            ["Selecione...", "Y", "PY", "PN", "N", "NI"], 
            help=help_1_1
        )

        # PERGUNTA 1.5 (Sempre visível)
        help_1_5 = """
        A utilização de um "controle negativo" – a exploração de uma análise alternativa na qual nenhuma associação deveria ser observada – pode, por vezes, sugerir que o resultado está sujeito a fatores de confusão não controlados, caso sejam identificadas associações semelhantes para o resultado que está sendo avaliado e para o controle negativo.
        Se o estudo não utilizou controles negativos e nenhuma outra consideração sugere fatores de confusão não controlados, responda 'N'. Responda 'S' ou 'PP' se os controles negativos indicarem que o resultado avaliado sofre de viés material devido a fatores de confusão.
        """
        q1_5 = st.selectbox(
            "1.5 O uso de controles negativos, ou outras considerações, sugeriu a presença de fatores de confusão não controlados significativos?", 
            ["Selecione...", "Y", "PY", "PN", "N"], 
            help=help_1_5
        )

    with c2:
        # VISIBILIDADE DINÂMICA
        q1_2 = "NA"
        q1_3 = "NA"
        q1_4 = "NA"

        # Regra de 1.2: Aparece somente se Y/PY para 1.1
        if q1_1 in ["Y", "PY"]:
            help_1_2 = """
            Os principais fatores de confusão são aqueles especificados na seção "Considerações preliminares sobre fatores de confusão". 
            A avaliação deve incluir fatores basais e variáveis no tempo. A falha em controlar fatores importantes pode levar a viés.
            - Y/PY ('S'/'PP'): Todos controlados.
            - WN: Maioria controlada, viés residual pouco provável (ex: fatores não controlados correlacionados com os controlados).
            - SN: Fator importante não controlado com provável impacto significativo.
            """
            q1_2 = st.selectbox(
                "1.2 Os autores controlaram todos os importantes fatores de confusão basais e variáveis ao longo do tempo para os quais isso era necessário?",
                ["Selecione...", "NA", "Y", "PY", "WN", "SN", "NI"],
                help=help_1_2
            )

            # Regra de 1.3: Aparece somente se Y/PY/WN para 1.2
            if q1_2 in ["Y", "PY", "WN"]:
                help_1_3 = """
                O controle adequado exige medidas válidas e confiáveis. 
                Se os autores controlarem as variáveis sem indicar validade/confiabilidade, avalie a subjetividade.
                """
                q1_3 = st.selectbox(
                    "1.3 Os fatores de confusão que foram controlados foram medidos de forma válida e confiável?",
                    ["Selecione...", "NA", "Y", "PY", "WN", "SN", "NI"],
                    help=help_1_3
                )
        
        # Regra de 1.4: Aparece somente se N/PN/NI para 1.1
        elif q1_1 in ["N", "PN", "NI"]:
            help_1_4 = """
            Essa questão surge quando um método de análise inadequado é utilizado. O controle de fatores variáveis no tempo medidos APÓS o início da intervenção provavelmente levará a viés (viés de colisor ou seleção).
            """
            q1_4 = st.selectbox(
                "1.4 Os autores controlaram fatores que variam ao longo do tempo ou outras variáveis medidas após o início da intervenção?",
                ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"],
                help=help_1_4
            )

    d1_risk = "PENDENTE"
    d1_reason = "Aguardando respostas..."

    # --- ALGORITMO DE DECISÃO (VARIANTE B) ---
    # Verifica se as perguntas visíveis foram respondidas
    inputs_ready = False
    if q1_1 != "Selecione..." and q1_5 != "Selecione...":
        if q1_1 in ["Y", "PY"]:
             if q1_2 != "Selecione...":
                 if q1_2 in ["Y", "PY", "WN"]:
                     # Se 1.2 habilitou 1.3, verifica se 1.3 foi respondida
                     if q1_3 != "Selecione...": inputs_ready = True
                 else:
                     # Se 1.2 foi SN/NI/NA, 1.3 fica oculta/NA, então está pronto
                     inputs_ready = True
        elif q1_1 in ["N", "PN", "NI"] and q1_4 != "Selecione...":
             inputs_ready = True

    if inputs_ready:
        # --- RISCO CRÍTICO (4 Caminhos) ---
        is_critical = False
        
        # 1. Viés de Colisor (Erro Metodológico)
        # 1.1 [N, PN, NI] -> 1.4 [Y, PY]
        if q1_1 in ["N", "PN", "NI"] and q1_4 in ["Y", "PY"]:
            d1_risk = "CRITICAL"
            d1_reason = "Método inadequado com ajuste por variáveis pós-intervenção (Viés de Colisor)."
            is_critical = True
        
        # 2. Método Inadequado + Viés Confirmado
        # 1.1 [N, PN, NI] -> 1.4 [N, PN, NI] -> 1.5 [Y, PY]
        elif q1_1 in ["N", "PN", "NI"] and q1_4 in ["N", "PN", "NI"] and q1_5 in ["Y", "PY"]:
            d1_risk = "CRITICAL"
            d1_reason = "Método inadequado e controles negativos indicam confusão não controlada."
            is_critical = True
            
        # 3. Falha Substancial de Controle + Viés Confirmado
        # 1.1 [Y, PY] -> 1.2 [SN, NI] -> 1.5 [Y, PY]
        elif q1_1 in ["Y", "PY"] and q1_2 in ["SN", "NI"] and q1_5 in ["Y", "PY"]:
            d1_risk = "CRITICAL"
            d1_reason = "Falha substancial no controle confirmada por controles negativos."
            is_critical = True
            
        # 4. Falha Substancial de Medição + Viés Confirmado
        # 1.1 [Y, PY] -> 1.2 [Y, PY, WN] -> 1.3 [SN, NI] -> 1.5 [Y, PY]
        elif q1_1 in ["Y", "PY"] and q1_3 in ["SN", "NI"] and q1_5 in ["Y", "PY"]:
            d1_risk = "CRITICAL"
            d1_reason = "Medição inválida dos fatores confirmada por viés em controles negativos."
            is_critical = True

        if not is_critical:
            # --- RISCO SÉRIO (7 Possibilidades) ---
            is_serious = False
            
            # Grupo A: Falha Metodológica (Sem Colisor)
            # 1.1 [N, PN, NI] -> 1.4 [N, PN, NI] -> 1.5 [N, PN]
            if q1_1 in ["N", "PN", "NI"] and q1_4 in ["N", "PN", "NI"] and q1_5 in ["N", "PN"]:
                d1_risk = "SERIOUS"
                d1_reason = "Método de análise inadequado para adesão (falha em ajustar confusão variável no tempo)."
                is_serious = True
            
            # Grupo B: Falhas Substanciais (Sem Confirmação Externa)
            # 2. Falha Substancial de Controle: 1.1 [Y, PY] -> 1.2 [SN, NI] -> 1.5 [N, PN]
            elif q1_1 in ["Y", "PY"] and q1_2 in ["SN", "NI"] and q1_5 in ["N", "PN"]:
                d1_risk = "SERIOUS"
                d1_reason = "Falha substancial no controle de fatores de confusão."
                is_serious = True
            
            # 3. Controle Bom + Falha Substancial de Medição: 1.1 [Y, PY] -> 1.2 [Y, PY] -> 1.3 [SN, NI] -> 1.5 [N, PN]
            elif q1_1 in ["Y", "PY"] and q1_2 in ["Y", "PY"] and q1_3 in ["SN", "NI"] and q1_5 in ["N", "PN"]:
                d1_risk = "SERIOUS"
                d1_reason = "Falha substancial na medição dos fatores de confusão."
                is_serious = True
                
            # 4. Controle Parcial (WN) + Falha Substancial de Medição: 1.1 [Y, PY] -> 1.2 [WN] -> 1.3 [SN, NI] -> 1.5 [N, PN]
            elif q1_1 in ["Y", "PY"] and q1_2 == "WN" and q1_3 in ["SN", "NI"] and q1_5 in ["N", "PN"]:
                 d1_risk = "SERIOUS"
                 d1_reason = "Controle parcial agravado por medição inválida."
                 is_serious = True
                
            # Grupo C: Viés Confirmado por Controles Negativos (Agravante)
            # 5. Viés Confirmado em Estudo "Perfeito": 1.1 [Y, PY] -> 1.2 [Y, PY] -> 1.3 [Y, PY] -> 1.5 [Y, PY]
            elif q1_1 in ["Y", "PY"] and q1_2 in ["Y", "PY"] and q1_3 in ["Y", "PY"] and q1_5 in ["Y", "PY"]:
                d1_risk = "SERIOUS"
                d1_reason = "Controles negativos sugerem viés, apesar do rigor metodológico aparente."
                is_serious = True
            
            # 6. Viés Confirmado com Ressalva Leve na Medição: 1.1 [Y, PY] -> 1.2 [Y, PY] -> 1.3 [WN] -> 1.5 [Y, PY]
            elif q1_1 in ["Y", "PY"] and q1_2 in ["Y", "PY"] and q1_3 == "WN" and q1_5 in ["Y", "PY"]:
                d1_risk = "SERIOUS"
                d1_reason = "Problemas menores de medição agravados por viés em controles negativos."
                is_serious = True
            
            # 7. Viés Confirmado com Ressalva Leve no Controle: 1.1 [Y, PY] -> 1.2 [WN] -> 1.3 [Y, PY, WN] -> 1.5 [Y, PY]
            elif q1_1 in ["Y", "PY"] and q1_2 == "WN" and q1_5 in ["Y", "PY"]:
                d1_risk = "SERIOUS"
                d1_reason = "Problemas menores de controle agravados por viés em controles negativos."
                is_serious = True

            if not is_serious:
                # --- RISCO MODERADO (2 Possibilidades) ---
                is_moderate = False
                
                # Ressalva no Controle: 1.1 [Y, PY] -> 1.2 [WN] -> 1.3 [Y, PY, WN] -> 1.5 [N, PN]
                if q1_1 in ["Y", "PY"] and q1_2 == "WN" and q1_5 in ["N", "PN"]:
                    d1_risk = "MODERATE"
                    d1_reason = "Controle incompleto (mas não substancial) dos fatores de confusão."
                    is_moderate = True
                
                # Ressalva na Medição: 1.1 [Y, PY] -> 1.2 [Y, PY] -> 1.3 [WN] -> 1.5 [N, PN]
                elif q1_1 in ["Y", "PY"] and q1_2 in ["Y", "PY"] and q1_3 == "WN" and q1_5 in ["N", "PN"]:
                    d1_risk = "MODERATE"
                    d1_reason = "Preocupações menores quanto à validade/confiabilidade da medição."
                    is_moderate = True
                
                if not is_moderate:
                    # --- BAIXO RISCO (1 Possibilidade) ---
                    # Caminho Perfeito: 1.1 [Y, PY] -> 1.2 [Y, PY] -> 1.3 [Y, PY] -> 1.5 [N, PN]
                    if q1_1 in ["Y", "PY"] and q1_2 in ["Y", "PY"] and q1_3 in ["Y", "PY"] and q1_5 in ["N", "PN"]:
                        d1_risk = "LOW"
                        d1_reason = "Baixo risco de viés (G-methods aplicados corretamente e medições válidas)."
                    else:
                        d1_risk = "PENDENTE"
                        d1_reason = "Aguardando preenchimento completo..."

    risks["D1"] = d1_risk
    reasons["D1"] = d1_reason
    
    report_data["domains"]["Domínio 1"] = {
        "risk": d1_risk, 
        "reason": d1_reason, 
        "answers": {"1.1": q1_1, "1.2": q1_2, "1.3": q1_3, "1.4": q1_4, "1.5": q1_5}
    }
    
    display_risk_card("Domínio 1", d1_risk, d1_reason)

st.divider()

# --- DOMÍNIO 2: CLASSIFICAÇÃO ---
st.header("Domínio 2: Viés na Classificação")
c1, c2 = st.columns(2)
with c1:
    q2_1 = st.selectbox("2.1 Intervenções distinguíveis no início?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q2_2 = st.selectbox("2.2 Eventos ocorreram após distinção?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
    q2_3 = st.selectbox("2.3 Análise apropriada para atribuição tardia?", ["Selecione...", "NA", "SY", "WY", "PN", "N", "NI"])
with c2:
    q2_4 = st.selectbox("2.4 Classificação influenciada pelo desfecho?", ["Selecione...", "SY", "WY", "PN", "N", "NI"])
    q2_5 = st.selectbox("2.5 Erros de classificação adicionais?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])

d2_risk, d2_reason = "PENDENTE", "Aguardando respostas..."
if "Selecione..." not in [q2_1, q2_2, q2_3, q2_4, q2_5]:
    immortal_time_issue = False
    if q2_1 in ["N", "PN", "NI"] and q2_2 in ["N", "PN", "NI"]:
        if q2_3 not in ["SY"]: 
            immortal_time_issue = True
    
    if q2_4 == "SY": d2_risk, d2_reason = "CRITICAL", "Classificação influenciada substancialmente pelo desfecho."
    elif q2_4 in ["WY", "NI"]: d2_risk, d2_reason = ("CRITICAL" if immortal_time_issue else "SERIOUS"), "Possível influência do desfecho na classificação."
    elif immortal_time_issue: d2_risk, d2_reason = "SERIOUS", "Problema de tempo imortal (immortal time bias) não resolvido."
    elif q2_5 in ["Y", "PY", "NI"] and q2_4 in ["N", "PN"]: d2_risk, d2_reason = "MODERATE", "Erros de classificação não-diferenciais prováveis."
    else: d2_risk, d2_reason = "LOW", "Classificação bem definida."

risks["D2"] = d2_risk
reasons["D2"] = d2_reason
report_data["domains"]["Domínio 2"] = {"risk": d2_risk, "reason": d2_reason, "answers": {"2.1": q2_1, "2.2": q2_2, "2.3": q2_3, "2.4": q2_4, "2.5": q2_5}}
display_risk_card("Domínio 2", d2_risk, d2_reason)
st.divider()

# --- DOMÍNIO 3: SELEÇÃO ---
st.header("Domínio 3: Viés de Seleção")
c1, c2 = st.columns(2)
with c1:
    q3_1 = st.selectbox("3.1 Follow-up coincide com início?", ["Selecione...", "Y", "PY", "WN", "SN", "NI"])
    q3_2 = st.selectbox("3.2 Exclusão de eventos iniciais?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q3_3 = st.selectbox("3.3 Seleção baseada em características pós-início?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q3_4 = st.selectbox("3.4 Variáveis associadas à intervenção?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
with c2:
    q3_5 = st.selectbox("3.5 Variáveis influenciadas pelo desfecho?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
    q3_6 = st.selectbox("3.6 Análise corrigiu viés?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
    q3_7 = st.selectbox("3.7 Sensibilidade mostrou impacto mínimo?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
    q3_8 = st.selectbox("3.8 Vieses severos?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])

d3_risk, d3_reason = "PENDENTE", "Aguardando respostas..."
if "Selecione..." not in [q3_1, q3_2, q3_3, q3_8]: 
    if q3_8 in ["Y", "PY"]: d3_risk, d3_reason = "CRITICAL", "Viés de seleção severo identificado."
    elif q3_1 in ["SN", "NI"] or q3_5 in ["Y", "PY"]:
        if q3_6 in ["Y", "PY"] or q3_7 in ["Y", "PY"]: d3_risk, d3_reason = "MODERATE", "Viés sério mitigado pela análise ou sensibilidade."
        else: d3_risk, d3_reason = "SERIOUS", "Falha no início do follow-up ou seleção influenciada pelo desfecho."
    elif q3_1 == "WN" or q3_2 in ["Y", "PY"] or (q3_3 in ["Y", "PY"] and q3_4 in ["Y", "PY"]): d3_risk, d3_reason = "MODERATE", "Problemas moderados de seleção (início tardio ou exclusão)."
    else: d3_risk, d3_reason = "LOW", "Seleção apropriada."

risks["D3"] = d3_risk
reasons["D3"] = d3_reason
report_data["domains"]["Domínio 3"] = {"risk": d3_risk, "reason": d3_reason, "answers": {"3.1": q3_1, "3.2": q3_2, "3.3": q3_3, "3.4": q3_4, "3.5": q3_5, "3.8": q3_8}}
display_risk_card("Domínio 3", d3_risk, d3_reason)
st.divider()

# --- DOMÍNIO 4: DADOS FALTANTES ---
st.header("Domínio 4: Dados Faltantes")
c1, c2 = st.columns(2)
with c1:
    q4_1 = st.selectbox("4.1 Dados intervenção completos?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q4_2 = st.selectbox("4.2 Dados desfecho completos?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q4_3 = st.selectbox("4.3 Dados confusão completos?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q4_4 = st.selectbox("4.4 Análise de casos completos (Complete Case)?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
with c2:
    q4_5 = st.selectbox("4.5 Exclusão relacionada ao desfecho?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
    q4_6 = st.selectbox("4.6 Relação explicada pelo modelo?", ["Selecione...", "NA", "Y", "PY", "WN", "SN", "NI"])
    q4_9 = st.selectbox("4.9 Imputação apropriada?", ["Selecione...", "NA", "Y", "PY", "WN", "SN", "NI"])
    q4_11 = st.selectbox("4.11 Evidência de que não houve viés?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])

d4_risk, d4_reason = "PENDENTE", "Aguardando respostas..."
if "Selecione..." not in [q4_1, q4_4]:
    all_complete = (q4_1 in ["Y", "PY"] and q4_2 in ["Y", "PY"] and q4_3 in ["Y", "PY"])
    if all_complete: d4_risk, d4_reason = "LOW", "Dados completos para quase todos os participantes."
    else:
        if q4_4 in ["Y", "PY", "NI"]:
            if q4_5 in ["Y", "PY", "NI"]:
                if q4_6 == "SN": d4_risk, d4_reason = ("SERIOUS" if q4_11 not in ["Y", "PY"] else "MODERATE"), "Exclusão relacionada ao desfecho não explicada pelo modelo."
                elif q4_6 in ["WN", "NI"]: d4_risk, d4_reason = "MODERATE", "Incerteza sobre a relação entre exclusão e desfecho."
                else: d4_risk, d4_reason = "LOW", "Relação explicada pelo modelo."
            else: d4_risk, d4_reason = "LOW", "Exclusão não relacionada ao desfecho."
        elif q4_9 == "SN": d4_risk, d4_reason = ("CRITICAL" if q4_11 not in ["Y", "PY"] else "SERIOUS"), "Método de imputação inadequado."
        elif q4_9 in ["WN", "NI"]: d4_risk, d4_reason = "MODERATE", "Dúvidas sobre a qualidade da imputação."
        else: d4_risk, d4_reason = "LOW", "Imputação ou método alternativo apropriado."

risks["D4"] = d4_risk
reasons["D4"] = d4_reason
report_data["domains"]["Domínio 4"] = {"risk": d4_risk, "reason": d4_reason, "answers": {"4.1": q4_1, "4.2": q4_2, "4.3": q4_3, "4.4": q4_4, "4.5": q4_5}}
display_risk_card("Domínio 4", d4_risk, d4_reason)
st.divider()

# --- DOMÍNIO 5: MEDIÇÃO ---
st.header("Domínio 5: Medição do Desfecho")
c1, c2 = st.columns(2)
with c1:
    q5_1 = st.selectbox("5.1 Métodos diferem entre grupos?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q5_2 = st.selectbox("5.2 Avaliadores cientes da intervenção?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
with c2:
    q5_3 = st.selectbox("5.3 Avaliação influenciada pelo conhecimento?", ["Selecione...", "NA", "SY", "WY", "PN", "N", "NI"])

d5_risk, d5_reason = "PENDENTE", "Aguardando respostas..."
if "Selecione..." not in [q5_1, q5_2, q5_3]:
    if q5_1 in ["Y", "PY"]: d5_risk, d5_reason = "SERIOUS", "Métodos de medição diferentes entre os grupos."
    elif q5_2 in ["Y", "PY", "NI"]:
        if q5_3 == "SY": d5_risk, d5_reason = "SERIOUS", "Avaliação subjetiva influenciada pelo conhecimento da intervenção."
        elif q5_3 in ["WY", "NI"]: d5_risk, d5_reason = "MODERATE", "Possível influência no avaliador."
        else: d5_risk, d5_reason = "LOW", "Avaliador ciente, mas desfecho objetivo."
    else:
        if q5_1 == "NI": d5_risk, d5_reason = "MODERATE", "Avaliador cego, mas incerteza sobre comparabilidade dos métodos."
        else: d5_risk, d5_reason = "LOW", "Medição objetiva e comparável."

risks["D5"] = d5_risk
reasons["D5"] = d5_reason
report_data["domains"]["Domínio 5"] = {"risk": d5_risk, "reason": d5_reason, "answers": {"5.1": q5_1, "5.2": q5_2, "5.3": q5_3}}
display_risk_card("Domínio 5", d5_risk, d5_reason)
st.divider()

# --- DOMÍNIO 6: RELATO SELETIVO ---
st.header("Domínio 6: Relato Seletivo")
c1, c2 = st.columns(2)
with c1:
    q6_1 = st.selectbox("6.1 Relatado conforme plano prévio?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q6_2 = st.selectbox("6.2 Seleção baseada em múltiplas medidas?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
with c2:
    q6_3 = st.selectbox("6.3 Seleção baseada em múltiplas análises?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])
    q6_4 = st.selectbox("6.4 Seleção baseada em subgrupos?", ["Selecione...", "Y", "PY", "PN", "N", "NI"])

d6_risk, d6_reason = "PENDENTE", "Aguardando respostas..."
if "Selecione..." not in [q6_1, q6_2, q6_3, q6_4]:
    if q6_1 in ["Y", "PY"]: d6_risk, d6_reason = "LOW", "Seguiu plano de análise pré-especificado."
    else:
        count_selection = 0
        if q6_2 in ["Y", "PY"]: count_selection += 1
        if q6_3 in ["Y", "PY"]: count_selection += 1
        if q6_4 in ["Y", "PY"]: count_selection += 1
        
        count_ni = 0
        if q6_2 == "NI": count_ni += 1
        if q6_3 == "NI": count_ni += 1
        if q6_4 == "NI": count_ni += 1

        if count_selection >= 2: d6_risk, d6_reason = "CRITICAL", "Fortes evidências de seleção de resultados (P-hacking) em múltiplos aspectos."
        elif count_selection == 1: d6_risk, d6_reason = "SERIOUS", "Evidência de seleção em um aspecto (medida, análise ou subgrupo)."
        elif count_ni == 3: d6_risk, d6_reason = "SERIOUS", "Sem plano de análise e sem informação suficiente para julgar seleção."
        elif count_ni > 0: d6_risk, d6_reason = "MODERATE", "Sem plano de análise e algumas informações faltando."
        else: d6_risk, d6_reason = "MODERATE", "Sem plano de análise, mas sem evidências claras de seleção."

risks["D6"] = d6_risk
reasons["D6"] = d6_reason
report_data["domains"]["Domínio 6"] = {"risk": d6_risk, "reason": d6_reason, "answers": {"6.1": q6_1, "6.2": q6_2, "6.3": q6_3, "6.4": q6_4}}
display_risk_card("Domínio 6", d6_risk, d6_reason)
st.divider()

# --- CÁLCULO GERAL ALGORITMO ---
st.header("Julgamento de Risco (Overall)")
all_risks = list(risks.values())
algo_risk = "PENDENTE"

if "PENDENTE" in all_risks:
    st.warning("Responda todos os domínios para ver o cálculo.")
else:
    # Se Domínio 1 estava em construção (N/A), ignoramos ele no cálculo geral por enquanto
    valid_risks = [r for r in all_risks if r != "N/A"]
    
    if "CRITICAL" in valid_risks: algo_risk = "CRITICAL"
    elif valid_risks.count("SERIOUS") >= 2: algo_risk = "CRITICAL"
    elif "SERIOUS" in valid_risks: algo_risk = "SERIOUS"
    elif valid_risks.count("MODERATE") >= 3: algo_risk = "SERIOUS"
    elif "MODERATE" in valid_risks: algo_risk = "MODERATE"
    else: algo_risk = "LOW"
    
    st.markdown(f"""
    <div style="padding: 15px; background-color: {get_risk_color(algo_risk)}; color: white; text-align: center; border-radius: 8px;">
        <h3>RISCO SUGERIDO (ALGORITMO): {algo_risk}</h3>
    </div>
    """, unsafe_allow_html=True)

# --- JULGAMENTO DO PESQUISADOR ---
st.markdown("### Validação pelo Pesquisador")
st.caption("O algoritmo oferece uma sugestão padrão. O pesquisador pode alterar o julgamento final se houver justificativa (Guidance Note 17).")

col_final1, col_final2 = st.columns([1, 2])
with col_final1:
    manual_risk = st.selectbox(
        "Decisão Final de Risco Global",
        ["LOW", "MODERATE", "SERIOUS", "CRITICAL"],
        index=["LOW", "MODERATE", "SERIOUS", "CRITICAL"].index(algo_risk) if algo_risk != "PENDENTE" else 0
    )
with col_final2:
    manual_justification = st.text_area(
        "Justificativa do Pesquisador (Obrigatório para Override)",
        placeholder="Explique se concordou com o algoritmo ou por que alterou o risco..."
    )

# --- ÁREA DE DOWNLOAD ---
st.divider()
st.subheader("📄 Exportar Relatório")

if st.button("Gerar Arquivos para Download"):
    # Atualiza dados finais
    report_data["algo_risk"] = algo_risk
    report_data["manual_risk"] = manual_risk
    report_data["manual_justification"] = manual_justification
    
    # Gera arquivos
    try:
        docx_file = generate_docx(report_data)
        pdf_file = generate_pdf(report_data)
        
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.download_button(
                label="📥 Baixar Relatório WORD (.docx)",
                data=docx_file.getvalue(),
                file_name=f"ROBINS_I_{study_id}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        with col_d2:
            st.download_button(
                label="📥 Baixar Relatório PDF (.pdf)",
                data=pdf_file,
                file_name=f"ROBINS_I_{study_id}.pdf",
                mime="application/pdf"
            )
    except Exception as e:
        st.error(f"Erro ao gerar arquivos: {e}")