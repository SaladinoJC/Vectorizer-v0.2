"""
Módulo para gestión, reemplazo y personalización de colores de logos para tapetes,
así como renderizado fotorrealista de vectores SVG a imágenes de alta definición.
"""

from typing import List, Dict, Tuple, Optional
import io
import re
import numpy as np
from PIL import Image
import resvg_py


def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """Convierte un código hexadecimal '#RRGGBB' a tupla RGB (r, g, b)."""
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convierte una tupla RGB (r, g, b) a string '#RRGGBB'."""
    return f"#{int(rgb[0]):02X}{int(rgb[1]):02X}{int(rgb[2]):02X}"


def color_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Distancia euclídea entre dos colores en espacio RGB."""
    return float(np.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2))))


def remap_svg_colors(svg_content: str, color_map: Dict[str, str]) -> str:
    """
    Reemplaza colores en el código SVG.
    color_map: {hex_original: hex_nuevo} (ej: {'#6E4E37': '#FF0000'})
    
    Utiliza aproximación por distancia de color para atrapar cualquier ligera
    variación generada por el clustering de vtracer.
    """
    if not color_map:
        return svg_content
        
    # Encontrar todos los códigos hexadecimales presentes en el SVG
    found_hexes = set(re.findall(r'#[0-9a-fA-F]{6}', svg_content))
    
    # Normalizar mapas en mayúsculas
    norm_map = {k.upper(): v.upper() for k, v in color_map.items() if k.upper() != v.upper()}
    if not norm_map:
        return svg_content
        
    svg_result = svg_content
    for fh in found_hexes:
        fh_upper = fh.upper()
        # 1. Coincidencia exacta
        if fh_upper in norm_map:
            pattern = re.compile(re.escape(fh), re.IGNORECASE)
            svg_result = pattern.sub(norm_map[fh_upper], svg_result)
            continue
            
        # 2. Coincidencia aproximada por cercanía (tolerancia de compresión de vtracer)
        fh_rgb = hex_to_rgb(fh)
        best_match = None
        min_dist = 999.0
        for orig_hex, new_hex in norm_map.items():
            dist = color_distance(fh_rgb, hex_to_rgb(orig_hex))
            if dist < 22.0 and dist < min_dist:
                min_dist = dist
                best_match = new_hex
                
        if best_match:
            pattern = re.compile(re.escape(fh), re.IGNORECASE)
            svg_result = pattern.sub(best_match, svg_result)
            
    return svg_result


def remap_image_pixels(
    image: Image.Image,
    color_map: Dict[str, str],
    tolerance: float = 20.0
) -> Image.Image:
    """
    Reemplaza los píxeles de la imagen raster según el color_map.
    """
    if not color_map:
        return image
        
    arr = np.array(image)
    if arr.shape[-1] < 4:
        return image
        
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3]
    
    for orig_hex, new_hex in color_map.items():
        if orig_hex.upper() == new_hex.upper():
            continue
        orig_rgb = np.array(hex_to_rgb(orig_hex), dtype=np.float32)
        target_rgb = np.array(hex_to_rgb(new_hex), dtype=np.uint8)
        
        # Distancia a los píxeles
        dist = np.sqrt(np.sum((rgb - orig_rgb) ** 2, axis=2))
        mask = (dist <= tolerance) & (alpha > 20)
        
        arr[mask, :3] = target_rgb
        
    return Image.fromarray(arr, mode="RGBA")


def remap_palette(palette: List[Dict], color_map: Dict[str, str]) -> List[Dict]:
    """
    Actualiza la lista de paleta con los nuevos colores elegidos por el usuario.
    """
    new_palette = []
    norm_map = {k.upper(): v.upper() for k, v in color_map.items()}
    
    for item in palette:
        entry = item.copy()
        current_hex = entry["hex"].upper()
        if current_hex in norm_map:
            new_h = norm_map[current_hex]
            entry["hex"] = new_h
            entry["rgb"] = hex_to_rgb(new_h)
        new_palette.append(entry)
        
    return new_palette


def render_svg_to_image(
    svg_content: str,
    target_width: int = 1200,
    target_height: int = 1200
) -> Optional[Image.Image]:
    """
    Renderiza el SVG vectorial puro a una imagen PIL RGBA en altísima resolución
    utilizando resvg (motor Rust de precisión milimétrica).
    Garantiza que la simulación de tapete muestre el vector real y no el raster original sucio.
    """
    try:
        # Extraer aspect ratio original del SVG si está disponible
        viewbox_match = re.search(r'viewBox=[\'"][0-9\.\s]+[\s]+([0-9\.]+)[\s]+([0-9\.]+)[\'"]', svg_content)
        w_attr = re.search(r'\bwidth=[\'"]([0-9\.]+)[\'"]', svg_content)
        h_attr = re.search(r'\bheight=[\'"]([0-9\.]+)[\'"]', svg_content)
        
        orig_w, orig_h = 600, 600
        if viewbox_match:
            orig_w = float(viewbox_match.group(1))
            orig_h = float(viewbox_match.group(2))
        elif w_attr and h_attr:
            orig_w = float(w_attr.group(1))
            orig_h = float(h_attr.group(1))
            
        # Calcular dimensiones manteniendo el aspect ratio original del vector
        aspect = orig_w / max(1.0, orig_h)
        if aspect >= 1.0:
            render_w = target_width
            render_h = max(50, int(target_width / aspect))
        else:
            render_h = target_height
            render_w = max(50, int(target_height * aspect))
            
        png_bytes = resvg_py.svg_to_bytes(
            svg_string=svg_content,
            width=render_w,
            height=render_h
        )
        return Image.open(io.BytesIO(png_bytes))
    except Exception as e:
        print(f"Advertencia al renderizar SVG con resvg: {e}")
        return None
