"""
Módulo de exportación de archivos vectoriales e informes de producción para tapetes.
Soporta exportación a:
- SVG (Estándar vectorial abierto)
- PDF Vectorial (Directo para imprentas y talleres de tufting)
- PNG de Alta Resolución (Para visualización o catálogos)
- Ficha Técnica de Producción en PDF (con tabla de colores, porcentajes e hilados)
"""

from typing import List, Dict, Optional
import io
import os
import tempfile
from PIL import Image

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def svg_to_pdf_bytes(svg_content: str) -> bytes:
    """
    Convierte el código SVG a un archivo PDF vectorial puro usando svglib y reportlab.
    """
    # Escribir temporalmente el SVG a disco para svglib
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w", encoding="utf-8") as tmp_svg:
        tmp_svg.write(svg_content)
        tmp_svg_path = tmp_svg.name
        
    try:
        drawing = svg2rlg(tmp_svg_path)
        if drawing is None:
            raise ValueError("No se pudo parsear el SVG para PDF")
            
        pdf_buffer = io.BytesIO()
        renderPDF.drawToFile(drawing, pdf_buffer)
        return pdf_buffer.getvalue()
    finally:
        if os.path.exists(tmp_svg_path):
            try:
                os.remove(tmp_svg_path)
            except Exception:
                pass


def image_to_png_bytes(image: Image.Image, scale_factor: int = 1) -> bytes:
    """
    Convierte una imagen PIL a bytes PNG, opcionalmente reescalada en alta resolución.
    """
    if scale_factor > 1:
        new_size = (image.width * scale_factor, image.height * scale_factor)
        img_scaled = image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        img_scaled = image
        
    buf = io.BytesIO()
    img_scaled.save(buf, format="PNG")
    return buf.getvalue()


def create_production_sheet_pdf(
    logo_image: Image.Image,
    mockup_image: Optional[Image.Image],
    palette: List[Dict],
    client_name: str = "Cliente",
    rug_size: str = "60 x 40 cm",
    rug_material: str = "Tufting / Hilado Acrílico",
    preset_name: str = "Tapete Estándar"
) -> bytes:
    """
    Genera un informe / Ficha Técnica de Producción profesional en PDF (A4)
    con especificaciones de tapete, desglose de colores y muestras visuales.
    """
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#718096"),
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=8
    )
    text_style = ParagraphStyle(
        "TextStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748")
    )
    
    story = []
    
    # 1. Cabecera
    story.append(Paragraph("FICHA TÉCNICA DE PRODUCCIÓN - TAPETE PERSONALIZADO", title_style))
    story.append(Paragraph(f"Cliente: <b>{client_name}</b> | Formato: Vectorial Listo para Fabricación", subtitle_style))
    story.append(Spacer(1, 8))
    
    # 2. Información del Tapete (Tabla resumen)
    info_data = [
        [Paragraph("<b>Dimensiones del Tapete:</b>", text_style), Paragraph(rug_size, text_style),
         Paragraph("<b>Tipo de Fabricación:</b>", text_style), Paragraph(rug_material, text_style)],
        [Paragraph("<b>Preset Vectorial:</b>", text_style), Paragraph(preset_name, text_style),
         Paragraph("<b>Colores Requeridos:</b>", text_style), Paragraph(f"{len(palette)} colores", text_style)]
    ]
    info_table = Table(info_data, colWidths=[130, 130, 130, 130])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))
    
    # 3. Vista previa del Mockup / Logo
    story.append(Paragraph("VISTA PREVIA DEL PRODUCTO TERMINADO", section_style))
    
    preview_img = mockup_image if mockup_image is not None else logo_image
    # Guardar imagen a temporal para reportlab
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        preview_img.save(tmp_img.name, format="PNG")
        tmp_img_path = tmp_img.name
        
    try:
        # Escalar proporcionalmente para que quepa en el PDF (ancho máx 480pt, alto máx 200pt)
        aspect = preview_img.height / max(1, preview_img.width)
        target_w = 460
        target_h = min(220, target_w * aspect)
        story.append(RLImage(tmp_img_path, width=target_w, height=target_h))
    finally:
        pass
        
    story.append(Spacer(1, 14))
    
    # 4. Tabla de Paleta de Colores para Hilado / Corte
    story.append(Paragraph("PALETA DE COLORES Y MATERIALES A UTILIZAR", section_style))
    story.append(Paragraph("Utilice estos códigos HEX / RGB para seleccionar los rollos de hilado, goma o vinilo correspondientes:", text_style))
    story.append(Spacer(1, 6))
    
    palette_data = [
        [
            Paragraph("<b>Muestra</b>", text_style),
            Paragraph("<b>Código HEX</b>", text_style),
            Paragraph("<b>RGB</b>", text_style),
            Paragraph("<b>% Superficie</b>", text_style),
            Paragraph("<b>Uso Recomendado</b>", text_style)
        ]
    ]
    
    for i, col in enumerate(palette):
        hex_val = col.get("hex", "#000000")
        rgb_val = col.get("rgb", (0, 0, 0))
        pct = col.get("percent", 0.0)
        
        # Uso sugerido
        if i == 0 and pct > 40:
            uso = "Color Base / Principal"
        elif pct > 15:
            uso = "Color Secundario"
        else:
            uso = "Detalles / Acento"
            
        palette_data.append([
            "",  # Celda vacía que pintaremos de fondo con el color real
            Paragraph(f"<b>{hex_val}</b>", text_style),
            Paragraph(f"({rgb_val[0]}, {rgb_val[1]}, {rgb_val[2]})", text_style),
            Paragraph(f"{pct}%", text_style),
            Paragraph(uso, text_style)
        ])
        
    palette_table = Table(palette_data, colWidths=[60, 90, 110, 100, 160])
    
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]
    
    # Colorear cada muestra en la primera columna
    for idx, col in enumerate(palette):
        row_idx = idx + 1
        rgb_val = col.get("rgb", (0, 0, 0))
        bg_col = colors.Color(rgb_val[0] / 255.0, rgb_val[1] / 255.0, rgb_val[2] / 255.0)
        table_styles.append(('BACKGROUND', (0, row_idx), (0, row_idx), bg_col))
        
    palette_table.setStyle(TableStyle(table_styles))
    story.append(palette_table)
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("<i>Nota: El archivo vectorial .SVG adjunto contiene las curvas y capas exactas requeridas para los programas de diseño (Illustrator, CorelDraw) o máquinas de corte/tufting.</i>", subtitle_style))
    
    # Construir documento
    doc.build(story)
    
    # Limpieza de archivo temporal
    if os.path.exists(tmp_img_path):
        try:
            os.remove(tmp_img_path)
        except Exception:
            pass
            
    return pdf_buffer.getvalue()
