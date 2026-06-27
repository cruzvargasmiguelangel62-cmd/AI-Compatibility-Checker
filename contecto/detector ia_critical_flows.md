# Critical Flows: detector ia

## Metadata
- Proyecto: detector ia
- Archivo: critical_flows.md
- Generado en: 18/6/2026, 5:44:21 p.m.
- Modo: deterministic local analysis
- Vigencia: úsalo como mapa de referencia y valida contra el código activo antes de tomar decisiones delicadas.

## Qué Es Este Archivo
Documento corto para separar flujos operativos y fuentes de verdad del resto del mapa técnico.

## Fuentes de Verdad
Esta sección es heurística. Señala archivos donde probablemente viven decisiones reales del sistema según ruta, nombre y señales del código.
- Reglas de negocio: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py, detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py, detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/nvidia_cuda.py
  Nota: Aquí suelen vivir decisiones funcionales, validaciones y cálculo de estados.
- Estado global y contexto: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/stdhooks/hook-vtkmodules.vtkPythonContext2D.py, detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/stdhooks/hook-vtkmodules.vtkRenderingContext2D.py, detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/stdhooks/hook-vtkmodules.vtkRenderingContextOpenGL2.py
  Nota: Aquí suele vivir el acceso global, la sesión y la propagación de estado.
- Integraciones y API: detector ia/.venv/Lib/site-packages/pip/_internal/utils/direct_url_helpers.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/inject_securetransport.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/logging.py
  Nota: Aquí suelen vivir llamadas externas, endpoints y capa de integración.
- UI y orquestación: detector ia/.venv/Lib/site-packages/pip/_internal/utils/compatibility_tags.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/glibc.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/logging.py
  Nota: Aquí suelen vivir pantallas, flujos visibles y orquestadores de interfaz.
- Autenticación y acceso: detector ia/.venv/Lib/site-packages/pip/_internal/utils/appdirs.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/direct_url_helpers.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/filesystem.py
  Nota: Aquí suele vivir el control de acceso, sesión y reglas de identidad.

## Flujos Críticos
Esta sección es heurística. No documenta todo el negocio; marca rutas de lectura que suelen cambiar decisiones antes de editar código.

### Autenticación y acceso
- Por qué importa: Conviene empezar aquí si el flujo depende de sesión, permisos o acceso global.
- Archivos guía: detector ia/.venv/Lib/site-packages/pip/_internal/utils/appdirs.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/inject_securetransport.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/setuptools_build.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/urls.py

### Pagos y bloqueo funcional
- Por qué importa: Conviene revisar estas piezas si el negocio depende de validación, tolerancia, bloqueo o desbloqueo.
- Archivos guía: detector ia/.venv/Lib/site-packages/pip/_internal/utils/deprecation.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/entrypoints.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/setuptools_build.py, detector ia/.venv/Lib/site-packages/_distutils_hack/__init__.py

### Onboarding o navegación principal
- Por qué importa: Ayuda a reconstruir por dónde entra el usuario y cómo se mueve entre pantallas.
- Archivos guía: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/main.py, detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/vtkmodules.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/appdirs.py

### Estado global del usuario
- Por qué importa: Útil para detectar dónde vive la información compartida que condiciona la UI.
- Archivos guía: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/appdirs.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/distutils_args.py, detector ia/.venv/Lib/site-packages/pip/_internal/utils/entrypoints.py

## Recomendación de Uso
- Léelo antes de editar si la tarea toca reglas funcionales, contexto global o integraciones.
- Cruza este archivo con snapshot y graph guide si necesitas más detalle estructural.
