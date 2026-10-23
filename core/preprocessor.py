"""
Módulo de preprocesamiento de imágenes para preparación de logos antes de vectorizar.
Diseñado específicamente para tapetes personalizados:
- Remoción de fondos (blanco, JPEG halo, color sólido o automático).
- Reducción de ruido JPEG y suavizado de bordes (filtro bilateral).
- Cuantización / reducción a N colores reales de hilado/material (K-Means).
- Recorte automático de márgenes vacíos (Auto-crop).
- Extracción de paleta de colores con códigos HEX y porcentajes.
"""

from typing import Tuple, List, Dict, Optional
import numpy as np
import cv2
from PIL import Image


def ensure_rgba(image: Image.Image) -> Image.Image:
    """Convierte cualquier imagen PIL (CMYK, P, L, RGB, etc.) a modo RGBA."""
    if image.mode == "RGBA":
        return image.copy()
    if image.mode == "CMYK":
        return image.convert("RGB").convert("RGBA")
    if image.mode == "P":
        return image.convert("RGBA")
    return image.convert("RGBA")


def detect_background_color(image: Image.Image) -> Tuple[int, int, int]:
    """
    Detecta automáticamente el color de fondo predominante analizando
    los bordes y las 4 esquinas de la imagen.
    """
    img_rgb = image.convert("RGB")
    arr = np.array(img_rgb)
    h, w, _ = arr.shape
    
    # Tomar muestras de los bordes exteriores (5% del tamaño o mín 5px)
    bx = max(5, int(w * 0.05))
    by = max(5, int(h * 0.05))
    
    top = arr[:by, :].reshape(-1, 3)
    bottom = arr[-by:, :].reshape(-1, 3)
    left = arr[:, :bx].reshape(-1, 3)
    right = arr[:, -bx:].reshape(-1, 3)
    
    border_pixels = np.vstack([top, bottom, left, right])
    
    # Color promedio o mediano de los bordes
    median_color = np.median(border_pixels, axis=0).astype(int)
    return tuple(int(c) for c in median_color)


def remove_background(
    image: Image.Image,
    bg_mode: str = "auto",
    custom_color: Tuple[int, int, int] = (255, 255, 255),
    tolerance: int = 35,
    remove_halo: bool = True
) -> Image.Image:
    """
    Elimina el fondo sólido de la imagen convirtiéndolo en transparente.
    
    Args:
        image: Imagen PIL.
        bg_mode: 'auto' (detecta bordes), 'white' (blanco), 'black' (negro),
                 'custom' (usa custom_color), o 'none' (no hace nada).
        custom_color: Color RGB a eliminar si bg_mode=='custom'.
        tolerance: Distancia de tolerancia para considerar un pixel como fondo (0-100).
        remove_halo: Si True, elimina el halo blanco/gris residual de los bordes de compresión JPEG.
    """
    if bg_mode == "none":
        return ensure_rgba(image)
        
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3].copy()
    
    if bg_mode == "auto":
        target_color = detect_background_color(image)
    elif bg_mode == "white":
        target_color = (255, 255, 255)
    elif bg_mode == "black":
        target_color = (0, 0, 0)
    elif bg_mode == "custom":
        target_color = custom_color
    else:
        return rgba
        
    target = np.array(target_color, dtype=np.float32)
    
    # Distancia euclídea al color de fondo
    dist = np.sqrt(np.sum((rgb - target) ** 2, axis=2))
    
    # Máscara de píxeles que pertenecen al fondo
    bg_mask = dist <= float(tolerance)
    
    # Si remove_halo está activo, dilatamos un poco la máscara de fondo
    # para matar el halo intermedio que deja la compresión JPEG
    if remove_halo and tolerance > 15:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bg_mask_uint8 = (bg_mask.astype(np.uint8)) * 255
        bg_mask_uint8 = cv2.dilate(bg_mask_uint8, kernel, iterations=1)
        bg_mask = bg_mask_uint8 > 0
        
    alpha[bg_mask] = 0
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, mode="RGBA")


def denoise_image(image: Image.Image, strength: int = 3) -> Image.Image:
    """
    Aplica filtro bilateral para eliminar ruido de artefactos JPEG sin desenfocar los bordes.
    Ideal para logos enviados por WhatsApp que vienen comprimidos.
    """
    if strength <= 0:
        return image
        
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    
    d = int(strength * 2 + 3)
    sigma_color = float(strength * 18)
    sigma_space = float(strength * 18)
    
    filtered_rgb = cv2.bilateralFilter(rgb, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)
    
    # Preservar el canal alfa original
    arr[:, :, :3] = filtered_rgb
    arr[:, :, 3] = alpha
    return Image.fromarray(arr, mode="RGBA")


def autocrop_image(image: Image.Image, padding: int = 15) -> Image.Image:
    """
    Recorta los márgenes vacíos o transparentes alrededor del logo
    y agrega un relleno pequeño simétrico.
    """
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    alpha = arr[:, :, 3]
    
    # Encontrar píxeles no transparentes
    coords = cv2.findNonZero((alpha > 15).astype(np.uint8))
    if coords is None:
        return image
        
    x, y, w, h = cv2.boundingRect(coords)
    
    # Aplicar padding
    img_h, img_w = arr.shape[:2]
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(img_w, x + w + padding)
    y2 = min(img_h, y + h + padding)
    
    cropped = rgba.crop((x1, y1, x2, y2))
    return cropped


def quantize_colors_kmeans(
    image: Image.Image,
    num_colors: int = 4
) -> Tuple[Image.Image, List[Dict]]:
    """
    Reduce la imagen exactamente a N colores usando K-Means sobre píxeles no transparentes.
    Esto es crucial para tapetes ya que cada color representa un hilado o material distinto.
    
    Returns:
        (imagen_cuantizada_rgba, lista_paleta_colores)
    """
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    
    # Máscara de píxeles visibles
    visible_mask = alpha > 25
    visible_pixels = rgb[visible_mask].astype(np.float32)
    
    if len(visible_pixels) == 0:
        return rgba, []
        
    # Limitar número de clusters al número de colores únicos disponibles
    unique_pixels = np.unique(visible_pixels, axis=0)
    actual_k = min(num_colors, len(unique_pixels))
    
    if actual_k <= 1:
        color = np.median(visible_pixels, axis=0).astype(np.uint8)
        new_rgb = np.zeros_like(rgb)
        new_rgb[visible_mask] = color
        arr[:, :, :3] = new_rgb
        hex_color = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        palette = [{"hex": hex_color, "rgb": tuple(int(c) for c in color), "percent": 100.0, "count": len(visible_pixels)}]
        return Image.fromarray(arr, mode="RGBA"), palette
        
    # K-Means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 0.5)
    _, labels, centers = cv2.kmeans(
        visible_pixels,
        actual_k,
        None,
        criteria,
        10,
        cv2.KMEANS_PP_CENTERS
    )
    
    centers = np.clip(centers, 0, 255).astype(np.uint8)
    quantized_visible = centers[labels.flatten()]
    
    new_rgb = rgb.copy()
    new_rgb[visible_mask] = quantized_visible
    arr[:, :, :3] = new_rgb
    
    # Calcular estadísticas de la paleta
    total_visible = len(labels)
    unique_labels, counts = np.unique(labels, return_counts=True)
    
    # Ordenar por frecuencia descendente
    sorted_indices = np.argsort(-counts)
    
    palette = []
    for idx in sorted_indices:
        label = unique_labels[idx]
        count = counts[idx]
        color = centers[label]
        hex_color = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        percent = round(float(count) / total_visible * 100.0, 1)
        palette.append({
            "hex": hex_color,
            "rgb": tuple(int(c) for c in color),
            "percent": percent,
            "count": int(count)
        })
        
    return Image.fromarray(arr, mode="RGBA"), palette


def extract_palette(image: Image.Image, max_colors: int = 12) -> List[Dict]:
    """
    Extrae la paleta dominante de colores de una imagen RGBA sin alterarla.
    """
    rgba = ensure_rgba(image)
    arr = np.array(rgba)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    
    visible_mask = alpha > 25
    visible_pixels = rgb[visible_mask]
    
    if len(visible_pixels) == 0:
        return []
        
    # Muestrear si hay demasiados píxeles para velocidad
    if len(visible_pixels) > 50000:
        step = len(visible_pixels) // 50000
        visible_pixels = visible_pixels[::step]
        
    pixels_float = visible_pixels.astype(np.float32)
    k = min(max_colors, len(np.unique(visible_pixels, axis=0)))
    
    if k <= 0:
        return []
        
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels_float,
        k,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS
    )
    
    centers = np.clip(centers, 0, 255).astype(np.uint8)
    unique_labels, counts = np.unique(labels, return_counts=True)
    sorted_indices = np.argsort(-counts)
    total = len(labels)
    
    palette = []
    for idx in sorted_indices:
        label = unique_labels[idx]
        count = counts[idx]
        color = centers[label]
        hex_color = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        palette.append({
            "hex": hex_color,
            "rgb": tuple(int(c) for c in color),
            "percent": round(float(count) / total * 100.0, 1),
            "count": int(count)
        })
        
    return palette


def preprocess_for_vectorization(
    image: Image.Image,
    remove_bg: bool = True,
    bg_mode: str = "auto",
    custom_bg_color: Tuple[int, int, int] = (255, 255, 255),
    bg_tolerance: int = 35,
    denoise_strength: int = 2,
    auto_crop: bool = True,
    limit_colors: bool = False,
    num_colors: int = 4
) -> Tuple[Image.Image, List[Dict]]:
    """
    Canalización completa de preprocesamiento para logos de tapetes.
    """
    img = ensure_rgba(image)
    
    # 1. Remoción de fondo
    if remove_bg:
        img = remove_background(
            img,
            bg_mode=bg_mode,
            custom_color=custom_bg_color,
            tolerance=bg_tolerance,
            remove_halo=True
        )
        
    # 2. Recorte de bordes vacíos
    if auto_crop:
        img = autocrop_image(img, padding=12)
        
    # 3. Reducción de ruido JPEG
    if denoise_strength > 0:
        img = denoise_image(img, strength=denoise_strength)
        
    # 4. Reducción de colores (K-Means)
    if limit_colors and num_colors >= 2:
        img, palette = quantize_colors_kmeans(img, num_colors=num_colors)
    else:
        palette = extract_palette(img, max_colors=10)
        
    return img, palette
