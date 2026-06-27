# Hotspots & Deuda Técnica: detector ia

## Hotspots Prioritarios
1. main.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/cli/main.py
   Importancia: 0
   Tipo: .py
   Rol: punto de entrada u orquestador principal
   Complejidad estimada: medium
   Lineas no vacias: 56
   Confianza: high (path)
   Contratos detectados: main(args: Optional[List[str]] = None)
2. main.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/main.py
   Importancia: 0
   Tipo: .py
   Rol: punto de entrada u orquestador principal
   Complejidad estimada: low
   Lineas no vacias: 9
   Confianza: high (path)
   Contratos detectados: main(args=None)
3. __init__.py
   Path: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/__init__.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 1
   Confianza: medium (path)
   Contratos detectados: N/A
4. mypy.py
   Path: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/mypy.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 22
   Confianza: medium (path)
   Contratos detectados: find_mypyc_module_for_dist(dist_name)
5. nvidia_cuda.py
   Path: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/nvidia_cuda.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: medium
   Lineas no vacias: 63
   Confianza: medium (path)
   Contratos detectados: collect_nvidia_cuda_binaries(hook_file), infer_hiddenimports_from_requirements(requirements), create_symlink_suppression_patterns(hook_file)
6. vtkmodules.py
   Path: detector ia/.venv/Lib/site-packages/_pyinstaller_hooks_contrib/utils/vtkmodules.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: high
   Lineas no vacias: 613
   Confianza: medium (path)
   Contratos detectados: add_vtkmodules_dependencies(hook_file)
7. __init__.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/utils/__init__.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 0
   Confianza: medium (path)
   Contratos detectados: N/A
8. _log.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/utils/_log.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 25
   Confianza: medium (path)
   Contratos detectados: VerboseLogger, getLogger(name: str), init_logging()
9. appdirs.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/utils/appdirs.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 26
   Confianza: medium (path)
   Contratos detectados: user_cache_dir(appname: str), user_config_dir(appname: str, roaming: bool = True), site_config_dirs(appname: str)
10. compat.py
   Path: detector ia/.venv/Lib/site-packages/pip/_internal/utils/compat.py
   Importancia: 0
   Tipo: .py
   Rol: módulo de soporte del proyecto
   Complejidad estimada: low
   Lineas no vacias: 45
   Confianza: medium (path)
   Contratos detectados: has_tls(), get_path_uid(path: str)

## Recomendaciones de Acción
- Revisa primero los archivos con más conexiones entrantes: suelen ser utilidades compartidas o núcleos frágiles.
- Revisa luego los archivos con más conexiones salientes: suelen ser orquestadores o pantallas con demasiadas responsabilidades.
- Antes de refactorizar, sigue las relaciones del grafo para evitar romper cadenas de dependencias ocultas.
