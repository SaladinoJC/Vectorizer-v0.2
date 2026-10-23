"""
Módulo de Vectorización utilizando VTracer optimizado para fabricación de tapetes.
Genera archivos SVG limpios, escalables y con curvas suaves para tufting,
corte láser/plotter o inyección de goma.
"""

from typing import Dict, Any, Optional
import io
import re
from PIL import Image
import vtracer


PRESETS: Dict[str, Dict[str, Any]] = {
    "tapete_tufting": {
        "name": "Tapete Tufting / Alfombra Estándar (Recomendado)",
        "description": "Curvas redondeadas y suaves, sin piezas diminutas. Ideal para hilado y alfombras tejidas.",
        "colormode": "color",
        "hierarchical": "cutout",       # Formas como piezas de rompecabezas (no se solapan)
        "mode": "spline",              # Curvas Bezier suaves
        "filter_speckle": 12,          # Elimina manchas/puntos de menos de 12px
        "color_precision": 7,
        "layer_difference": 16,
        "corner_threshold": 60,        # Suaviza esquinas agresivas
        "length_threshold": 4.0,
        "splice_threshold": 45,
        "path_precision": 2
    },
    "tapete_geometric": {
        "name": "Logo Geométrico y Tipografía (Letras Claras)",
        "description": "Preserva esquinas rectas y texto nítido sin perder bordes definidos.",
        "colormode": "color",
        "hierarchical": "cutout",
        "mode": "spline",
        "filter_speckle": 5,
        "color_precision": 8,
        "layer_difference": 12,
        "corner_threshold": 25,        # Esquinas más agudas/precisas
        "length_threshold": 2.5,
        "splice_threshold": 35,
        "path_precision": 3
    },
    "tapete_monocromo": {
        "name": "1 Color / Silueta / Vinilo de Corte",
        "description": "Convierte el logo a una silueta vectorial monocromática para recorte o bajo relieve.",
        "colormode": "binary",
        "hierarchical": "stacked",
        "mode": "spline",
        "filter_speckle": 8,
        "color_precision": 6,
        "layer_difference": 16,
        "corner_threshold": 45,
        "length_threshold": 3.0,
        "splice_threshold": 40,
        "path_precision": 2
    },
    "tapete_stacked": {
        "name": "Por Capas Superpuestas (Serigrafía / Estampado)",
        "description": "Las formas se apilan capa sobre capa. Útil si la técnica de producción lo requiere.",
        "colormode": "color",
        "hierarchical": "stacked",
        "mode": "spline",
        "filter_speckle": 8,
        "color_precision": 7,
        "layer_difference": 16,
        "corner_threshold": 50,
        "length_threshold": 3.5,
        "splice_threshold": 40,
        "path_precision": 2
    },
    "tapete_detallado": {
        "name": "Alta Fidelidad (Logos con Muchos Detalles)",
        "description": "Captura detalles pequeños y sutiles variaciones de color.",
        "colormode": "color",
        "hierarchical": "cutout",
        "mode": "spline",
        "filter_speckle": 2,
        "color_precision": 8,
        "layer_difference": 8,
        "corner_threshold": 35,
        "length_threshold": 2.0,
        "splice_threshold": 30,
        "path_precision": 3
    }
}


def sanitize_svg(svg_content: str, width: int, height: int) -> str:
    """
    Asegura que el SVG contenga atributos de viewBox y tamaño correctos
    para máxima compatibilidad con software de diseño (Illustrator, CorelDraw, Inkscape).
    """
    if "viewBox" not in svg_content:
        svg_content = re.sub(
            r'<svg([^>]*)>',
            rf'<svg\1 viewBox="0 0 {width} {height}">',
            svg_content,
            count=1
        )
    return svg_content


def count_svg_paths(svg_content: str) -> int:
    """Cuenta cuántos elementos <path> tiene el SVG generado."""
    return len(re.findall(r'<path\b', svg_content, flags=re.IGNORECASE))


def vectorize_image(
    image: Image.Image,
    preset_key: str = "tapete_tufting",
    custom_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convierte una imagen PIL preprocesada en un archivo SVG vectorial.
    
    Returns:
        Diccionario con:
        - 'svg': Código SVG en formato string
        - 'path_count': Cantidad de trazados vectoriales
        - 'width': Ancho en píxeles
        - 'height': Alto en píxeles
        - 'preset_used': Clave del preset usado
        - 'params': Parámetros finales aplicados
    """
    # Guardar imagen a buffer PNG en memoria
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    
    # Obtener configuración base del preset
    preset_config = PRESETS.get(preset_key, PRESETS["tapete_tufting"]).copy()
    
    # Extraer campos informativos que no van a vtracer
    preset_config.pop("name", None)
    preset_config.pop("description", None)
    
    # Aplicar personalizaciones si existen
    if custom_overrides:
        for k, v in custom_overrides.items():
            if v is not None:
                preset_config[k] = v
                
    # Llamar a vtracer
    svg_raw = vtracer.convert_raw_image_to_svg(
        png_bytes,
        img_format="png",
        **preset_config
    )
    
    width, height = image.size
    svg_clean = sanitize_svg(svg_raw, width=width, height=height)
    path_count = count_svg_paths(svg_clean)
    
    return {
        "svg": svg_clean,
        "path_count": path_count,
        "width": width,
        "height": height,
        "preset_used": preset_key,
        "params": preset_config
    }
