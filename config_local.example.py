# Copia este archivo como config_local.py y ajusta tus valores.
# config_local.py está excluido de Git, así cada desarrollador
# tiene su propia configuración sin afectar a los demás.

SOURCE_MODE = "serial"   # "serial" | "ble" | "simulated"

SERIAL_PORT = "COM3"     # Cambia al puerto que aparece en tu PC
SERIAL_BAUD = 115200

BLE_ADDRESS = "AA:BB:CC:DD:EE:FF"
BLE_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
