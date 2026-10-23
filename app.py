"""
Aplicación Web Streamlit: Vectorizador Automático de Logos para Tapetes Personalizados.
Permite convertir imágenes JPG/PNG a vectores limpios SVG/PDF, elegir y reemplazar
colores de hilado individualmente, simular tapetes fotorrealistas y generar fichas técnicas.
"""

import io
import zipfile
from pathlib import Path
from PIL import Image
import streamlit as st

from core.preprocessor import preprocess_for_vectorization, extract_palette
from core.vectorizer import vectorize_image, PRESETS
from core.exporter import svg_to_pdf_bytes, create_production_sheet_pdf, image_to_png_bytes
from core.mockup import create_rug_mockup, RUG_MATERIALS
from core.color_manager import (
    remap_svg_colors,
    remap_image_pixels,
    remap_palette,
    render_svg_to_image
)


st.set_page_config(
    page_title="Vectorizador de Tapetes",
    page_icon="🧶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para apariencia moderna
st.markdown("""
<style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .color-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-vector {
        background-color: #ECFDF5;
        color: #059669;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #A7F3D0;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


# Título principal
st.markdown('<div class="main-title">🧶 Vectorizador Automático para Tapetes Personalizados</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Convierte logos en JPG/PNG a vectores limpios (SVG/PDF), elige los colores exactos de tus hilados, simula el tapete con vector nítido y genera fichas de producción.</div>', unsafe_allow_html=True)


# --- SIDEBAR DE CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Configuración del Logo")
    
    # 1. Preset de Tapete
    preset_options = list(PRESETS.keys())
    preset_names = [PRESETS[k]["name"] for k in preset_options]
    selected_preset_idx = st.selectbox(
        "Tipo de Tapete / Técnica:",
        range(len(preset_options)),
        format_func=lambda i: preset_names[i],
        index=0
    )
    current_preset = preset_options[selected_preset_idx]
    st.caption(f"ℹ️ {PRESETS[current_preset]['description']}")
    
    st.markdown("---")
    st.subheader("🧹 Limpieza de Fondo")
    
    bg_mode = st.selectbox(
        "Tratamiento del fondo:",
        ["auto", "white", "black", "custom", "none"],
        format_func=lambda x: {
            "auto": "Automático (detectar borde)",
            "white": "Quitar fondo Blanco",
            "black": "Quitar fondo Negro",
            "custom": "Color personalizado",
            "none": "Conservar fondo original"
        }[x],
        index=0
    )
    
    custom_bg_rgb = (255, 255, 255)
    if bg_mode == "custom":
        bg_hex = st.color_picker("Selecciona color a remover:", "#FFFFFF")
        custom_bg_rgb = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        
    bg_tolerance = st.slider("Tolerancia de fondo:", min_value=10, max_value=80, value=35, step=5,
                             help="Mayor tolerancia elimina sombras o halos grises en bordes JPEG.")
    
    auto_crop = st.checkbox("Recortar márgenes vacíos (Auto-crop)", value=True)
    
    st.markdown("---")
    st.subheader("🎨 Control de Colores / Hilados")
    
    limit_colors = st.checkbox("Limitar cantidad de colores (K-Means)", value=True,
                               help="Ideal para tufting: reduce el logo al número exacto de colores de hilado a utilizar.")
    
    num_colors = 4
    if limit_colors:
        num_colors = st.slider("Número de colores:", min_value=2, max_value=12, value=4, step=1,
                               help="Define cuántos colores de hilado físico tendrá el diseño.")
        
    st.markdown("---")
    st.subheader("🔍 Filtros de Calidad")
    
    denoise_strength = st.slider("Reducción de ruido JPEG:", min_value=0, max_value=5, value=2,
                                 help="Suaviza el grano y artefactos de compresión sin perder esquinas.")
                                 
    min_speckle = st.slider("Eliminar manchas menores a (px):", min_value=1, max_value=30,
                            value=PRESETS[current_preset]["filter_speckle"],
                            help="Descarta piezas diminutas imposibles de tejer o cortar.")


# --- CONTENEDOR PRINCIPAL: PESTAÑAS ---
tab_single, tab_mockup, tab_sheet, tab_batch = st.tabs([
    "📐 Vectorizar y Elegir Colores",
    "🛋️ Simulador de Tapete (Mockup)",
    "📋 Ficha Técnica para Taller",
    "📦 Procesamiento por Lote"
])


# ==========================================
# PESTAÑA 1: VECTORIZAR Y PERSONALIZAR COLORES
# ==========================================
with tab_single:
    uploaded_file = st.file_uploader(
        "Carga el logo del cliente (JPG, PNG, WEBP):",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        key="single_uploader"
    )
    
    if uploaded_file is not None:
        try:
            # Control de cambio de archivo para reiniciar personalizaciones
            current_file_id = f"{uploaded_file.name}_{limit_colors}_{num_colors}_{current_preset}_{bg_mode}_{bg_tolerance}"
            if st.session_state.get("last_processed_file_id") != current_file_id:
                st.session_state["last_processed_file_id"] = current_file_id
                # Limpiar selecciones de color anteriores
                for k in list(st.session_state.keys()):
                    if k.startswith("user_color_"):
                        del st.session_state[k]
                        
            raw_image = Image.open(uploaded_file)
            
            # Preprocesamiento base
            with st.spinner("Procesando imagen base..."):
                base_cleaned_image, base_palette = preprocess_for_vectorization(
                    raw_image,
                    remove_bg=(bg_mode != "none"),
                    bg_mode=bg_mode,
                    custom_bg_color=custom_bg_rgb,
                    bg_tolerance=bg_tolerance,
                    denoise_strength=denoise_strength,
                    auto_crop=auto_crop,
                    limit_colors=limit_colors,
                    num_colors=num_colors
                )
                
                # Vectorización base
                vector_result = vectorize_image(
                    base_cleaned_image,
                    preset_key=current_preset,
                    custom_overrides={"filter_speckle": min_speckle}
                )
                base_svg = vector_result["svg"]
                path_count = vector_result["path_count"]
                
            # --- SECCIÓN: PERSONALIZAR COLORES DEL LOGO ---
            st.markdown("### 🎨 Selector y Personalización de Colores de Hilado")
            st.write("Aquí puedes cambiar cada uno de los colores detectados por el tono exacto de hilado, goma o vinilo que tengas en taller:")
            
            color_replacements = {}
            palette_cols = st.columns(min(6, max(1, len(base_palette))))
            
            for i, p in enumerate(base_palette[:12]):
                col_widget = palette_cols[i % len(palette_cols)]
                with col_widget:
                    orig_hex = p["hex"].upper()
                    picker_key = f"user_color_{i}_{uploaded_file.name}"
                    
                    # Selector interactivo de color
                    chosen_hex = st.color_picker(
                        f"Color {i+1} ({p['percent']}%)",
                        value=st.session_state.get(picker_key, orig_hex),
                        key=picker_key
                    ).upper()
                    
                    st.caption(f"Original: `{orig_hex}`")
                    if chosen_hex != orig_hex:
                        color_replacements[orig_hex] = chosen_hex
                        
            # Botón para restablecer colores si se cambió alguno
            if color_replacements:
                st.info(f"✨ Personalizaste {len(color_replacements)} color(es). Todos los vectores (SVG, PDF) y el simulador de tapete se han actualizado.")
                if st.button("🔄 Restablecer a los colores originales detectados"):
                    for k in list(st.session_state.keys()):
                        if k.startswith("user_color_"):
                            del st.session_state[k]
                    st.rerun()
                    
            # Aplicar remapeo de colores en SVG, paleta e imagen
            if color_replacements:
                final_svg = remap_svg_colors(base_svg, color_replacements)
                final_palette = remap_palette(base_palette, color_replacements)
                final_cleaned_image = remap_image_pixels(base_cleaned_image, color_replacements)
            else:
                final_svg = base_svg
                final_palette = base_palette
                final_cleaned_image = base_cleaned_image
                
            # Renderizar el vector puro en alta resolución usando resvg
            with st.spinner("Renderizando vector de alta precisión..."):
                vector_rendered_image = render_svg_to_image(final_svg, target_width=1200, target_height=1200)
                if vector_rendered_image is None:
                    vector_rendered_image = final_cleaned_image
                    
            # Guardar en session_state para las demás pestañas
            st.session_state["cleaned_image"] = final_cleaned_image
            st.session_state["vector_rendered_image"] = vector_rendered_image
            st.session_state["svg_content"] = final_svg
            st.session_state["palette"] = final_palette
            st.session_state["file_stem"] = Path(uploaded_file.name).stem
            st.session_state["preset_used"] = PRESETS[current_preset]["name"]
            
            st.markdown("---")
            
            # Métricas del vector
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Trazados (Paths)", f"{path_count}")
            with m2:
                st.metric("Colores en Diseño", f"{len(final_palette)}")
            with m3:
                st.metric("Resolución Base", f"{final_cleaned_image.width} × {final_cleaned_image.height} px")
            with m4:
                st.metric("Modo Vectorial", PRESETS[current_preset]["hierarchical"].capitalize())
                
            st.markdown("---")
            
            # Vista comparativa lado a lado
            col_orig, col_clean, col_svg = st.columns(3)
            
            with col_orig:
                st.subheader("1. Imagen Original")
                st.image(raw_image, use_container_width=True)
                st.caption(f"Archivo: {uploaded_file.name} ({raw_image.width}×{raw_image.height} px)")
                
            with col_clean:
                st.subheader("2. Fondo Limpio & Cuantizado")
                st.image(final_cleaned_image, use_container_width=True)
                st.caption(f"Fondo transparente, reducido a {len(final_palette)} colores")
                
            with col_svg:
                st.subheader("3. Vector Final (SVG / Curvas)")
                st.markdown(
                    f'<div style="background-color: #FAFAFA; border: 1px dashed #CBD5E0; border-radius: 8px; padding: 12px; text-align: center;">{final_svg}</div>',
                    unsafe_allow_html=True
                )
                st.caption("✨ Trazados vectoriales con los colores seleccionados")
                
            st.markdown("---")
            
            # Descargas
            st.subheader("📥 Descargar Archivos de Fabricación")
            d1, d2, d3 = st.columns(3)
            
            # 1. SVG
            with d1:
                st.download_button(
                    label="⬇️ Descargar .SVG (Vectorial)",
                    data=final_svg,
                    file_name=f"{st.session_state['file_stem']}_vector.svg",
                    mime="image/svg+xml",
                    use_container_width=True
                )
                st.caption("Para Adobe Illustrator, CorelDraw, Inkscape o máquinas de corte.")
                
            # 2. PDF Vectorial
            with d2:
                try:
                    pdf_vector_bytes = svg_to_pdf_bytes(final_svg)
                    st.download_button(
                        label="⬇️ Descargar .PDF Vectorial",
                        data=pdf_vector_bytes,
                        file_name=f"{st.session_state['file_stem']}_vector.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.caption("Para enviar a talleres o imprentas que solicitan PDF vectorial.")
                except Exception as e:
                    st.warning(f"No se pudo generar PDF: {e}")
                    
            # 3. PNG Alta Resolución
            with d3:
                png_bytes = image_to_png_bytes(vector_rendered_image, scale_factor=1)
                st.download_button(
                    label="⬇️ Descargar .PNG Vector Renderizado",
                    data=png_bytes,
                    file_name=f"{st.session_state['file_stem']}_vector_render.png",
                    mime="image/png",
                    use_container_width=True
                )
                st.caption("Renderizado nítido del vector sin fondo en alta resolución.")
                
        except Exception as ex:
            st.error(f"Error al procesar la imagen: {ex}")
    else:
        st.info("👆 Por favor sube una imagen de logo arriba para comenzar.")


# ==========================================
# PESTAÑA 2: SIMULADOR DE TAPETE (MOCKUP)
# ==========================================
with tab_mockup:
    st.subheader("🛋️ Simulador Fotorrealista de Tapete")
    st.markdown('<span class="badge-vector">✨ Mostrando el logo en VECTOR PURO (100% nítido, con tus colores y sin ruido)</span>', unsafe_allow_html=True)
    st.write("Genera una vista previa del producto final para enviarle al cliente por WhatsApp y cerrar la venta.")
    
    if "vector_rendered_image" in st.session_state or "svg_content" in st.session_state:
        # Usar el logo vectorizado nítido en lugar del raster sucio
        logo_to_mockup = st.session_state.get("vector_rendered_image", st.session_state.get("cleaned_image"))
        
        cfg1, cfg2, cfg3, cfg4 = st.columns(4)
        
        with cfg1:
            mat_keys = list(RUG_MATERIALS.keys())
            mat_names = [RUG_MATERIALS[k]["name"] for k in mat_keys]
            sel_mat_idx = st.selectbox(
                "Material / Base del Tapete:",
                range(len(mat_keys)),
                format_func=lambda i: mat_names[i],
                index=0,
                key="mockup_mat_select"
            )
            selected_mat = mat_keys[sel_mat_idx]
            
            custom_rug_color = (45, 45, 50)
            if selected_mat == "personalizado":
                c_hex = st.color_picker("Color base del tapete:", "#2D3748", key="mockup_custom_bg")
                custom_rug_color = tuple(int(c_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
                
        with cfg2:
            rug_shape = st.selectbox(
                "Forma del Tapete:",
                ["rect", "round"],
                format_func=lambda s: "Rectangular" if s == "rect" else "Redondo / Circular",
                key="mockup_shape_select"
            )
            
        with cfg3:
            rug_aspect = st.selectbox(
                "Medida Estándar:",
                ["60x40", "75x45", "90x60", "120x80"],
                format_func=lambda a: {
                    "60x40": "60 × 40 cm (Entrada estándar)",
                    "75x45": "75 × 45 cm (Mediano)",
                    "90x60": "90 × 60 cm (Comercial)",
                    "120x80": "120 × 80 cm (Corporativo / Doble)"
                }[a] if rug_shape == "rect" else "80 × 80 cm (Circular)",
                key="mockup_aspect_select"
            )
            
        with cfg4:
            rug_border = st.selectbox(
                "Terminación de Borde:",
                ["caucho", "ribete", "ninguno"],
                format_func=lambda b: {
                    "caucho": "Borde de goma antirropiezos",
                    "ribete": "Ribete cosido de hilo (Overlock)",
                    "ninguno": "Sin borde visible"
                }[b],
                key="mockup_border_select"
            )
            
        logo_scale = st.slider("Tamaño del logo dentro del tapete (%):", min_value=35, max_value=85, value=65, step=5, key="mockup_scale_slider")
        
        # Generar Mockup con el vector real
        with st.spinner("Renderizando simulación con el logo vectorial..."):
            mockup_image = create_rug_mockup(
                logo_to_mockup,
                material_key=selected_mat,
                custom_base_color=custom_rug_color,
                shape=rug_shape,
                aspect_ratio=rug_aspect,
                border_style=rug_border,
                logo_scale=logo_scale / 100.0,
                add_shadow=True
            )
            st.session_state["mockup_image"] = mockup_image
            
        # Mostrar Mockup
        st.image(mockup_image, use_container_width=True)
        
        # Descarga de Mockup
        mockup_bytes = image_to_png_bytes(mockup_image)
        st.download_button(
            label="📲 Descargar Mockup para WhatsApp (.PNG)",
            data=mockup_bytes,
            file_name=f"{st.session_state.get('file_stem', 'tapete')}_mockup_cliente.png",
            mime="image/png",
            use_container_width=True
        )
    else:
        st.info("Primero sube y vectoriza un logo en la pestaña '📐 Vectorizar y Elegir Colores'.")


# ==========================================
# PESTAÑA 3: FICHA TÉCNICA DE PRODUCCIÓN (PDF)
# ==========================================
with tab_sheet:
    st.subheader("📋 Generador de Ficha Técnica para Fabricación")
    st.write("Exporta un documento PDF oficial con la simulación vectorial, medidas del tapete y la tabla de hilados con códigos de color exactos para el taller.")
    
    if "palette" in st.session_state:
        f1, f2 = st.columns(2)
        with f1:
            client_input = st.text_input("Nombre del Cliente / Empresa:", value="Restaurante / Empresa")
            size_input = st.text_input("Dimensiones del Tapete:", value="60 × 40 cm")
        with f2:
            material_input = st.text_input("Técnica / Material:", value="Tufting / Hilado Acrílico")
            notes_input = st.text_area("Observaciones para taller:", value="Verificar tonos con muestra de hilado antes de comenzar el tufting.")
            
        if st.button("📄 Generar Ficha Técnica en PDF", use_container_width=True):
            with st.spinner("Creando PDF de producción con datos vectoriales..."):
                mockup_to_use = st.session_state.get("mockup_image", None)
                logo_to_use = st.session_state.get("vector_rendered_image", st.session_state.get("cleaned_image"))
                
                sheet_pdf_bytes = create_production_sheet_pdf(
                    logo_image=logo_to_use,
                    mockup_image=mockup_to_use,
                    palette=st.session_state["palette"],
                    client_name=client_input,
                    rug_size=size_input,
                    rug_material=material_input,
                    preset_name=st.session_state.get("preset_used", "Tapete Estándar")
                )
                
            st.success("¡Ficha técnica generada correctamente con los colores actualizados!")
            st.download_button(
                label="⬇️ Descargar Ficha Técnica (.PDF)",
                data=sheet_pdf_bytes,
                file_name=f"{st.session_state.get('file_stem', 'cliente')}_ficha_produccion.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.info("Primero sube y procesa un logo en la pestaña '📐 Vectorizar y Elegir Colores'.")


# ==========================================
# PESTAÑA 4: PROCESAMIENTO POR LOTE (BATCH)
# ==========================================
with tab_batch:
    st.subheader("📦 Procesar Múltiples Logos a la Vez")
    st.write("Sube varios archivos a la vez para vectorizarlos en lote y descargarlos en un único archivo comprimido (.ZIP).")
    
    batch_files = st.file_uploader(
        "Selecciona múltiples logos (JPG, PNG):",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="batch_uploader"
    )
    
    if batch_files:
        st.write(f"Se seleccionaron **{len(batch_files)}** archivos.")
        
        if st.button("🚀 Iniciar Vectorización por Lote"):
            zip_buffer = io.BytesIO()
            progress_bar = st.progress(0)
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, file in enumerate(batch_files):
                    try:
                        img = Image.open(file)
                        cleaned, pal = preprocess_for_vectorization(
                            img,
                            remove_bg=(bg_mode != "none"),
                            bg_mode=bg_mode,
                            custom_bg_color=custom_bg_rgb,
                            bg_tolerance=bg_tolerance,
                            denoise_strength=denoise_strength,
                            auto_crop=auto_crop,
                            limit_colors=limit_colors,
                            num_colors=num_colors
                        )
                        v_res = vectorize_image(cleaned, preset_key=current_preset)
                        stem = Path(file.name).stem
                        
                        # Agregar SVG
                        zip_file.writestr(f"{stem}/{stem}.svg", v_res["svg"])
                        
                        # Agregar PDF Vectorial
                        try:
                            pdf_b = svg_to_pdf_bytes(v_res["svg"])
                            zip_file.writestr(f"{stem}/{stem}.pdf", pdf_b)
                        except Exception:
                            pass
                            
                        # Agregar Mockup con vector nítido
                        try:
                            v_img = render_svg_to_image(v_res["svg"], target_width=1200, target_height=1200)
                            logo_m = v_img if v_img is not None else cleaned
                            m_img = create_rug_mockup(logo_m, material_key="goma_negra")
                            m_bytes = image_to_png_bytes(m_img)
                            zip_file.writestr(f"{stem}/{stem}_mockup.png", m_bytes)
                        except Exception:
                            pass
                            
                    except Exception as err:
                        st.warning(f"Error procesando {file.name}: {err}")
                        
                    progress_bar.progress((idx + 1) / len(batch_files))
                    
            st.success(f"¡Lote completado! {len(batch_files)} logos vectorizados.")
            st.download_button(
                label="⬇️ Descargar Todos en Archivo ZIP",
                data=zip_buffer.getvalue(),
                file_name="logos_vectorizados_tapetes.zip",
                mime="application/zip",
                use_container_width=True
            )
