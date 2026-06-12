# AI-Compatibility-Checker 🚀

Un detector de hardware local multiplataforma escrito en Python para analizar los recursos de tu PC (CPU, RAM, GPU, VRAM) y evaluar con precisión qué modelos de Inteligencia Artificial locales (LLMs y Generadores de Imágenes) son aptos para tu configuración.

Inspirado en el concepto web de `CanIRun.ai`, pero construido como una **aplicación de escritorio local** para saltarse las restricciones de seguridad del navegador, logrando lecturas de hardware 100% exactas y detalladas.

---

## ✨ Características

- 🔍 **Detección Nivel Sistema**: Identificación exacta del procesador (nombre, núcleos, hilos), memoria RAM real instalada, nombre de tarjeta de video (GPU) y VRAM dedicada.
- 🍏 **Soporte Apple Silicon**: Identificación de procesadores de la serie M de Apple y cálculo basado en su arquitectura de **Memoria Unificada**.
- 🐧 **Acceso al Kernel en Linux**: Lectura de VRAM directa desde `sysfs` para tarjetas AMD en Linux, y consulta `nvidia-smi` en NVIDIA.
- ⚡ **Diagnóstico AVX2**: Escaneo de soporte de la instrucción AVX2 en CPU (indispensable para correr modelos de lenguaje locales rápido).
- 🎛️ **Modo Offline & Online**:
  - **Offline (Local)**: Consulta una base de datos local rápida de modelos (`models.json`).
  - **Online (Remoto)**: Descarga dinámicamente la lista de modelos más actualizada desde un servidor/GitHub Gist remoto, con fallback local automático.
- 🎨 **Tema Oscuro Premium**: Interfaz gráfica moderna y responsiva construida con **CustomTkinter** y micro-animaciones (hover effects).
- ⚙️ **Configuración Desacoplada**: Control total del tema visual y de los umbrales de compatibilidad física de memoria mediante un archivo `.env`.

---

## 🖥️ Requisitos

- Python 3.10 o superior.
- Sistemas Operativos: Windows 10/11, macOS, o Linux.

---

## 🚀 Instalación y Uso Rápido

### En Windows 🪟
1. Descarga o clona este repositorio.
2. Haz doble clic en el archivo `run.bat`.
   *El script creará automáticamente un entorno virtual aislado (`.venv`), instalará las librerías necesarias y lanzará la aplicación.*

### En macOS y Linux 🍎/🐧
1. Abre tu terminal en la carpeta del proyecto.
2. Otorga permisos de ejecución al script e inícialo:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

---

## ⚙️ Configuración Personalizada

Puedes copiar el archivo `.env.example` y renombrarlo como `.env` para personalizar la aplicación:
```env
# Tema visual
APP_THEME=dark
APP_COLOR_THEME=blue

# URL de la base de datos de modelos online
ONLINE_MODELS_URL=https://raw.githubusercontent.com/.../models_online.json
```
Consulte el archivo `.env.example` para ver la lista completa de umbrales de memoria personalizables.

---

## 🛠️ Estructura del Código

- `gui.py`: La interfaz gráfica de usuario responsiva.
- `detector.py`: El script encargado de interrogar a los comandos del sistema y WMI.
- `models.py`: El motor de clasificación lógica de compatibilidad y pesos de VRAM/RAM.
- `models.json`: La base de datos local de modelos base.
- `models_online.json`: La base de datos local expandida de modelos recientes.
- `config.py`: Parser de variables del archivo `.env`.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
