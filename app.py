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
    if "LOW" in risk: return "green"
    elif "MODERATE" in risk: return "gold" 
    elif "SERIOUS" in risk: return "orange"
    elif "CRITICAL" in risk: return "red"
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

# --- 1. TRIAGEM ---
st.header("1. Considerações Preliminares (Triagem)")
col_b1, col_b2, col_b3 = st.columns(3)
with col_b1: b1 = st.selectbox("B1. Tentativa de controle de confusão?", ["Selecione...", "Y", "PY", "PN", "N"])
with col_b2: b2 = st.selectbox("B2. Potencial de confusão impede avaliação?", ["Selecione...", "N", "PN", "Y", "PY"])
with col_b3: b3 = st.selectbox("B3. Método de medição inapropriado?", ["Selecione...", "N", "PN", "Y", "PY"])

if b2 in ["Y", "PY"] or b3 in ["Y", "PY"]:
    st.error("🚨 RISCO CRÍTICO DETECTADO NA TRIAGEM. Pare a avaliação.")
    st.stop()
st.divider()

# --- SELEÇÃO DE VARIANTE ---
c4 = st.radio("C4. Análise contabilizou trocas (switches) ou desvios de protocolo?", ["Não (Intention-to-treat)", "Sim (Per-protocol)"])
is_variant_a = "Não" in c4

# Armazenamento de dados para o relatório e lógica
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
    st.caption("Variante A (Intention-to-treat)")
    c1, c2 = st.columns(2)
    with c1:
        q1_1 = st.selectbox("1.1 Controlou todos fatores importantes?", ["Selecione...", "Y", "PY", "WN", "SN", "NI"], help="WN: No, not substantial / SN: No, substantial")
        q1_2 = st.selectbox("1.2 Fatores medidos validamente?", ["Selecione...", "NA", "Y", "PY", "WN", "SN", "NI"])
    with c2:
        q1_3 = st.selectbox("1.3 Controlou variáveis pós-intervenção?", ["Selecione...", "NA", "Y", "PY", "PN", "N", "NI"])
        q1_4 = st.selectbox("1.4 Controles negativos sugerem viés?", ["Selecione...", "N", "PN", "Y", "PY"])
    
    d1_risk, d1_reason = "PENDENTE", "Aguardando respostas..."
    if "Selecione..." not in [q1_1, q1_2, q1_3, q1_4]:
        if q1_4 in ["Y", "PY"]: d1_risk, d1_reason = "CRITICAL", "Controles negativos indicam viés de confusão não controlada séria."
        elif q1_1 in ["SN", "NI"]: d1_risk, d1_reason = "SERIOUS", "Falha substancial no controle de fatores de confusão importantes."
        elif q1_3 in ["Y", "PY"]: d1_risk, d1_reason = "SERIOUS", "Controle inadequado de variáveis pós-intervenção (over-adjustment)."
        elif q1_2 in ["SN", "NI"]: d1_risk, d1_reason = "SERIOUS", "Erro de medição substancial nos fatores de confusão."
        elif q1_1 == "WN" or q1_2 == "WN": d1_risk, d1_reason = "MODERATE", "Preocupações menores com confusão residual ou erro de medição."
        else: d1_risk, d1_reason = "LOW", "Baixo risco (exceto confusão residual)."
    
    risks["D1"] = d1_risk
    reasons["D1"] = d1_reason
    report_data["domains"]["Domínio 1"] = {"risk": d1_risk, "reason": d1_reason, "answers": {"1.1": q1_1, "1.2": q1_2, "1.3": q1_3, "1.4": q1_4}}
    display_risk_card("Domínio 1", d1_risk, d1_reason)
else:
    st.warning("A Variante B requer lógica complexa de G-methods. Implemente conforme necessário.")
    risks["D1"] = "N/A"
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
if "Selecione..." not in [q3_1, q3_2, q3_3, q3_8]: # Checagem simplificada para ativar lógica
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
        # Complete Case
        if q4_4 in ["Y", "PY", "NI"]:
            if q4_5 in ["Y", "PY", "NI"]:
                if q4_6 == "SN": d4_risk, d4_reason = ("SERIOUS" if q4_11 not in ["Y", "PY"] else "MODERATE"), "Exclusão relacionada ao desfecho não explicada pelo modelo."
                elif q4_6 in ["WN", "NI"]: d4_risk, d4_reason = "MODERATE", "Incerteza sobre a relação entre exclusão e desfecho."
                else: d4_risk, d4_reason = "LOW", "Relação explicada pelo modelo."
            else: d4_risk, d4_reason = "LOW", "Exclusão não relacionada ao desfecho."
        # Imputação (Simplificada)
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
    if "CRITICAL" in all_risks: algo_risk = "CRITICAL"
    elif all_risks.count("SERIOUS") >= 2: algo_risk = "CRITICAL"
    elif "SERIOUS" in all_risks: algo_risk = "SERIOUS"
    elif all_risks.count("MODERATE") >= 3: algo_risk = "SERIOUS"
    elif "MODERATE" in all_risks: algo_risk = "MODERATE"
    else: algo_risk = "LOW"
    
    st.markdown(f"""
    <div style="padding: 15px; background-color: {get_risk_color(algo_risk)}; color: white; text-align: center; border-radius: 8px;">
        <h3>RISCO SUGERIDO (ALGORITMO): {algo_risk}</h3>
    </div>
    """, unsafe_allow_html=True)

# --- JULGAMENTO DO PESQUISADOR (CAMPO NOVO) ---
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