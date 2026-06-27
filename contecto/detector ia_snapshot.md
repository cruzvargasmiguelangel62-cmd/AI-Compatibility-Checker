# Architectural Snapshot

Project Context: detector ia
Tech Stack: Python, SCSS/Sass, PWA, React, Django, WebSockets, Database (ORM/ODM), Express.js, Flask, Vue, C#
Scale: 1500 Analyzed Modules

## Metadata
- Proyecto: detector ia
- Archivo: snapshot.md
- Generado en: 18/6/2026, 5:43:08 p.m.
- Modo: deterministic local analysis
- Vigencia: úsalo como mapa de referencia y valida contra el código activo antes de tomar decisiones delicadas.

## Qué Pasarle A Un Agente
- Instrucciones operativas de la tarea actual.
- Este snapshot como contexto base del repositorio.
- Los archivos concretos que el snapshot marca como hotspots o fuentes de verdad.
- No le pases dumps largos de código salvo que la tarea ya esté localizada.

## Lectura de Confianza
- Hechos verificables: entry points detectados, tipos de archivo, relaciones del grafo, conexiones entrantes/salientes, contratos extraídos por regex y métricas de tamaño.
- Heurísticas: fuentes de verdad, flujos críticos, rol inferido del archivo y complejidad estimada.

## Identidad del Proyecto
- Descripción: detector ia está orientado a backend FastAPI para análisis y orquestación de IA.
- Resumen arquitectónico: Backend detectado con 1500 archivos de lógica/servicio. Los hotspots más conectados son main.py (detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py) [0], main.py (detector ia/.venv/Lib/site-packages/pip/_internal/main.py) [0], __init__.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py) [0], mypy.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py) [0].
- Entry points probables: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/main.py
- Directorios principales: .venv
- Tipos de archivo dominantes: .py (1500)

## Capacidades Detectadas
- Capacidades base: N/A
- Archivos núcleo: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py, detector ia/.venv/Lib/site-packages/pip/_internal/main.py, detector ia/.venv/Lib/site-packages/PyInstaller/building/build_main.py
- Estrategia: análisis determinístico primero y enriquecimiento con IA solo como capa opcional.

## Restricciones de Lectura
- Modelo local-first: no asumir SaaS, multiusuario ni servicio remoto sin evidencia explícita.
- Persistencia: la persistencia detectada es local; no afirmar nube o base de datos de usuarios sin evidencia.
- Regla de inferencia: si una capacidad no aparece en archivos, rutas, dependencias o funciones detectadas, no la inventes.

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

## Prioridad de Lectura
1. main.py (detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py) [0]
2. main.py (detector ia/.venv/Lib/site-packages/pip/_internal/main.py) [0]
3. __init__.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py) [0]
4. mypy.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py) [0]
5. nvidia_cuda.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/nvidia_cuda.py) [0]
6. vtkmodules.py (detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/vtkmodules.py) [0]

## Hotspots con Contrato Corto
- main.py: punto de entrada u orquestador principal; complejidad medium; 56 lineas; exports main(args: Optional[List[str]] = None).
- main.py: punto de entrada u orquestador principal; complejidad low; 9 lineas; exports main(args=None).
- __init__.py: módulo de soporte del proyecto; complejidad low; 1 lineas; exports N/A.
- mypy.py: módulo de soporte del proyecto; complejidad low; 22 lineas; exports find_mypyc_module_for_dist(dist_name).
- nvidia_cuda.py: módulo de soporte del proyecto; complejidad medium; 63 lineas; exports collect_nvidia_cuda_binaries(hook_file), infer_hiddenimports_from_requirements(requirements), create_symlink_suppression_patterns(hook_file).
- vtkmodules.py: módulo de soporte del proyecto; complejidad high; 613 lineas; exports add_vtkmodules_dependencies(hook_file).

## Capas y Directorios
- .venv

- [.VENV] main.py, main.py, __init__.py, mypy.py, nvidia_cuda.py, vtkmodules.py

## Relaciones Clave Del Grafo
N/A

## Lectura del Grafo
- main.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- main.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- __init__.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- mypy.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- nvidia_cuda.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- vtkmodules.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- __init__.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.
- _log.py: 0 conexiones totales (0 salientes, 0 entrantes). Usa -> N/A. Es usado por -> N/A.

## Estructura de Conexiones por Nodo
Este bloque ayuda a explicar cómo se conecta cada archivo crítico dentro del grafo para que otro agente o persona entienda el mapa sin abrir el canvas.

### main.py
- Archivo: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py
- Centralidad: 0
- Rol inferido: punto de entrada u orquestador principal
- Complejidad estimada: medium
- Lineas no vacias: 56
- Confianza de lectura: high (path)
- Contratos detectados: main(args: Optional[List[str]] = None)
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

### main.py
- Archivo: detector ia/.venv/Lib/site-packages/pip/_internal/main.py
- Centralidad: 0
- Rol inferido: punto de entrada u orquestador principal
- Complejidad estimada: low
- Lineas no vacias: 9
- Confianza de lectura: high (path)
- Contratos detectados: main(args=None)
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

### __init__.py
- Archivo: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py
- Centralidad: 0
- Rol inferido: módulo de soporte del proyecto
- Complejidad estimada: low
- Lineas no vacias: 1
- Confianza de lectura: medium (path)
- Contratos detectados: N/A
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

### mypy.py
- Archivo: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py
- Centralidad: 0
- Rol inferido: módulo de soporte del proyecto
- Complejidad estimada: low
- Lineas no vacias: 22
- Confianza de lectura: medium (path)
- Contratos detectados: find_mypyc_module_for_dist(dist_name)
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

### nvidia_cuda.py
- Archivo: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/nvidia_cuda.py
- Centralidad: 0
- Rol inferido: módulo de soporte del proyecto
- Complejidad estimada: medium
- Lineas no vacias: 63
- Confianza de lectura: medium (path)
- Contratos detectados: collect_nvidia_cuda_binaries(hook_file), infer_hiddenimports_from_requirements(requirements), create_symlink_suppression_patterns(hook_file)
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

### vtkmodules.py
- Archivo: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/vtkmodules.py
- Centralidad: 0
- Rol inferido: módulo de soporte del proyecto
- Complejidad estimada: high
- Lineas no vacias: 613
- Confianza de lectura: medium (path)
- Contratos detectados: add_vtkmodules_dependencies(hook_file)
- Usa directamente: N/A
- Es usado por: N/A
- Impacto secundario probable: N/A

