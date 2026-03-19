# ERP Consultora - Sistema de Gestión

Sistema ERP desarrollado con Flask para la gestión integral de consultoras. Permite administrar clientes, proyectos, empleados y facturación con detalle.

## 🚀 Características

- ✅ **Dashboard interactivo** con gráficos de facturación
- ✅ **Gestión de clientes** (CRUD completo)
- ✅ **Gestión de proyectos** con asignación de responsables
- ✅ **Gestión de empleados** con roles (admin/consultor)
- ✅ **Facturación profesional** con detalle múltiple
- ✅ **Control de pagos** (facturas pagadas/pendientes)
- ✅ **Diseño responsive** con Bootstrap 5
- ✅ **Base de datos SQLite** (fácil migración a PostgreSQL)

## 📋 Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## 🔧 Instalación local

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/TU-USUARIO/TU-REPO.git
   cd erp-consultora

2. Crear y activar entorno virtual

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate

3. Instalar dependencias

pip install -r requirements.txt

4. Ejecutar la aplicación

python app.py

5. Abrir en el navegador

http://localhost:5000

6. 👤 Usuario por defecto
   
Email: admin@consultora.com
Contraseña: admin123

📁 Estructura del proyecto

erp-consultora/
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias
├── Procfile               # Configuración para Render
├── README.md              # Este archivo
├── .gitignore             # Archivos ignorados por Git
├── instance/              # Base de datos SQLite
│   └── erp_consultora.db
├── static/                # Archivos estáticos (CSS)
│   └── style.css
└── templates/             # Plantillas HTML
    ├── base.html
    ├── dashboard.html
    ├── clientes.html
    ├── proyectos.html
    ├── empleados.html
    ├── facturas.html
    └── factura_form.html