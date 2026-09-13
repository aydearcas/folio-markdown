# Estado de validación / Validation status

## Actualización · Folio 0.2.3

- **69/69 pruebas correctas, sin omisiones**, con Qt real offscreen en Linux. Se comprueban PDFium como valor inicial en opciones, interfaz y diagnóstico; activación explícita del lector experimental; migración de preferencias antiguas sin alterar otros ajustes; persistencia y traducciones.
- Conversión real con LiteParse repetida correctamente (PDF sintético, contenido, JSON y marcas de páginas).
- Inspección visual en español e inglés a 980 × 700: casilla del lector original desmarcada y advertencia legible. Capturas `screenshots/default_reader_023_es.png` y `screenshots/default_reader_023_en.png`.
- Docling/PDFium no se han ejecutado de nuevo en el entorno de desarrollo. El usuario ha confirmado una conversión real con PDFium en su Windows en 0.2.2; esta versión cambia valores iniciales y presentación, no sus modelos ni su implementación de lectura.

English: 69 automated tests passed, none skipped. Default selection, explicit experimental opt-in, settings migration, persistence and bilingual UI were checked. The actual LiteParse smoke test passed. Docling/PDFium conversion was not rerun in this development environment; the user previously confirmed conversion on Windows with 0.2.2.

## Actualización 2026-09-13 · Folio 0.2.2

- **67/67 pruebas correctas, sin omisiones**, Linux, Python 3.12.14, Qt real offscreen. Se añaden 6 pruebas para clasificar incidencias nativas, seleccionar PDFium y separar su caché, validar opciones, conservar/traducir ajustes y mostrar avisos tras una salida normal del proceso.
- API de PDFium contrastada con el código del paquete publicado `docling-slim==2.126.0`. Pruebas del adaptador con dobles explícitos: no ejecutan los modelos reales de Docling.
- Se repite correctamente la conversión real del PDF sintético con LiteParse: contenido, JSON y marcas de páginas. Se inspecciona el nuevo control en español e inglés a 980 × 700 (`screenshots/compatibility_es.png` y `compatibility_en.png`).
- Los registros del usuario muestran dos conversiones Docling completadas en Windows (sin OCR y con OCR), ambas con mensajes de excepciones nativas. No equivalen a una validación limpia de Docling ni validan esta nueva alternativa PDFium.
- **Corrección al informe anterior del icono:** el ICO contenido en el ZIP 0.2.1 estaba vacío. Se ha regenerado y decodificado cada una de las 7 imágenes, de 16 a 256 píxeles. Se añade comprobación previa al empaquetado para rechazar un ICO vacío. No se ha probado en el escritorio real de Windows.
- No se ha reproducido el cierre del artículo original ni se afirma que el cambio de lector lo resuelva. La comparación en el equipo afectado sigue pendiente.

English: 67 tests passed, none skipped. The alternative PDFium reader is supported by the inspected Docling 2.126.0 source; adapter tests use fakes. User-supplied Windows runs completed but contain native exception messages. PDFium conversion on that machine remains unverified. The previous ZIP's ICO was empty; the regenerated ICO was decoded at all seven sizes and the packager now rejects an empty ICO.

## Actualización 2026-09-13 · Folio 0.2.1

- **61/61 pruebas correctas, sin omisiones** en el mismo entorno Linux/Python 3.12.14/Qt offscreen descrito abajo.
- Se añaden 3 pruebas de diagnóstico: metadatos sin volcado de variables de entorno, límites del código de salida de Qt y ejecución real del subproceso de diagnóstico con documentos TXT, tanto éxito como error por archivo. Esta última valida el protocolo, no ejecuta Docling.
- Se añaden 2 pruebas Qt: menú contextual con paleta oscura simulada e icono cargable, y guardado real del registro mediante el botón (selector de destino simulado).
- Se repite correctamente la conversión **real con LiteParse**, PDF sintético de dos páginas, contenido, JSON y marcas de páginas.
- Se generan e inspeccionan las capturas `context_menu_dark_system.png`, `context_input_dark_system.png` e `interface_021.png`. Se corrigen también los colores de texto seleccionado en la previsualización.
- El PNG del icono se carga en Qt. El ICO se abre con Pillow y contiene 7 tamaños, de 16 a 256 píxeles. La integración nativa de icono/menús en Windows sigue pendiente.
- **Docling/EasyOCR y el cierre nativo de Windows no se han reproducido ni validado.** Esta versión facilita su diagnóstico; no confirma una solución del motor. No se han modificado versiones de dependencias ni opciones de Docling.

English: 61 tests passed, none skipped. Actual LiteParse conversion was repeated successfully. Diagnostics protocol, log saving and Qt popup rendering under a simulated dark palette were tested. Docling/OCR, native Windows crashes and native Windows icon integration remain untested. This release improves diagnostics; it does not establish or fix the unknown Docling crash cause.

## Validación previa conservada / Previous validation retained

2026-09-12 · Folio 0.2.0

## Entorno / Environment

Linux, Python 3.12.14, PySide6 6.11.2, LiteParse 2.14.4, python-docx 1.2.0. Interfaz Qt real ejecutada con plataforma `offscreen` y estilo Fusion. Docling no está instalado en este entorno.

## Ejecutado / Executed

- **56/56 pruebas correctas, sin omisiones**, mediante `python -m unittest discover -s tests -v`.
- 20 pruebas de lógica: opciones, Unicode/rutas, traducciones, detección de errores, publicación transaccional y protección frente a sobrescritura.
- 8 pruebas de contrato de adaptadores PDF con implementaciones simuladas: llamadas, selección, caché, exportación y fallos parciales. Estas pruebas por sí solas no ejecutan las bibliotecas reales.
- 9 pruebas de interfaz **Qt real**: idiomas, cola, motor/tipo, previsualización local, restricciones de recursos, clic en ajustes avanzados, estabilidad de tamaño con foco, selección múltiple al traducir y conversión DOCX/TXT mediante el QProcess real. Comprueban botones desactivados al terminar y conservación del resumen al cambiar de idioma. Las pruebas usan preferencias aisladas.
- 16 pruebas de conversión **real de documentos de texto**: DOCX con orden de títulos/listas/tablas, enlaces, notas al pie, encabezados, imágenes, celdas combinadas y avisos de cambios pendientes; TXT UTF-8/16/32/Windows-1252; Markdown; CSV/TSV entrecomillado con saltos y delimitadores; detección de firma, formatos forzados, binarios y archivos vacíos. No usan motores PDF simulados para convertir texto.
- 3 pruebas de protocolo/proceso: error por archivo sin detener el lote, petición malformada y cancelación real de un subproceso con adaptador bloqueante simulado.
- **LiteParse real**, PDF digital sintético de dos páginas: texto, identificador 9281, etiqueta de tabla Sample A, JSON, imágenes exportadas y copia con marcas de páginas 1 y 2.
- **Lote mixto real desde Qt/QProcess**: PDF con LiteParse, DOCX, TXT y CSV. Los cuatro terminaron. El diagnóstico automático del PDF señaló necesidad de OCR; al no estar instalado Docling, eligió LiteParse y mostró el aviso correspondiente. Esta prueba se realizó con OCR desactivado.
- Apertura, capturas e inspección visual de la interfaz en español e inglés, incluyendo 980 × 700 y 1280 × 960. Se comprobaron botones desactivados, desplegables, casillas, pestañas, tabla y vista previa. Las capturas reales están en `screenshots/`.
- El nuevo ejemplo DOCX se renderizó y se inspeccionó visualmente: una página, títulos, listas, tabla y enlace. Los PDF sintéticos existentes ya habían sido renderizados e inspeccionados en 0.1.
- El ZIP se comprueba con `ZipFile.testzip()`; excluye entornos, cachés y resultados temporales.

## Pendiente / Not executed

- Conversiones reales con Docling, EasyOCR o Tesseract; descarga de modelos y funcionamiento sin conexión tras preparar cachés.
- Instalación limpia completa de dependencias en Windows/macOS; ejecución de sus lanzadores nativos.
- Interacción con ventanas nativas y escalado DPI en una pantalla física Windows/macOS. Qt offscreen permite verificar el renderizado y los controles, pero no sustituye esas pruebas.
- Medidas de velocidad/RAM con documentos grandes y validación de fidelidad con documentos reales del usuario.
- Fidelidad de toda la variedad de DOCX: objetos flotantes, fórmulas, numeraciones complejas, notas con tablas y revisiones. La aplicación avisa de varios de estos casos; no afirma conservarlos íntegramente.

## Comprobar en tu equipo / Local checks

1. Instala esta versión y abre la ventana; cambia idioma y tipo de documento.
2. Convierte los cinco ejemplos de texto y el PDF digital. Comprueba el marcador 9281, tildes, listas, cifras y columnas.
3. Si usarás escaneos, prueba ambos motores con OCR y el idioma necesario (`tools/smoke_test.py --engine MOTOR --ocr`). Puede descargar modelos.
4. Revisa controles, foco de teclado y escalado de pantalla en tu sistema.
5. Compara con una muestra representativa de tus documentos antes de usar el flujo habitualmente.

## English summary

56 tests passed, none skipped. Actual Qt interface, QProcess DOCX/TXT batch, editable-document conversions and LiteParse digital PDF conversion were exercised. A real mixed PDF/DOCX/TXT/CSV GUI batch completed. Spanish/English and compact-window screenshots were inspected. PDF adapter contract tests still use fakes; actual Docling/OCR, native Windows/macOS setup and accuracy on user documents remain untested. The tested synthetic examples establish functionality, not a general extraction-fidelity guarantee.
