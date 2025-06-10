#!/usr/bin/env python3
"""
SETUP.PY
========
Script de Instalación Automática - BD Reporting Demo
Sistema de Business Intelligence para Ferretería Petapa

Autor: José Fernando Hurtarte
Email: jhurtarte1@gmail.com

Este script automatiza la instalación completa del sistema:
- Verificación de dependencias
- Configuración de entorno virtual
- Instalación de paquetes Python
- Configuración de base de datos
- Inicialización de datos
- Verificación del sistema

Uso:
    python setup.py --install    # Instalación completa
    python setup.py --verify     # Solo verificar sistema
    python setup.py --demo       # Configuración demo rápida
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import argparse
import json
from datetime import datetime

class Colors:
    """Colores para output en terminal"""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    """Imprimir header del script"""
    print(f"""
{Colors.BLUE}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                    BD-REPORTING-DEMO SETUP                      ║
║              Sistema de Business Intelligence                     ║
║                 Ferretería Petapa                                ║
╠══════════════════════════════════════════════════════════════════╣
║ Desarrollado por: José Fernando Hurtarte                         ║
║ Email: jhurtarte1@gmail.com                                      ║
║ Fecha: Diciembre 2024                                           ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.END}
""")

def print_step(step_num, total_steps, description):
    """Imprimir paso actual"""
    print(f"\n{Colors.BLUE}[{step_num}/{total_steps}]{Colors.END} {Colors.BOLD}{description}{Colors.END}")

def print_success(message):
    """Imprimir mensaje de éxito"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message):
    """Imprimir mensaje de advertencia"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message):
    """Imprimir mensaje de error"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    """Imprimir mensaje informativo"""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def run_command(command, capture_output=True, check=True):
    """Ejecutar comando del sistema"""
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
            return result.stdout.strip(), result.stderr.strip()
        else:
            result = subprocess.run(command, shell=True, check=check)
            return "", ""
    except subprocess.CalledProcessError as e:
        return "", str(e)

def check_python_version():
    """Verificar versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ requerido. Versión actual: {version.major}.{version.minor}")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
    return True

def check_git():
    """Verificar si Git está instalado"""
    stdout, stderr = run_command("git --version", check=False)
    if stderr:
        print_warning("Git no encontrado. Instalar Git para mejor experiencia.")
        return False
    
    print_success("Git disponible ✓")
    return True

def check_postgresql():
    """Verificar si PostgreSQL está disponible"""
    # Verificar cliente psql
    stdout, stderr = run_command("psql --version", check=False)
    if stderr:
        print_warning("PostgreSQL cliente no encontrado.")
        print_info("El sistema puede funcionar con archivos CSV o PostgreSQL remoto.")
        return False
    
    print_success("PostgreSQL cliente disponible ✓")
    return True

def create_virtual_environment():
    """Crear entorno virtual"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print_warning("Entorno virtual ya existe. Eliminando...")
        shutil.rmtree(venv_path)
    
    print_info("Creando entorno virtual...")
    stdout, stderr = run_command(f"{sys.executable} -m venv venv")
    
    if stderr:
        print_error(f"Error creando entorno virtual: {stderr}")
        return False
    
    print_success("Entorno virtual creado ✓")
    return True

def get_venv_python():
    """Obtener ruta del Python del entorno virtual"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\python.exe"
    else:
        return "venv/bin/python"

def get_venv_pip():
    """Obtener ruta del pip del entorno virtual"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\pip.exe"
    else:
        return "venv/bin/pip"

def install_requirements():
    """Instalar dependencias de Python"""
    print_info("Instalando dependencias de Python...")
    
    pip_cmd = get_venv_pip()
    
    # Actualizar pip
    stdout, stderr = run_command(f"{pip_cmd} install --upgrade pip")
    if stderr and "error" in stderr.lower():
        print_error(f"Error actualizando pip: {stderr}")
        return False
    
    # Instalar requirements
    if Path("requirements.txt").exists():
        stdout, stderr = run_command(f"{pip_cmd} install -r requirements.txt")
        if stderr and "error" in stderr.lower():
            print_error(f"Error instalando dependencias: {stderr}")
            return False
    else:
        # Instalar dependencias básicas manualmente
        packages = [
            "streamlit>=1.28.0",
            "pandas>=2.0.0",
            "numpy>=1.24.0",
            "plotly>=5.15.0",
            "scikit-learn>=1.3.0",
            "psycopg2-binary>=2.9.0",
            "sqlalchemy>=2.0.0"
        ]
        
        for package in packages:
            print_info(f"Instalando {package}...")
            stdout, stderr = run_command(f"{pip_cmd} install {package}")
            if stderr and "error" in stderr.lower():
                print_warning(f"Advertencia instalando {package}: {stderr}")
    
    print_success("Dependencias instaladas ✓")
    return True

def create_env_file():
    """Crear archivo de configuración .env"""
    env_content = """# CONFIGURACIÓN BD-REPORTING-DEMO
# ================================

# Base de Datos PostgreSQL (Opcional)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ferreteria_petapa
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
DB_SSLMODE=prefer

# Para PostgreSQL en la nube (Heroku, AWS RDS, etc.)
# DATABASE_URL=postgresql://usuario:password@host:puerto/database

# Configuración de aplicación
DEBUG_MODE=false
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=false
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Datos de demo
LOAD_SAMPLE_DATA=true
USE_CSV_FALLBACK=true
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print_success("Archivo .env creado ✓")
    print_info("Edita .env para configurar tu base de datos PostgreSQL")

def create_directory_structure():
    """Crear estructura de directorios necesaria"""
    directories = [
        "data",
        "sql", 
        "backups",
        "logs",
        "reports",
        "docs",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print_success("Estructura de directorios creada ✓")

def verify_data_files():
    """Verificar que los archivos de datos existen"""
    required_files = [
        "data/inventario_expandido.csv",
        "data/categorias.csv",
        "data/proveedores.csv",
        "data/ubicaciones.csv"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print_warning("Archivos de datos faltantes:")
        for file in missing_files:
            print(f"  - {file}")
        
        print_info("Creando archivos de datos de ejemplo...")
        create_sample_data()
    else:
        print_success("Archivos de datos verificados ✓")
    
    return True

def create_sample_data():
    """Crear datos de ejemplo si no existen"""
    # Este es un ejemplo básico - en producción cargarías desde los CSVs reales
    sample_data = {
        "categorias.csv": """categoria_id,nombre_categoria,descripcion,margen_promedio,activo,fecha_creacion
1,Herramientas Manuales,Martillos y herramientas básicas,0.35,TRUE,2023-01-15
2,Herramientas Eléctricas,Taladros y sierras,0.25,TRUE,2023-01-15
3,Tornillería,Tornillos y fijaciones,0.40,TRUE,2023-01-15""",
        
        "proveedores.csv": """proveedor_id,nombre_proveedor,contacto,telefono,email,ciudad,tiempo_entrega_dias,calificacion,activo
1,Ferremax Guatemala,Carlos Méndez,2234-5678,ventas@ferremax.gt,Guatemala,3,4.5,TRUE
2,Distribuidora Central,Ana López,2345-6789,pedidos@distcentral.com,Guatemala,5,4.2,TRUE""",
        
        "ubicaciones.csv": """ubicacion_id,seccion,pasillo,estante,nivel,capacidad_maxima,descripcion
1,A,1,A,1,50,Herramientas manuales básicas
2,A,1,A,2,50,Herramientas eléctricas
3,B,1,B,1,75,Tornillería y fijaciones""",
        
        "inventario_expandido.csv": """producto_id,nombre,descripcion,categoria_id,proveedor_id,ubicacion_id,stock_actual,stock_minimo,punto_reorden,costo_unitario,precio_venta,ventas_mes_actual,ventas_mes_anterior,activo
1,Martillo 16oz,Martillo profesional,1,1,1,25,5,10,50.00,75.00,15,12,TRUE
2,Taladro 12V,Taladro inalámbrico,2,2,2,8,3,8,300.00,450.00,5,4,TRUE
3,Tornillo #8,Tornillo autoperforante,3,1,3,150,30,50,0.50,0.75,100,85,TRUE"""
    }
    
    for filename, content in sample_data.items():
        file_path = Path("data") / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    print_success("Datos de ejemplo creados ✓")

def setup_database():
    """Configurar base de datos"""
    python_cmd = get_venv_python()
    
    print_info("Intentando configurar base de datos...")
    
    # Verificar si database_config.py existe
    if not Path("database_config.py").exists():
        print_warning("database_config.py no encontrado. Saltando configuración de BD.")
        return True
    
    # Intentar configurar BD
    stdout, stderr = run_command(f"{python_cmd} database_config.py --test", check=False)
    
    if stderr and "error" in stderr.lower():
        print_warning("No se pudo conectar a PostgreSQL.")
        print_info("El sistema funcionará con archivos CSV.")
        return True
    
    # Si la conexión funciona, configurar completamente
    stdout, stderr = run_command(f"{python_cmd} database_config.py --setup", check=False)
    
    if stderr and "error" in stderr.lower():
        print_warning(f"Advertencia en configuración de BD: {stderr}")
    else:
        print_success("Base de datos configurada ✓")
    
    return True

def verify_installation():
    """Verificar que la instalación funciona"""
    python_cmd = get_venv_python()
    
    print_info("Verificando instalación...")
    
    # Verificar que se puede importar streamlit
    test_script = """
import streamlit as st
import pandas as pd
import plotly.express as px
print("✅ Imports básicos funcionan")

# Verificar archivos de datos
import os
data_files = ['data/inventario_expandido.csv', 'data/categorias.csv']
for file in data_files:
    if os.path.exists(file):
        print(f"✅ {file} encontrado")
    else:
        print(f"⚠️ {file} no encontrado")

print("✅ Verificación completada")
"""
    
    with open("test_installation.py", "w") as f:
        f.write(test_script)
    
    stdout, stderr = run_command(f"{python_cmd} test_installation.py")
    
    # Limpiar archivo temporal
    Path("test_installation.py").unlink(missing_ok=True)
    
    if stderr and "error" in stderr.lower():
        print_error(f"Error en verificación: {stderr}")
        return False
    
    print(stdout)
    print_success("Verificación de instalación completada ✓")
    return True

def create_run_scripts():
    """Crear scripts para ejecutar la aplicación"""
    
    # Script para Windows
    windows_script = f"""@echo off
echo Iniciando BD-Reporting-Demo...
{get_venv_python()} -m streamlit run app.py
pause
"""
    
    with open("run_windows.bat", "w") as f:
        f.write(windows_script)
    
    # Script para Linux/Mac
    unix_script = f"""#!/bin/bash
echo "Iniciando BD-Reporting-Demo..."
{get_venv_python()} -m streamlit run app.py
"""
    
    with open("run_unix.sh", "w") as f:
        f.write(unix_script)
    
    # Hacer ejecutable en Unix
    if platform.system() != "Windows":
        os.chmod("run_unix.sh", 0o755)
    
    print_success("Scripts de ejecución creados ✓")

def generate_installation_report():
    """Generar reporte de instalación"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "architecture": platform.architecture()[0]
        },
        "installation": {
            "virtual_env": Path("venv").exists(),
            "env_file": Path(".env").exists(),
            "data_files": Path("data").exists(),
            "requirements": Path("requirements.txt").exists()
        },
        "next_steps": [
            "1. Editar archivo .env con configuración de base de datos",
            "2. Ejecutar 'python database_config.py --setup' si usas PostgreSQL",
            "3. Ejecutar 'streamlit run app.py' para iniciar la aplicación",
            "4. Abrir http://localhost:8501 en el navegador"
        ]
    }
    
    with open("installation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print_success("Reporte de instalación generado ✓")
    return report

def print_final_instructions():
    """Imprimir instrucciones finales"""
    print(f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════════╗
║                    INSTALACIÓN COMPLETADA                       ║
╚══════════════════════════════════════════════════════════════════╝
{Colors.END}

{Colors.BOLD}📋 PRÓXIMOS PASOS:{Colors.END}

{Colors.BLUE}1. Configurar Base de Datos (Opcional):{Colors.END}
   - Editar archivo .env con tus
