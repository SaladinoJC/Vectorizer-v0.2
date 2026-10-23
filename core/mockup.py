"""
Módulo de generación de Mockups hiperrealistas de tapetes personalizados.
Permite simular cómo quedará el logo vectorizado en el tapete real:
- Formas: Rectangular con esquinas redondeadas o Circular.
- Texturas y materiales: Goma de alto tránsito, Felpa/Moqueta tufting, Fibra de coco beige, etc.
- Bordes: Chaflán de goma antirropiezos, Ribete overlock cosido o sin borde.
- Tamaños estándar: 60x40cm, 90x60cm, 120x80cm, etc.
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


# Paletas predefinidas de materiales de tapetes
RUG_MATERIALS: Dict[str, Dict[str, Any]] = {
    "goma_negra": {
        "name": "Goma Vulcanizada (Negro Carbón)",
        "base_color": (32, 33, 36),
        "border_color": (20, 20, 22),
        "texture_noise": 10,
        "border_type": "caucho"
    },
    "moqueta_gris": {
        "name": "Felpa / Moqueta Tufting (Gris Grafito)",
        "base_color": (55, 58, 64),
        "border_color": (30, 32, 35),
        "texture_noise": 18,
        "border_type": "ribete"
    },
    "coco_natural": {
        "name": "Fibra de Coco Natural (Beige Rústico)",
        "base_color": (195, 160, 115),
        "border_color": (40, 35, 30),
        "texture_noise": 26,
        "border_type": "ribete"
    },
    "moqueta_marino": {
        "name": "Felpa Tufting (Azul Marino Profundo)",
        "base_color": (24, 38, 62),
        "border_color": (15, 22, 36),
        "texture_noise": 16,
        "border_type": "ribete"
    },
    "moqueta_borgoña": {
        "name": "Felpa Tufting (Rojo Borgoña Elegante)",
        "base_color": (95, 24, 36),
        "border_color": (50, 15, 20),
        "texture_noise": 16,
        "border_type": "ribete"
    },
    "personalizado": {
        "name": "Color Personalizado",
        "base_color": (45, 45, 50),
        "border_color": (25, 25, 28),
        "texture_noise": 14,
        "border_type": "caucho"
    }
}


def add_subtle_texture(image: Image.Image, noise_strength: int = 15) -> Image.Image:
    """Añade una textura granular sutil simulando fibras textiles de alfombra o grano de goma."""
    if noise_strength <= 0:
        return image
        
    arr = np.array(image, dtype=np.int16)
    h, w, c = arr.shape
    
    # Generar ruido gaussiano
    noise = np.random.normal(0, noise_strength / 2.0, (h, w, 1)).astype(np.int16)
    
    # Aplicar ruido sólo a canales RGB, no al alpha
    arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)
    
    return Image.fromarray(arr.astype(np.uint8), mode="RGBA")


def create_rug_mockup(
    logo_image: Image.Image,
    material_key: str = "goma_negra",
    custom_base_color: Optional[Tuple[int, int, int]] = None,
    shape: str = "rect",            # 'rect' o 'round'
    aspect_ratio: str = "60x40",     # '60x40', '75x45', '90x60', '120x80', '100x100'
    border_style: str = "caucho",    # 'caucho', 'ribete', 'ninguno'
    logo_scale: float = 0.65,        # 0.4 a 0.85 del área del tapete
    add_shadow: bool = True
) -> Image.Image:
    """
    Genera una maqueta (mockup) fotorrealista del tapete terminado con el logo centrado.
    """
    # Dimensiones del lienzo final (alta resolución para preview y WhatsApp)
    canvas_w = 1200
    
    # Calcular alto según proporción
    if shape == "round":
        canvas_h = 1200
    elif aspect_ratio == "60x40" or aspect_ratio == "90x60" or aspect_ratio == "120x80":
        canvas_h = int(canvas_w * (40.0 / 60.0))  # 800px
    elif aspect_ratio == "75x45":
        canvas_h = int(canvas_w * (45.0 / 75.0))  # 720px
    else:
        canvas_h = 800
        
    # Obtener configuración del material
    mat = RUG_MATERIALS.get(material_key, RUG_MATERIALS["goma_negra"]).copy()
    base_color = custom_base_color if (material_key == "personalizado" and custom_base_color) else mat["base_color"]
    border_color = mat["border_color"]
    
    # Margen exterior del lienzo para sombra proyectada
    margin = 70
    rug_x1 = margin
    rug_y1 = margin
    rug_x2 = canvas_w - margin
    rug_y2 = canvas_h - margin
    rug_w = rug_x2 - rug_x1
    rug_h = rug_y2 - rug_y1
    
    # Crear lienzo base transparente
    canvas_img = Image.new("RGBA", (canvas_w, canvas_h), (245, 246, 248, 255))
    
    # 1. Sombra exterior del tapete sobre el suelo
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_img)
    shadow_offset_y = 18
    
    if shape == "round":
        shadow_box = [rug_x1, rug_y1 + shadow_offset_y, rug_x2, rug_y2 + shadow_offset_y]
        shadow_draw.ellipse(shadow_box, fill=(0, 0, 0, 95))
    else:
        shadow_box = [rug_x1, rug_y1 + shadow_offset_y, rug_x2, rug_y2 + shadow_offset_y]
        shadow_draw.rounded_rectangle(shadow_box, radius=35, fill=(0, 0, 0, 95))
        
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=22))
    canvas_img.paste(shadow_img, (0, 0), shadow_img)
    
    # 2. Tapete base
    rug_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    rug_draw = ImageDraw.Draw(rug_layer)
    
    border_thickness = 32 if border_style != "ninguno" else 0
    corner_radius = 32
    
    if shape == "round":
        # Borde exterior
        if border_style != "ninguno":
            rug_draw.ellipse([rug_x1, rug_y1, rug_x2, rug_y2], fill=(*border_color, 255))
            rug_draw.ellipse(
                [rug_x1 + border_thickness, rug_y1 + border_thickness,
                 rug_x2 - border_thickness, rug_y2 - border_thickness],
                fill=(*base_color, 255)
            )
        else:
            rug_draw.ellipse([rug_x1, rug_y1, rug_x2, rug_y2], fill=(*base_color, 255))
    else:
        # Rectangular
        if border_style != "ninguno":
            rug_draw.rounded_rectangle(
                [rug_x1, rug_y1, rug_x2, rug_y2],
                radius=corner_radius,
                fill=(*border_color, 255)
            )
            inner_radius = max(8, corner_radius - int(border_thickness * 0.7))
            rug_draw.rounded_rectangle(
                [rug_x1 + border_thickness, rug_y1 + border_thickness,
                 rug_x2 - border_thickness, rug_y2 - border_thickness],
                radius=inner_radius,
                fill=(*base_color, 255)
            )
        else:
            rug_draw.rounded_rectangle(
                [rug_x1, rug_y1, rug_x2, rug_y2],
                radius=corner_radius,
                fill=(*base_color, 255)
            )
            
    # Añadir textura sutil al tapete
    rug_layer = add_subtle_texture(rug_layer, noise_strength=mat.get("texture_noise", 14))
    
    # Si el borde es ribete cosido, dibujar línea interior punteada simulando costura
    if border_style == "ribete" and border_thickness > 0:
        stitch_draw = ImageDraw.Draw(rug_layer)
        stitch_inset = int(border_thickness * 0.5)
        stitch_col = (min(255, border_color[0] + 50), min(255, border_color[1] + 50), min(255, border_color[2] + 50), 180)
        
        if shape == "round":
            stitch_draw.ellipse(
                [rug_x1 + stitch_inset, rug_y1 + stitch_inset,
                 rug_x2 - stitch_inset, rug_y2 - stitch_inset],
                outline=stitch_col,
                width=2
            )
        else:
            stitch_draw.rounded_rectangle(
                [rug_x1 + stitch_inset, rug_y1 + stitch_inset,
                 rug_x2 - stitch_inset, rug_y2 - stitch_inset],
                radius=corner_radius - 8,
                outline=stitch_col,
                width=2
            )
            
    canvas_img.paste(rug_layer, (0, 0), rug_layer)
    
    # 3. Colocar el Logo centrado y escalado
    usable_w = rug_w - (border_thickness * 2) - 40
    usable_h = rug_h - (border_thickness * 2) - 40
    
    # Calcular tamaño objetivo del logo
    target_area_w = usable_w * logo_scale
    target_area_h = usable_h * logo_scale
    
    logo_aspect = logo_image.width / max(1, logo_image.height)
    
    if target_area_w / logo_aspect <= target_area_h:
        new_logo_w = int(target_area_w)
        new_logo_h = int(target_area_w / logo_aspect)
    else:
        new_logo_h = int(target_area_h)
        new_logo_w = int(target_area_h * logo_aspect)
        
    logo_resized = logo_image.resize((max(10, new_logo_w), max(10, new_logo_h)), Image.Resampling.LANCZOS)
    
    # Posición centrada
    pos_x = (canvas_w - new_logo_w) // 2
    pos_y = (canvas_h - new_logo_h) // 2
    
    # Efecto de relieve / ligera sombra si add_shadow es True
    if add_shadow:
        logo_shadow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        # Crear máscara de sombra a partir del alpha del logo
        logo_alpha = logo_resized.split()[3]
        shadow_shape = Image.new("RGBA", (new_logo_w, new_logo_h), (0, 0, 0, 70))
        logo_shadow.paste(shadow_shape, (pos_x + 2, pos_y + 4), mask=logo_alpha)
        logo_shadow = logo_shadow.filter(ImageFilter.GaussianBlur(radius=3))
        canvas_img.paste(logo_shadow, (0, 0), logo_shadow)
        
    # Pegar logo
    canvas_img.paste(logo_resized, (pos_x, pos_y), mask=logo_resized.split()[3])
    
    return canvas_img
