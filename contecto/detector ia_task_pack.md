# Agent Task Pack: detector ia

## Tarea Solicitada
Analiza la tarea solicitada y ubica los archivos relevantes.

## Qué Hace el Proyecto
- Resumen: detector ia usa Python, SCSS/Sass, PWA, React, Django, WebSockets y tiene como entry points detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/main.py.
- Stack: Python, SCSS/Sass, PWA, React, Django, WebSockets, Express.js, Flask
- Entry points: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/main.py

## Archivos Primarios a Revisar
- `detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py` (impacto: 0, score: 0)
  - Hotspot arquitectónico del proyecto
- `detector ia/.venv/Lib/site-packages/pip/_internal/main.py` (impacto: 0, score: 0)
  - Hotspot arquitectónico del proyecto
- `detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py` (impacto: 0, score: 0)
  - Hotspot arquitectónico del proyecto
- `detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py` (impacto: 0, score: 0)
  - Hotspot arquitectónico del proyecto
- `detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/nvidia_cuda.py` (impacto: 0, score: 0)
  - Hotspot arquitectónico del proyecto

## Archivos Relacionados
- No se detectaron relacionados claros en el subgrafo inicial.

## Orden de Lectura Recomendado
1. `detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py`
2. `detector ia/.venv/Lib/site-packages/pip/_internal/main.py`
3. `detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py`
4. `detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py`

## Instrucciones para el Agente
1. Empieza por los archivos primarios y confirma si contienen la UI, lógica o integración principal de la tarea.
2. Después revisa archivos relacionados para detectar dependencias laterales, estado compartido y posibles regresiones.
3. Si modificas un hotspot, valida entradas y salidas del módulo antes de aplicar cambios.
4. Términos guía detectados: solicitada, ubica, archivo, relevant. Usa esos conceptos para seguir componentes, stores, contextos y APIs.
