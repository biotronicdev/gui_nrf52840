# Modo de fuente: "serial" | "ble" | "simulated"
SOURCE_MODE = "serial"

SERIAL_PORT = "COM3"
SERIAL_BAUD = 115200

BLE_ADDRESS = "AA:BB:CC:DD:EE:FF"
BLE_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

INT16_SCALE = 0.001

# Carga configuración local si existe (no se sube a Git)
try:
    from config_local import *
except ImportError:
    pass
