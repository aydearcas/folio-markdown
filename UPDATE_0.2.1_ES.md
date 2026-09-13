# Folio 0.2.1 — diagnóstico, contraste e icono

Nota histórica: para la versión 0.2.2 utiliza `UPDATE_0.2.2_ES.md`. Esa versión añade un selector de lector PDF y corrige el ICO vacío incluido por error en 0.2.1.

Esta actualización mejora el diagnóstico de cierres inesperados de Docling y corrige la presentación de menús contextuales. **No se ha reproducido el cierre en Windows ni confirmado su causa; no es una corrección verificada del motor Docling.** No cambia sus versiones, modelos ni configuración de conversión.

## Actualizar sin reinstalar los modelos

1. Cierra Folio y guarda una copia de la carpeta del programa.
2. Extrae el ZIP en otra carpeta. Desde la nueva carpeta `Folio`, copia `folio/`, `tools/` y `diagnose_docling.cmd` a la carpeta de tu instalación, reemplazando esos archivos. Conserva allí `main.py` y tu `.venv` existente. Si has modificado esos archivos, compara los cambios antes de reemplazarlos.
3. Abre Folio con tu lanzador habitual. No es necesario borrar cachés, documentos ni resultados, ni ejecutar como administrador. Las descargas de modelos que estuviesen incompletas aún pueden ser necesarias.

El ZIP también contiene el código completo, ejemplos y pruebas para una instalación nueva. No incluye dependencias ni modelos.

## Qué indica el registro original

Los avisos de deprecación de EasyOCR/PyTorch no son por sí solos errores fatales. El aviso de Hugging Face sobre peticiones sin autenticar indica límites de descarga; el de enlaces simbólicos en Windows indica que la caché puede ocupar más espacio, pero sigue funcionando.

El mensaje final de Folio no mostraba el estado de salida del subproceso. Sin ese dato o una traza no es posible decidir entre una incompatibilidad de dependencias nativas, un problema de recursos, modelos o un fallo ligado al documento. Esta versión muestra el estado de Qt, permite **Guardar registro** y activa `faulthandler`, que puede registrar algunas excepciones nativas. No garantiza capturar todos los cierres.

Importante: Qt solo garantiza la validez de `exitCode()` con `NormalExit`. Un valor bruto que acompaña a `CrashExit` no permite diagnosticar por sí solo una excepción de Windows. El diagnóstico independiente captura el código de salida del sistema operativo.

## Prueba recomendada

1. Prueba un solo PDF digital cuyo uso esté permitido. Si contiene el texto que necesitas y se puede seleccionar, desactiva OCR para esta comparación. Desactiva también las salidas opcionales de imágenes y copia de páginas. Comprueba que el Markdown conserve la información necesaria.
2. Ejecuta `diagnose_docling.cmd` con doble clic. Elige **N** para la primera prueba. Utiliza el PDF sintético incluido, no tu artículo, y ejecuta la conversión real en tu entorno existente. Puede descargar modelos y tardar varios minutos.
3. Repite el diagnóstico eligiendo **S** para activar OCR. No actives OCR simultáneamente en otra instancia durante esta comparación.
4. Cada ejecución crea una carpeta independiente dentro de `diagnostics/` con `diagnostic.json`, `worker.log` y, si termina, los resultados. Revisa los dos archivos de diagnóstico antes de compartirlos: pueden incluir rutas locales, nombres y mensajes de bibliotecas. No hace falta enviar el artículo.

Si la prueba sin OCR termina y con OCR falla, el problema queda acotado al recorrido que activa OCR, sin identificar aún una dependencia concreta. Si falla también el ejemplo sin OCR, hay que revisar el entorno/modelos/motor antes de atribuirlo al artículo. Si ambos terminan pero el artículo falla, el siguiente paso es una prueba controlada de ese documento. Un `pip check` correcto no descarta incompatibilidades binarias ni problemas de memoria.

Para probar otro documento desde una terminal en la carpeta de Folio:

```bat
.venv\Scripts\python.exe tools\diagnose_docling.py --source "C:\ruta\documento.pdf"
.venv\Scripts\python.exe tools\diagnose_docling.py --source "C:\ruta\documento.pdf" --ocr --language spa
```

El script no sube los documentos ni los registros, no reinstala paquetes y no borra cachés. Las bibliotecas pueden contactar sus repositorios habituales para descargar modelos. No necesitas facilitar un token de Hugging Face para resolver el aviso de enlaces simbólicos.

## Interfaz e icono

- Paleta clara explícita y estados legibles para menús contextuales, selección y opciones deshabilitadas, también cuando Qt recibe una paleta oscura del sistema. Se conserva el diseño claro de Folio; no se añade un tema oscuro completo.
- Botón **Guardar registro / Save log**.
- Nuevo icono: una F blanca con pliegue de papel en verde menta sobre fondo verde azulado. `folio/assets/folio.png` se utiliza dentro de Qt; `folio/assets/folio.ico` contiene tamaños de 16 a 256 píxeles para Windows.
- Los archivos `.cmd` no cambian automáticamente de icono. Para un acceso directo existente de Windows: clic derecho → Propiedades → Cambiar icono → seleccionar `folio/assets/folio.ico`.

## Límites de validación

Las pruebas se ejecutan en Linux con Qt real en modo offscreen y una paleta oscura simulada. Eso no sustituye una comprobación visual con Windows real, sus ventanas nativas, escalado DPI y barra de tareas. Docling/EasyOCR no están instalados en el entorno de desarrollo de esta actualización, por lo que no se afirma haber reproducido ni resuelto el fallo del usuario. Consulta `VALIDATION.md`.

Fuentes técnicas: [caché de Hugging Face](https://huggingface.co/docs/huggingface_hub/guides/manage-cache#limitations), [QProcess y códigos de salida](https://doc.qt.io/qt-6/qprocess.html#exitCode), [faulthandler](https://docs.python.org/3/library/faulthandler.html).
