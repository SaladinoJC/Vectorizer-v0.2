"""
Script para generar logos de prueba y verificar el funcionamiento del vectorizador.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_sample_logos():
    out_dir = Path("sample_logos")
    out_dir.mkdir(exist_ok=True)
    
    # 1. Logo Cafetería (con fondo blanco JPEG típico de cliente)
    w, h = 600, 600
    img1 = Image.new("RGB", (w, h), (255, 255, 255))
    d1 = ImageDraw.Draw(img1)
    
    # Círculo exterior e interior
    d1.ellipse([40, 40, w - 40, h - 40], outline=(111, 78, 55), width=12)
    d1.ellipse([70, 70, w - 70, h - 70], outline=(200, 160, 120), width=4)
    
    # Taza de café estilizada en el centro
    # Base de taza
    d1.pieslice([180, 240, 420, 480], 0, 180, fill=(111, 78, 55))
    # Asa de taza
    d1.arc([380, 260, 470, 360], 270, 90, fill=(111, 78, 55), width=12)
    # Granos de café / detalles
    d1.ellipse([270, 160, 330, 210], fill=(160, 82, 45))
    d1.line([300, 160, 300, 210], fill=(255, 255, 255), width=3)
    
    # Guardar como JPEG con compresión típica para probar remoción de artefactos
    img1.save(out_dir / "logo_cafeteria.jpg", format="JPEG", quality=85)
    print(f"Creado: {out_dir / 'logo_cafeteria.jpg'}")
    
    # 2. Logo Gimnasio (Borde geométrico y formas sólidas)
    img2 = Image.new("RGB", (600, 400), (248, 249, 250))
    d2 = ImageDraw.Draw(img2)
    
    # Mancuerna / Símbolo fitness
    # Barra
    d2.rectangle([140, 185, 460, 215], fill=(30, 41, 59))
    # Discos izquierda
    d2.rounded_rectangle([180, 110, 220, 290], radius=8, fill=(239, 68, 68))
    d2.rounded_rectangle([130, 130, 170, 270], radius=8, fill=(239, 68, 68))
    # Discos derecha
    d2.rounded_rectangle([380, 110, 420, 290], radius=8, fill=(239, 68, 68))
    d2.rounded_rectangle([430, 130, 470, 270], radius=8, fill=(239, 68, 68))
    # Agarre centro
    d2.rectangle([270, 180, 330, 220], fill=(203, 213, 225))
    
    img2.save(out_dir / "logo_gimnasio.jpg", format="JPEG", quality=88)
    print(f"Creado: {out_dir / 'logo_gimnasio.jpg'}")


if __name__ == "__main__":
    create_sample_logos()
