# Folio 0.2.2 — lector PDFium y diagnóstico de incidencias nativas

## Qué hemos observado

Las dos pruebas remitidas del PDF sintético notifican conversión completada de 2 páginas y código de salida `0x00000000`. La prueba sin OCR tardó 13,20 s y contiene un mensaje `Windows fatal exception: access violation`. La prueba con OCR tardó 20,55 s y contiene dos. Ambas pasan `pip check`.

Las trazas incluyen `docling_parse/pdf_parser.py`, `_timings_from_decoder` y la lectura/renderizado de páginas. Esto orienta la siguiente comparación hacia el lector PDF. No prueba que ese sea el origen del cierre del artículo, ni que el OCR, Python 3.13 o la memoria sean culpables. Estas dos ejecuciones continuaron después de las trazas y no reprodujeron el cierre original. No se han recibido sus Markdown, por lo que no se ha comprobado la fidelidad del contenido.

## Cambios

- Casilla **Docling: usar lector PDFium**, en **Ajustes avanzados**. Selecciona `PyPdfiumDocumentBackend` manteniendo el motor Docling, sus modelos de estructura/tablas, la configuración de CPU y el OCR elegido. No es un cambio a LiteParse. La lectura del texto y su reconstrucción pueden variar; compara el Markdown con el PDF.
- Se conserva el lector predeterminado cuando la casilla está desmarcada. No hay reintentos silenciosos con otro lector.
- El diagnóstico ahora diferencia `completed`, `completed_with_native_notices` y `failed`. Registra el número de mensajes nativos y conserva el código de salida real. Un mensaje de excepción no convierte automáticamente una ejecución completada en un cierre fatal.
- La interfaz muestra una advertencia al terminar un lote si el registro contiene esas incidencias. La advertencia corresponde al lote y no atribuye por sí sola el problema a un archivo concreto.
- ICO regenerado: se detectó que el archivo ICO del ZIP anterior estaba vacío. El archivo actual se ha decodificado y validado en sus 7 tamaños: 16, 24, 32, 48, 64, 128 y 256 píxeles. El empaquetado rechaza ahora un ICO vacío o sin las entradas esperadas.

## Actualizar tu instalación

1. Cierra Folio y guarda una copia de la carpeta del programa.
2. Extrae este ZIP aparte. Copia las carpetas `folio/` y `tools/`, y `diagnose_docling.cmd`, a tu carpeta actual de Folio, reemplazando esos archivos. Si tienes modificaciones propias, compáralas antes de reemplazarlas.
3. Conserva tu `.venv`, `examples/`, documentos y modelos. No necesitas reinstalar paquetes para probar esta opción con la instalación de Docling 2.126.0 que figura en los diagnósticos.

## Prueba siguiente

1. En Folio selecciona **Docling** como motor PDF.
2. Abre **Ajustes avanzados** y marca **Docling: usar lector PDFium**.
3. Prueba el artículo que antes fallaba, con la misma opción de OCR de aquella conversión, y guarda el registro. El programa no sobrescribe resultados previos. Si el archivo ya aparece completado en la cola, quítalo y vuelve a añadirlo para repetirlo.
4. Comprueba títulos, orden de columnas, tablas, cifras y referencias del Markdown frente al original. Terminar la conversión no garantiza la calidad de extracción.
5. Para una comparación controlada con el ejemplo: ejecuta `diagnose_docling.cmd`, responde **S** a «Usar lector PDFium» y primero **N**, después **S**, a OCR en dos ejecuciones distintas. Cada prueba crea su propia carpeta en `diagnostics/`.

Si PDFium completa la conversión y desaparecen las incidencias, será evidencia a favor de utilizar esa alternativa en este equipo. Si persisten, comparte el nuevo `diagnostic.json` y `worker.log` tras revisar rutas y nombres personales. No hace falta enviar el artículo para esta primera comparación.

Desde una terminal abierta en la carpeta de Folio también puedes ejecutar:

```bat
.venv\Scripts\python.exe tools\diagnose_docling.py --pdfium
.venv\Scripts\python.exe tools\diagnose_docling.py --pdfium --ocr
.venv\Scripts\python.exe tools\diagnose_docling.py --pdfium --ocr --source "C:\ruta\documento.pdf"
```

El diagnóstico devuelve código 0 para completado sin mensajes nativos, 2 para completado con incidencias nativas y 1 para fallo/cancelación. Los avisos habituales de deprecación no se clasifican como excepciones nativas.

## Icono de acceso directo de Windows

El archivo se encuentra en `folio/assets/folio.ico` y también se entrega como `Folio.ico` por separado. Guarda el ICO en una carpeta permanente. Sobre un **acceso directo** (`.lnk`): clic derecho → **Propiedades** → **Acceso directo** → **Cambiar icono** → **Examinar** → selecciona el ICO → **Aceptar / Aplicar**. El botón no aparece de la misma forma sobre el archivo `.cmd` original: primero crea un acceso directo a `start_windows.cmd`.

## Validación y fuentes

La implementación se contrasta con el código publicado de `docling-slim==2.126.0`: `PdfFormatOption` admite `backend` y `docling.backend.pypdfium2_backend` expone `PyPdfiumDocumentBackend`. Se prueban selección, separación de caché, persistencia de ajustes, traducciones y avisos mediante pruebas automatizadas. Los contratos de Docling usan dobles de prueba; no son una ejecución real de Docling/PDFium. No se ha ejecutado el programa en Windows desde el entorno de desarrollo.

La alternativa PDFium está [documentada por Docling](https://docling-project.github.io/docling/reference/cli/). Python documenta el [manejador de excepciones de Windows en faulthandler](https://docs.python.org/3/library/faulthandler.html); Microsoft explica que los [manejadores de excepciones pueden observarlas antes de que se resuelvan](https://learn.microsoft.com/en-us/windows/win32/debug/vectored-exception-handling).

Esta versión propone una alternativa comprobable; no afirma haber solucionado definitivamente el cierre original.
