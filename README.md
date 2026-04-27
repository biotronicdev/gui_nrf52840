# Interfaz EMG — Proyecto MCBCI

Aplicación de escritorio para adquirir, visualizar y registrar señales biomédicas (EMG, giroscopio y acelerómetro) desde un dispositivo nRF.

## Requisitos

- Python 3.10 o superior
- Las dependencias listadas en `requirements.txt`

## Instalación

### 1. Clonar o copiar el proyecto

```bash
cd NRF_MCBCI/Interfaz
```

### 2. Crear y activar el entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Configuración

Copia el archivo de ejemplo y ajusta tu puerto COM o dirección BLE:

```bash
cp config_local.example.py config_local.py
```

Edita `config_local.py`:

```python
SOURCE_MODE = "serial"   # "serial" | "ble" | "simulated"
SERIAL_PORT  = "COM4"    # el puerto que aparece en tu PC
SERIAL_BAUD  = 115200
```

> `config_local.py` está excluido de Git. Cada integrante del equipo tiene el suyo propio.

## Ejecución

```bash
python main.py
```

## Modos de fuente de datos

| Modo | Descripción |
|---|---|
| `serial` | Lee desde el dispositivo nRF por puerto serial (USB) |
| `ble` | Recibe notificaciones BLE con `bleak` |
| `simulated` | Genera señal sintética para pruebas sin hardware |

## Estructura del proyecto

```
Interfaz/
├── main.py                   # Punto de entrada
├── interf_emg.py             # Lógica principal e interfaz
├── config.py                 # Configuración con valores por defecto
├── config_local.py           # Tu configuración personal (no en Git)
├── config_local.example.py   # Plantilla de configuración local
├── style.py                  # Estilos visuales Qt
├── requirements.txt          # Dependencias del proyecto
└── .gitignore
```

## Dependencias principales

- [PyQt6](https://pypi.org/project/PyQt6/) — interfaz gráfica
- [pyqtgraph](https://pypi.org/project/pyqtgraph/) — gráficas en tiempo real
- [pyserial](https://pypi.org/project/pyserial/) — comunicación serial
- [bleak](https://pypi.org/project/bleak/) — Bluetooth BLE
