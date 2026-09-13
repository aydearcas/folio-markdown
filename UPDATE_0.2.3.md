# Folio 0.2.3 — PDFium predeterminado / PDFium by default

## Español

PDFium es ahora el lector predeterminado siempre que Folio convierte un PDF con Docling, en cualquier sistema operativo. Se aplica también cuando el modo automático elige Docling. LiteParse y la conversión de documentos de texto no cambian.

En **Ajustes avanzados → Lector PDF de Docling**, la casilla **Usar original (experimental)** está desmarcada inicialmente. Debajo se muestra:

> PDFium se usa por defecto. El original tiende a dar errores en el entorno Windows probado; úsalo solo para pruebas.

Al actualizar desde 0.2.2 o anterior, la preferencia antigua del lector se sustituye por PDFium sin cambiar idioma, OCR, destino ni otros ajustes. Si después eliges expresamente el lector experimental, esa nueva elección se conserva al reiniciar. Los mensajes del registro identifican el lector utilizado. No cambia el motor ni los modelos de Docling, solo su lector PDF.

### Actualización

1. Cierra Folio y guarda una copia de la carpeta del programa.
2. Extrae el ZIP aparte. Copia `folio/`, `tools/` y `diagnose_docling.cmd` a tu instalación, reemplazando esos archivos. Si los has personalizado, compara tus cambios antes de reemplazarlos.
3. Conserva `.venv`, modelos y documentos. Abre Folio con tu lanzador habitual. No necesitas reinstalar dependencias.

El diagnóstico usa PDFium por defecto. En `diagnose_docling.cmd` selecciona **P**; **O** activa el original experimental. Desde la terminal:

```bat
.venv\Scripts\python.exe tools\diagnose_docling.py
.venv\Scripts\python.exe tools\diagnose_docling.py --original-reader
```

La opción anterior `--pdfium` sigue siendo válida. Las guías 0.2.1 y 0.2.2 se conservan como historial; las instrucciones de esta guía las sustituyen en lo referente al lector predeterminado y su selector.

El icono de acceso directo validado sigue en `folio/assets/folio.ico`. Mantén la revisión del Markdown frente al original, especialmente cifras, columnas y tablas. La advertencia refleja los fallos observados en el equipo Windows probado, no demuestra que el lector original falle en todos los equipos ni que PDFium sea infalible.

## English

PDFium is now the default PDF reader whenever Folio uses Docling, including automatic engine selection. LiteParse and text-document conversion are unchanged.

Under **Advanced settings → Docling PDF reader**, **Use original (experimental)** is initially unchecked. The accompanying warning states that the original reader tends to fail in the tested Windows environment and should only be used for testing.

Upgrading from 0.2.2 or earlier switches the old reader preference to PDFium while retaining all other settings. An explicit selection of the experimental reader made in this version persists across restarts.

To update, close Folio, back up the application folder, then copy `folio/`, `tools/` and `diagnose_docling.cmd` from the ZIP over your installation. Preserve `.venv`, models and documents. No dependency reinstall is required. The diagnostic also defaults to PDFium; use `--original-reader` only for an explicit experimental comparison. The existing `--pdfium` flag remains supported.

The original-reader warning is scoped to the observed Windows environment. It is not a universal failure claim. Always review converted tables, numbers and column order against the source.
