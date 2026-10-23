# 🧶 Vectorizador Automático de Logos para Tapetes Personalizados

Herramienta diseñada específicamente para fabricantes y diseñadores de **tapetes, alfombras tufting, felpudos de goma vulcanizada y vinilo**.

Permite tomar cualquier logo enviado por clientes en formatos raster (**JPG, PNG, WEBP**), eliminar fondos automáticamente, limpiar ruido de compresión (ej. logos de WhatsApp), reducir a la cantidad exacta de colores de hilado y generar archivos vectoriales limpios (**SVG / PDF**), simuladores fotorrealistas de tapetes y fichas técnicas de producción.

---

## 🚀 Inicio Rápido (1 Clic en Windows)

1. Haz doble clic en el archivo **`Iniciar_Vectorizador.bat`**.
2. Se abrirá automáticamente la aplicación en tu navegador web (`http://localhost:8501`).
3. Arrastra el logo en JPG o PNG y ¡listo!

---

## ✨ Características Principales

### 1. Vectorización Optimizada para Tapetes
* **Sin solapamiento de formas (Modo Cutout)**: Las piezas vectoriales encajan como un rompecabezas, evitando encimar hilado o material innecesario.
* **Curvas Bezier suaves (Spline)**: Evita dientes de sierra o bordes puntiagudos difíciles de tejer o cortar.
* **Filtro de impurezas y motas (Speckle Filter)**: Elimina automáticamente puntos o manchas menores a N píxeles que las máquinas o tijeras rechazan.

### 2. Presets Especializados
* **Tapete Tufting / Alfombra Estándar (Recomendado)**: Suavizado de bordes y curvas continuas para hilado acrílico/lana.
* **Logo Geométrico y Tipografía**: Conserva esquinas nítidas y letras rectas sin deformarlas.
* **1 Color / Silueta / Vinilo**: Vector blanco y negro ideal para corte en plotter o grabado láser.
* **Por Capas Superpuestas**: Para serigrafía o estampado directo sobre felpa.
* **Alta Fidelidad**: Para ilustraciones complejas o logos con degradados escalonados.

### 3. Reducción y Personalización de Colores (Color Pickers)
* Los tapetes tienen limitaciones físicas de hilados/gomas. Puedes activar la reducción a **2, 3, 4, 6 u 8 colores exactos**.
* **Elige y reemplaza cada color:** Puedes hacer clic en cada color detectado y elegir con un selector de color el tono exacto del hilado que tienes en stock.
* Todos los archivos generados (**SVG, PDF vectorial, Mockup y Ficha técnica**) se actualizan automáticamente con los colores que elegiste.

### 4. Simulador Fotorrealista de Tapete con Vector Puro (Mockup para WhatsApp)
* **100% Vectorial:** El mockup renderiza el vector real (vía motor Rust `resvg`), garantizando bordes nítidos, curvas Bezier suaves y cero ruido de compresión o píxeles borrosos.
* Muestra al cliente cómo quedará su tapete antes de fabricarlo:
  * Medidas: 60x40 cm, 75x45 cm, 90x60 cm, 120x80 cm o Circular.
  * Materiales: Goma vulcanizada negra, Felpa gris grafito, Fibra de coco natural beige, Felpa azul marino, etc.
  * Bordes: Bisel de goma antirropiezos, Ribete cosido overlock o sin borde.
* Descarga directa en PNG para enviar por WhatsApp y cerrar el presupuesto.

### 5. Ficha Técnica de Producción (PDF)
* Genera un informe oficial para el operario de taller con:
  * Foto de la simulación.
  * Dimensiones y técnica de fabricación.
  * Tabla con muestras de color, códigos HEX, RGB y porcentajes.

---

## 💻 Uso desde Línea de Comandos (CLI / Lotes)

Si prefieres procesar logos desde la terminal o por lotes:

```bash
# Vectorizar un solo logo con valores por defecto
python vectorizar.py mi_logo.jpg

# Vectorizar limitando a 4 colores con mockup y ficha técnica para un cliente
python vectorizar.py mi_logo.png --colores 4 --cliente "Cafetería Roma"

# Procesar una carpeta entera con múltiples logos
python vectorizar.py ./carpeta_logos/ --fondo auto --pdf --ficha
```

### Opciones disponibles en CLI:
| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `--preset` | `tapete_tufting`, `tapete_geometric`, `tapete_monocromo`, etc. | `tapete_tufting` |
| `--fondo` | `auto`, `white`, `black`, `none` | `auto` |
| `--colores` | Número de colores exactos (ej: `2`, `4`, `6`, `0`=auto) | `0` |
| `--tolerancia` | Sensibilidad para eliminar fondo (10-80) | `35` |
| `--ruido` | Reducción de ruido JPEG (0 a 5) | `2` |
| `-o, --output` | Carpeta de salida | `output_vectorizados` |

---

## 📁 Estructura del Proyecto

```
vectorizer/
├── app.py                      # Interfaz gráfica interactiva Web (Streamlit)
├── vectorizar.py               # Herramienta de línea de comandos y por lotes
├── Iniciar_Vectorizador.bat    # Acceso directo para Windows
├── requirements.txt            # Dependencias del proyecto
├── core/
│   ├── preprocessor.py         # Limpieza de fondo, reducción de ruido y cuantización
│   ├── vectorizer.py           # Motor VTracer con presets para tapetes
│   ├── exporter.py             # Exportación a SVG, PDF y Ficha técnica
│   └── mockup.py               # Generador de simulación visual de tapetes
├── sample_logos/               # Logos de ejemplo para pruebas
└── output_vectorizados/        # Carpeta donde se guardan las exportaciones
```
