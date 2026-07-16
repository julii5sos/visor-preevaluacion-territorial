from io import BytesIO

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


st.set_page_config(
    page_title="Visor de preevaluación territorial",
    layout="wide",
)

st.title("Visor de preevaluación territorial")

st.info(
    "Prototipo para identificar señales y priorizar revisiones. "
    "No determina cumplimiento EUDR."
)


def generar_pdf():
    memoria = BytesIO()
    documento = canvas.Canvas(memoria, pagesize=A4)

    documento.setFont("Helvetica-Bold", 16)
    documento.drawString(60, 790, "FICHA DE PREEVALUACIÓN TERRITORIAL")

    documento.setFont("Helvetica", 11)
    documento.drawString(60, 755, "Primera prueba de generación del reporte.")
    documento.drawString(60, 735, "Posteriormente se agregarán mapas y resultados.")

    documento.save()
    memoria.seek(0)
    return memoria.getvalue()


st.download_button(
    label="Descargar ficha PDF",
    data=generar_pdf(),
    file_name="ficha_preevaluacion.pdf",
    mime="application/pdf",
    type="primary",
)
