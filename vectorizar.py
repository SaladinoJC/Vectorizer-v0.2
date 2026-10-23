"""
Herramienta de línea de comandos (CLI) y procesamiento por lotes para
vectorizar logos de clientes automáticamente para tapetes personalizados.

Uso:
    python vectorizar.py logo.jpg
    python vectorizar.py logo.png --preset tapete_geometric --colores 4 --mockup
    python vectorizar.py ./mis_logos/ --fondo auto --pdf --ficha
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from PIL import Image

from core.preprocessor import preprocess_for_vectorization
from core.vectorizer import vectorize_image, PRESETS
from core.exporter import svg_to_pdf_bytes, create_production_sheet_pdf, image_to_png_bytes
from core.mockup import create_rug_mockup
from core.color_manager import render_svg_to_image


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def process_single_image(
    input_path: Path,
    output_dir: Path,
    preset: str = "tapete_tufting",
    bg_mode: str = "auto",
    bg_tolerance: int = 35,
    num_colors: int = 0,
    denoise_strength: int = 2,
    generate_pdf: bool = True,
    generate_mockup: bool = True,
    generate_sheet: bool = True,
    client_name: str = "Cliente"
):
    print(f"\n[+] Procesando: {input_path.name}")
    
    try:
        raw_img = Image.open(input_path)
    except Exception as e:
        print(f"  [!] Error al abrir la imagen: {e}")
        return False
        
    stem = input_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Preprocesamiento
    limit_colors = num_colors >= 2
    print(f"  -> Limpiando fondo ({bg_mode}), eliminando ruido y preparando colores...")
    cleaned_img, palette = preprocess_for_vectorization(
        raw_img,
        remove_bg=(bg_mode != "none"),
        bg_mode=bg_mode,
        bg_tolerance=bg_tolerance,
        denoise_strength=denoise_strength,
        auto_crop=True,
        limit_colors=limit_colors,
        num_colors=num_colors if limit_colors else 4
    )
    
    # 2. Vectorización
    print(f"  -> Vectorizando con preset '{preset}'...")
    res = vectorize_image(cleaned_img, preset_key=preset)
    svg_content = res["svg"]
    path_count = res["path_count"]
    print(f"  -> ¡Vectorizado con éxito! {path_count} trazados generados.")
    
    # Guardar SVG
    svg_path = output_dir / f"{stem}_vectorizado.svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"  [OK] SVG guardado: {svg_path.name}")
    
    # 3. Exportar PDF Vectorial
    if generate_pdf:
        try:
            pdf_bytes = svg_to_pdf_bytes(svg_content)
            pdf_path = output_dir / f"{stem}_vectorizado.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"  [OK] PDF vectorial guardado: {pdf_path.name}")
        except Exception as e:
            print(f"  [!] No se pudo generar PDF vectorial: {e}")
            
    # 4. Generar Mockup del Tapete (usando el vector real y nítido)
    mockup_img = None
    vector_rendered = render_svg_to_image(svg_content, target_width=1200, target_height=1200)
    logo_for_mockup = vector_rendered if vector_rendered is not None else cleaned_img
    
    if generate_mockup or generate_sheet:
        try:
            mockup_img = create_rug_mockup(logo_for_mockup, material_key="goma_negra", aspect_ratio="60x40")
            if generate_mockup:
                mockup_path = output_dir / f"{stem}_tapete_mockup.png"
                mockup_img.save(mockup_path, format="PNG")
                print(f"  [OK] Mockup del tapete guardado: {mockup_path.name}")
        except Exception as e:
            print(f"  [!] Error al generar mockup: {e}")
            
    # 5. Generar Ficha Técnica de Producción
    if generate_sheet:
        try:
            sheet_bytes = create_production_sheet_pdf(
                logo_image=logo_for_mockup,
                mockup_image=mockup_img,
                palette=palette,
                client_name=client_name or stem,
                rug_size="60 x 40 cm",
                preset_name=PRESETS.get(preset, {}).get("name", preset)
            )
            sheet_path = output_dir / f"{stem}_ficha_produccion.pdf"
            with open(sheet_path, "wb") as f:
                f.write(sheet_bytes)
            print(f"  [OK] Ficha tecnica PDF guardada: {sheet_path.name}")
        except Exception as e:
            print(f"  [!] Error al generar ficha de produccion: {e}")
            
    print(f"  Colores detectados ({len(palette)}): {', '.join([c['hex'] for c in palette[:5]])}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Vectorizador Automático de Logos para Fabricación de Tapetes Personalizados."
    )
    parser.add_argument("input", help="Ruta a una imagen (JPG, PNG) o a una carpeta con imágenes")
    parser.add_argument("-o", "--output", default="output_vectorizados", help="Carpeta de salida (default: output_vectorizados)")
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="tapete_tufting",
        help="Preset de vectorización (default: tapete_tufting)"
    )
    parser.add_argument(
        "--fondo",
        choices=["auto", "white", "black", "none"],
        default="auto",
        help="Modo de remoción de fondo (default: auto)"
    )
    parser.add_argument(
        "--colores",
        type=int,
        default=0,
        help="Limitar a N colores exactos (ej: 2, 4, 6). 0 = automático"
    )
    parser.add_argument("--tolerancia", type=int, default=35, help="Tolerancia de fondo (0-100, default: 35)")
    parser.add_argument("--ruido", type=int, default=2, help="Fuerza de reducción de ruido (0-5, default: 2)")
    parser.add_argument("--no-pdf", action="store_true", help="No generar PDF vectorial")
    parser.add_argument("--no-mockup", action="store_true", help="No generar mockup de simulación")
    parser.add_argument("--no-ficha", action="store_true", help="No generar ficha técnica de producción")
    parser.add_argument("--cliente", default="", help="Nombre del cliente para la ficha técnica")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: La ruta '{input_path}' no existe.")
        sys.exit(1)
        
    targets = []
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            targets.append(input_path)
        else:
            print(f"Error: Formato '{input_path.suffix}' no soportado.")
            sys.exit(1)
    elif input_path.is_dir():
        for f in input_path.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                targets.append(f)
                
    if not targets:
        print("No se encontraron imágenes compatibles para procesar.")
        sys.exit(1)
        
    print(f"============================================================")
    print(f" VECTORIZADOR AUTOMÁTICO DE TAPETES - MODO POR LOTES / CLI")
    print(f" Imágenes a procesar: {len(targets)}")
    print(f" Preset: {args.preset} | Fondo: {args.fondo} | Colores: {args.colores or 'Auto'}")
    print(f" Carpeta de destino: {output_dir.resolve()}")
    print(f"============================================================")
    
    success = 0
    for t in targets:
        if process_single_image(
            t,
            output_dir,
            preset=args.preset,
            bg_mode=args.fondo,
            bg_tolerance=args.tolerancia,
            num_colors=args.colores,
            denoise_strength=args.ruido,
            generate_pdf=not args.no_pdf,
            generate_mockup=not args.no_mockup,
            generate_sheet=not args.no_ficha,
            client_name=args.cliente
        ):
            success += 1
            
    print(f"\n============================================================")
    print(f"[OK] Finalizado: {success}/{len(targets)} imagenes procesadas con exito.")
    print(f"Archivos disponibles en: {output_dir.resolve()}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
