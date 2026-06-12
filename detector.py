import os
import platform
import subprocess
import json
import re
import shutil

_windows_sys_info_cache = None

def _query_windows_system_info():
    global _windows_sys_info_cache
    if _windows_sys_info_cache is not None:
        return _windows_sys_info_cache
        
    info = {"ram": None, "gpus": []}
    try:
        # Run a single PowerShell process to fetch both RAM and GPUs (takes ~1.0s instead of ~4s for multiple calls)
        cmd = [
            "powershell",
            "-Command",
            "$ram = Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum | Select-Object -ExpandProperty Sum; "
            "$gpus = Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json -Compress; "
            "Write-Output \"$ram===$gpus\""
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        if "===" in out:
            parts = out.split("===", 1)
            ram_str = parts[0].strip()
            if ram_str.isdigit():
                info["ram"] = round(float(ram_str) / (1024.0 ** 3), 1)
                
            gpus_str = parts[1].strip()
            if gpus_str:
                data = json.loads(gpus_str)
                if not isinstance(data, list):
                    data = [data]
                for item in data:
                    name = item.get("Name", "")
                    if not name:
                        continue
                    raw_vram = item.get("AdapterRAM")
                    vram_gb = 0.0
                    if raw_vram is not None:
                        try:
                            vram_bytes = int(raw_vram)
                            if vram_bytes < 0:
                                vram_bytes += 2**32
                            vram_gb = round(vram_bytes / (1024.0 ** 3), 1)
                        except (ValueError, TypeError):
                            pass
                    
                    name_upper = name.upper()
                    vendor = "NVIDIA" if "NVIDIA" in name_upper else "AMD" if "AMD" in name_upper or "RADEON" in name_upper else "Intel" if "INTEL" in name_upper else "Other"
                    info["gpus"].append({
                        "name": name,
                        "vram": vram_gb if vram_gb > 0 else 0.0,
                        "vendor": vendor
                    })
    except Exception as e:
        print(f"Error querying Windows system info: {e}")
        
    _windows_sys_info_cache = info
    return info

def get_cpu_name():
    system = platform.system()
    try:
        if system == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return name.strip()
        elif system == "Darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        elif system == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"

def check_avx2_support():
    """Verifica si el CPU soporta instrucciones AVX2 (Crítico para correr LLMs rápido en CPU)"""
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                return "avx2" in f.read().lower()
        elif system == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.optional.avx2_0"]).decode().strip()
            return out == "1"
        elif system == "Windows":
            # En Windows sin librerías externas de C, intentamos deducir por la familia del procesador
            # La mayoría de CPUs de la última década lo tienen.
            cpu_name = get_cpu_name().lower()
            # Falsos negativos si es muy antiguo
            if "core i" in cpu_name or "ryzen" in cpu_name or "epyc" in cpu_name:
                return True
    except Exception:
        pass
    return False

def get_windows_gpus():
    gpus = []
    
    # 1. Intentar nvidia-smi primero (Más confiable para NVIDIA)
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL
        ).decode()
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) == 2:
                name = parts[0].strip()
                vram_mib = float(parts[1].strip())
                gpus.append({
                    "name": name,
                    "vram": round(vram_mib / 1024.0, 1),
                    "vendor": "NVIDIA"
                })
        if gpus:
            return gpus
    except Exception:
        pass

    # 2. Usar consulta unificada para GPUs generales (AMD, Intel)
    try:
        info = _query_windows_system_info()
        if info["gpus"]:
            return info["gpus"]
    except Exception:
        pass

    return [{"name": "Generic Display Adapter", "vram": 0.0, "vendor": "Other"}]

def get_macos_gpus(total_ram_gb):
    gpus = []
    is_apple_silicon = platform.machine() == "arm64"
    
    try:
        out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"]).decode()
        
        chipsets = re.findall(r"Chipset Model:\s*(.*)", out)
        # Extraer núcleos (Cores) es muy importante en M1/M2/M3 para estimar potencia AI
        cores_matches = re.findall(r"Total Number of Cores:\s*(\d+)", out)
        
        for i, chipset in enumerate(chipsets):
            chipset = chipset.strip()
            vendor = "Apple" if "Apple" in chipset or is_apple_silicon else "AMD" if "AMD" in chipset or "Radeon" in chipset else "Intel" if "Intel" in chipset else "Other"
            
            # Añadir información de los núcleos al nombre de la GPU si existe
            if is_apple_silicon and i < len(cores_matches):
                chipset = f"{chipset} ({cores_matches[i]} Cores)"
            
            if is_apple_silicon:
                # macOS reserva dinámicamente aprox el 75% de la RAM para la GPU
                vram_gb = round(total_ram_gb * 0.75, 1)
                gpus.append({
                    "name": chipset,
                    "vram": vram_gb,
                    "vendor": "Apple",
                    "unified": True
                })
            else:
                # Intel Macs
                vram_match = re.search(r"VRAM \(Dynamic, Max\):\s*(\d+)\s*(MB|GB)", out)
                if not vram_match:
                    vram_match = re.search(r"VRAM \(Total\):\s*(\d+)\s*(MB|GB)", out)
                
                vram_gb = 0.0
                if vram_match:
                    amount = float(vram_match.group(1))
                    unit = vram_match.group(2)
                    vram_gb = amount if unit == "GB" else round(amount / 1024.0, 1)
                
                gpus.append({
                    "name": chipset,
                    "vram": vram_gb,
                    "vendor": vendor,
                    "unified": False
                })
        if gpus:
            return gpus
    except Exception:
        pass

    if is_apple_silicon:
        return [{
            "name": "Apple M-Series GPU",
            "vram": round(total_ram_gb * 0.75, 1),
            "vendor": "Apple",
            "unified": True
        }]
    return [{"name": "Intel Integrated Graphics", "vram": 0.5, "vendor": "Intel"}]

def get_linux_gpus():
    gpus = []
    # 1. Intentar nvidia-smi
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL
        ).decode()
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) == 2:
                name = parts[0].strip()
                vram_mib = float(parts[1].strip())
                gpus.append({
                    "name": name,
                    "vram": round(vram_mib / 1024.0, 1),
                    "vendor": "NVIDIA"
                })
        if gpus:
            return gpus
    except Exception:
        pass

    # 2. Intentar lspci para AMD/Intel
    try:
        out = subprocess.check_output("lspci | grep -i -E 'vga|3d|display'", shell=True, stderr=subprocess.DEVNULL).decode()
        for line in out.split("\n"):
            if not line.strip():
                continue
            name = line.split("controller:")[-1].strip()
            vendor = "Other"
            if "NVIDIA" in name.upper():
                vendor = "NVIDIA"
            elif "AMD" in name.upper() or "ATI" in name.upper() or "RADEON" in name.upper():
                vendor = "AMD"
            elif "INTEL" in name.upper():
                vendor = "Intel"
            
            vram_gb = 0.0
            gpus.append({
                "name": name,
                "vram": vram_gb, # Inicializamos en 0, lo buscaremos abajo
                "vendor": vendor
            })
            
        # Mejora: Buscar VRAM real para gráficas AMD en Linux leyendo el Kernel (sysfs)
        for gpu in gpus:
            if gpu["vendor"] == "AMD" and gpu["vram"] == 0.0:
                try:
                    vram_bytes = 0
                    # drm (Direct Rendering Manager) expone la info de memoria de AMD
                    for path in os.listdir("/sys/class/drm"):
                        if path.startswith("card") and "-" not in path:
                            mem_path = f"/sys/class/drm/{path}/device/mem_info_vram_total"
                            if os.path.exists(mem_path):
                                with open(mem_path, "r") as f:
                                    vram_bytes = max(vram_bytes, int(f.read().strip()))
                    if vram_bytes > 0:
                        gpu["vram"] = round(vram_bytes / (1024.0 ** 3), 1)
                except Exception:
                    pass
                    
        if gpus:
            return gpus
    except Exception:
        pass

    return [{"name": "Generic Linux Display Device", "vram": 0.0, "vendor": "Other"}]

def get_installed_ram():
    system = platform.system()
    try:
        if system == "Windows":
            info = _query_windows_system_info()
            return info["ram"]
        elif system == "Darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
            if out:
                return round(float(out) / (1024.0 ** 3), 1)
    except Exception:
        pass
    return None

def get_os_pretty_name():
    system = platform.system()
    try:
        if system == "Windows":
            # Registry query is extremely fast (takes < 1ms)
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                product_name = winreg.QueryValueEx(key, "ProductName")[0]
                build = int(winreg.QueryValueEx(key, "CurrentBuild")[0])
                winreg.CloseKey(key)
                
                if "Windows 10" in product_name and build >= 22000:
                    product_name = product_name.replace("Windows 10", "Windows 11")
                return product_name
            except Exception:
                pass
            
            release = platform.release()
            ver = platform.version()
            parts = ver.split(".")
            if len(parts) >= 3 and int(parts[2]) >= 22000 and release == "10":
                return "Microsoft Windows 11"
            return f"Microsoft Windows {release}"
        elif system == "Darwin":
            mac_ver = platform.mac_ver()[0]
            return f"macOS {mac_ver}"
        elif system == "Linux":
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip().strip('"')
            return "Linux"
    except Exception:
        pass
    return f"{system} {platform.release()}"

def detect_system():
    global _windows_sys_info_cache
    _windows_sys_info_cache = None  # Reset cache to force fresh lookup
    
    # Importar psutil dentro de la función para evitar fallos si el entorno virtual no está listo
    import psutil
    
    system = platform.system()
    arch = platform.machine()
    
    # 1. CPU & AVX2
    cpu_name = get_cpu_name()
    physical_cores = psutil.cpu_count(logical=False) or 0
    logical_cores = psutil.cpu_count(logical=True) or 0
    has_avx2 = check_avx2_support()
    
    # 2. RAM
    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / (1024.0 ** 3), 1)
    installed_ram_gb = get_installed_ram() or total_ram_gb
    
    # 3. Detección de Apple Silicon
    is_apple_silicon = (system == "Darwin" and arch == "arm64")
    
    # 4. GPU & VRAM
    if system == "Windows":
        gpus = get_windows_gpus()
    elif system == "Darwin":
        gpus = get_macos_gpus(total_ram_gb)
    elif system == "Linux":
        gpus = get_linux_gpus()
    else:
        gpus = [{"name": "Unknown GPU Device", "vram": 0.0, "vendor": "Other"}]
    
    # Limpiar y ajustar datos de la GPU
    for gpu in gpus:
        if "unified" not in gpu:
            gpu["unified"] = is_apple_silicon

    # Si la VRAM es 0, intentamos estimarla dinámicamente según el sistema
    for gpu in gpus:
        if gpu["vram"] <= 0.0:
            if gpu["vendor"] == "Intel":
                gpu["vram"] = round(total_ram_gb * 0.5, 1)
                gpu["unified"] = True
            elif gpu["vendor"] == "AMD" and is_apple_silicon:
                gpu["vram"] = round(total_ram_gb * 0.75, 1)
                gpu["unified"] = True

    return {
        "os": system,
        "os_pretty": get_os_pretty_name(),
        "os_release": platform.release(),
        "arch": arch,
        "cpu_name": cpu_name,
        "cores": physical_cores,
        "threads": logical_cores,
        "has_avx2": has_avx2,
        "ram": total_ram_gb,
        "ram_installed": installed_ram_gb,
        "is_apple_silicon": is_apple_silicon,
        "gpus": gpus
    }

if __name__ == "__main__":
    # Diagnostic test run
    try:
        import psutil
        print("Psutil instalado correctamente.")
    except ImportError:
        print("Psutil NO instalado.")
    specs = detect_system()
    print(json.dumps(specs, indent=2))