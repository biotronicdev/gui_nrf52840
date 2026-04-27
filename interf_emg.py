# Importa sys para manejar argumentos del sistema y cerrar la app correctamente
import sys

# Importa random para generar ruido aleatorio en la simulación
import random

# Importa math para usar seno, pi, etc. en la simulación
import math

# Importa time para medir tiempo y timestamps
import time

# Importa threading para correr la lectura serial en un hilo aparte
import threading

# Importa asyncio para manejar BLE de forma asíncrona
import asyncio

# Importa cliente BLE
from bleak import BleakClient

# Importa json para exportar datos estructurados
import json

# Importa csv para exportar sesiones en archivos CSV
import csv

# Importa os para trabajar con rutas y carpetas
import os

# Importa datetime para generar fechas y horas legibles
from datetime import datetime

# Importa deque para almacenar muestras con tamaño máximo eficiente
from collections import deque

# Importa dataclass para crear estructuras simples tipo objeto
from dataclasses import dataclass

# Importa tipos opcionales y listas/diccionarios para claridad del código
from typing import Optional, List, Dict

# Importa widgets principales de PyQt6
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,   # App, contenedores, botones y etiquetas
    QVBoxLayout, QHBoxLayout, QFrame,             # Layouts vertical/horizontal y marcos
    QMessageBox, QFileDialog,                     # Ventanas de mensaje y selector de archivos
    QListWidget, QTabWidget, QMainWindow,         # Lista, tabs y ventana principal
    QLineEdit, QDialog, QFormLayout, QDateEdit,   # Cajas de texto, diálogos, formularios y fecha
    QTextEdit, QComboBox, QDoubleSpinBox, QGroupBox, # Texto largo, combo, número decimal y grupos
    QListWidgetItem, QSplitter                    # Ítems de lista y divisor redimensionable
)

# Importa clases básicas de Qt
from PyQt6.QtCore import Qt, QTimer, QDate, QRegularExpression

# Importa QPixmap para mostrar imágenes y validadores de texto
from PyQt6.QtGui import QPixmap, QRegularExpressionValidator

# Importa pyqtgraph para dibujar señales en tiempo real
import pyqtgraph as pg

# Se importa lo del archivo de config.py 
from config import *




#  DATA TYPES para los tipos de datos o estrucutras que se van a usar 

# Dataclass para guardar una muestra de señal
@dataclass
class Sample: # Saample es una sola muestra de la señal 
    # Tiempo en el que llego la muestra
    t: float

    # Lista de 3 valores [canal1, canal2, canal3], EMG, giroscopio y acelerometro
    values: List[float]


#   DATA SOURCE LAYER

# Es la caoa de fuente de datos, de donde salen 
class DataSource:
    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def read_latest(self) -> Optional[Sample]:
        raise NotImplementedError

    def drain(self) -> List[Sample]:
        s = self.read_latest()
        return [s] if s else []


# VIDs USB de fabricantes comunes de placas nRF52840
_NRF_VIDS = {0x2886, 0x1915, 0x239A, 0x2341, 0x1366}

def auto_detect_serial_port() -> Optional[str]:
    """Busca el primer puerto COM que coincida con VIDs conocidos de nRF52840.
    Si no encuentra ninguno, devuelve el primer puerto disponible."""
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if p.vid in _NRF_VIDS:
            return p.device
    if ports:
        return ports[0].device
    return None


# Función que intenta convertir un payload recibido en 3 floats
def parse_payload_to_3floats(payload: bytes) -> Optional[List[float]]:
    """
    Soporta:
    1) Texto CSV: b"0.12,-0.03,0.44\\n"
    2) Binario int16: 6 bytes => 3 canales
    """

    # Primer intento: interpretar como texto UTF-8 CSV o valor único
    try:
        # Convierte bytes a string y quita espacios o saltos de línea
        s = payload.decode("utf-8", errors="strict").strip()

        # Revisa que la cadena no está vacía
        if s:
            # Parte por comas y limpia espacios
            parts = [p.strip() for p in s.split(",")]

            # Si hay 3 o más valores separados por coma
            if len(parts) >= 3:
                return [float(parts[0]), float(parts[1]), float(parts[2])]

            # Si hay un solo valor (ej. "248\n"), lo manda al canal 1
            if len(parts) == 1:
                val = float(parts[0])
                return [val, 0.0, 0.0]
    except Exception:
        # Si falla pasa a un segundo intento
        pass

    # Segundo intento en interpretar como 3 enteros de 16 bits
    if len(payload) >= 6: #cada canal ocupa 2 bytes, 3 chan por 2 bytes = 6 bytes 
        try:
            # struct para desempacar bytes binarios, interpreta como numeros 
            import struct

            # Desempaca 3 enteros con little-endian o sea que l bit menos significativo va primero
            ch1, ch2, ch3 = struct.unpack("<hhh", payload[:6])
            # h es un entero de 16 bits con signo, hhh son tres enteros seguidos 

            # Escala los enteros a valores reales
            return [ch1 * INT16_SCALE, ch2 * INT16_SCALE, ch3 * INT16_SCALE]
        except Exception:
            # Si falla regresa None
            return None

    # Si no se pudo interpretar regresa None
    return None


# Fuente de datos simulada
class SimulatedEMGSource(DataSource):
    
    def __init__(self):
        # Bandera para saber si está corriendo
        self.running = False
        # Tiempo inicial
        self.t0 = time.time()

    # Inicia la simulación
    def start(self):
        self.running = True
        self.t0 = time.time()

    # Detiene la simulación
    def stop(self):
        self.running = False

    # Devuelve una muestra simulada
    def read_latest(self) -> Optional[Sample]:
        # Si no está corriendo, no regresa nada
        if not self.running:
            return None

        # Tiempo relativo desde que inició, cuantos s han pasado desde que incio 
        t = time.time() - self.t0

        # Señal base lenta tipo seno
        base = 0.08 * math.sin(2 * math.pi * 2.0 * t)

        # Componente burst rápida
        burst = 0.0

        # Cada ciertos segundos mete ráfagas
        if int(t) % 5 in (2, 3):
            burst = 0.35 * math.sin(2 * math.pi * 40.0 * t)

        # Canal 1 = base + burst + ruido
        ch1 = base + burst + random.uniform(-0.08, 0.08)

        # Canal 2 = variación del canal 1
        ch2 = 0.9 * base + 0.8 * burst + random.uniform(-0.08, 0.08)

        # Canal 3 = otra variación
        ch3 = 1.1 * base + 0.6 * burst + random.uniform(-0.08, 0.08)

        # Regresa muestra con tiempo y los 3 canales
        return Sample(t=t, values=[ch1, ch2, ch3])


# Fuente de datos por puerto serial
class NRFSerialSource(DataSource):
    """
    Lee del puerto serial en un hilo.
    Espera líneas tipo:
      0.12,-0.03,0.44\\n
    o bytes binarios int16.
    """

    # Constructor
    def __init__(self, port: str, baud: int):
        # Guarda puerto
        self.port = port

        # Guarda baudrate
        self.baud = baud

        # Bandera de ejecución
        self._running = False

        # Hilo lector
        self._thread: Optional[threading.Thread] = None

        # Buffer que acumula todas las muestras sin perder ninguna
        self._buffer: deque = deque(maxlen=2000)

        # Lock para acceso seguro entre hilos
        self._lock = threading.Lock()

        # Tiempo inicial
        self._t0 = 0.0

        # Objeto serial
        self._ser = None

    # Inicia la lectura serial
    def start(self):
        import serial

        if self._running:
            return

        # Si el puerto es "auto", detecta el primero disponible
        port = self.port
        if port.lower() == "auto":
            port = auto_detect_serial_port()
            if not port:
                raise RuntimeError("No se encontró ningún puerto serial disponible.")

        self._ser = serial.Serial(port, self.baud, timeout=0.1)

        # Marca como corriendo
        self._running = True

        # Reinicia tiempo base
        self._t0 = time.time()

        # Crea hilo lector
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)

        # Arranca hilo
        self._thread.start()

    # Detiene la lectura serial
    def stop(self):
        # Baja bandera
        self._running = False

        # Si existe hilo, espera un poco a que termine
        if self._thread:
            self._thread.join(timeout=1.0)

        # Limpia referencia al hilo
        self._thread = None

        # Intenta cerrar el puerto
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass

        # Limpia referencia serial
        self._ser = None

    # Bucle interno del hilo lector
    def _reader_loop(self):
        # Buffer para acumular bytes
        buffer = bytearray()

        # Mientras esté corriendo y exista serial
        while self._running and self._ser:
            try:
                # Lee hasta 256 bytes
                chunk = self._ser.read(256)

                # Si no llegó nada, sigue
                if not chunk:
                    continue

                # Agrega lo leído al buffer
                buffer.extend(chunk)

                # Si llegaron líneas CSV completas
                while b"\n" in buffer:
                    # Separa una línea y lo restante
                    line, _, rest = buffer.partition(b"\n")

                    # Actualiza buffer con lo que sobró
                    buffer = bytearray(rest)

                    # Limpia espacios y saltos
                    payload = line.strip()

                    # Si la línea quedó vacía, la ignora
                    if not payload:
                        continue

                    # Intenta convertir payload en 3 floats
                    vals = parse_payload_to_3floats(payload)

                    # Si sí obtuvo 3 valores
                    if vals and len(vals) >= 3:
                        t = time.time() - self._t0
                        with self._lock:
                            self._buffer.append(Sample(t=t, values=vals[:3]))

                # Si no hay saltos de línea, intenta procesar binario puro de 6 bytes
                while len(buffer) >= 6 and b"\n" not in buffer:
                    payload = bytes(buffer[:6])
                    del buffer[:6]
                    vals = parse_payload_to_3floats(payload)
                    if vals and len(vals) >= 3:
                        t = time.time() - self._t0
                        with self._lock:
                            self._buffer.append(Sample(t=t, values=vals[:3]))

            except Exception:
                # Si algo falla, sigue intentando para no tirar la app
                continue

    def read_latest(self) -> Optional[Sample]:
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    def drain(self) -> List[Sample]:
        with self._lock:
            samples = list(self._buffer)
            self._buffer.clear()
            return samples


# Fuente de datos BLE
class NRFBLESource(DataSource):
    """
    BLE con bleak.
    Espera:
      - texto CSV "0.1,0.2,0.3"
      - o binario int16 de 6 bytes
    """

    # Constructor
    def __init__(self, address: str, char_uuid: str):
        # Dirección BLE
        self.address = address

        # UUID de característica
        self.char_uuid = char_uuid

        # Bandera de ejecución
        self._running = False

        # Última muestra recibida
        self._latest: Optional[Sample] = None

        # Lock para acceso seguro
        self._lock = threading.Lock()

        # Tiempo inicial
        self._t0 = 0.0

        # Hilo BLE
        self._thread: Optional[threading.Thread] = None

        # Loop asíncrono
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # Inicia el proceso BLE
    def start(self):
        # Si ya corre, no hace nada
        if self._running:
            return

        # Activa bandera
        self._running = True

        # Guarda tiempo base
        self._t0 = time.time()

        # Crea hilo para el loop async
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

        # Lo inicia
        self._thread.start()

    # Detiene BLE
    def stop(self):
        # Baja bandera
        self._running = False

        # Si existe loop, pide detenerlo
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

        # Espera al hilo
        if self._thread:
            self._thread.join(timeout=2.0)

        # Limpia referencias
        self._thread = None
        self._loop = None

    # Crea y corre el event loop async
    def _run_loop(self):
        # Crea un loop nuevo
        self._loop = asyncio.new_event_loop()

        # Lo asigna al hilo actual
        asyncio.set_event_loop(self._loop)

        try:
            # Ejecuta la tarea BLE
            self._loop.run_until_complete(self._ble_task())
        except Exception:
            pass

    # Tarea principal BLE
    async def _ble_task(self):
        # Callback que se ejecuta cada vez que llegan notificaciones
        def on_notify(_, data: bytearray):
            # Parsea bytes a 3 floats
            vals = parse_payload_to_3floats(bytes(data))

            # Si obtuvo 3 valores
            if vals and len(vals) >= 3:
                # Tiempo relativo
                t = time.time() - self._t0

                # Crea muestra
                s = Sample(t=t, values=vals[:3])

                # Guarda última muestra
                with self._lock:
                    self._latest = s

        # Abre conexión BLE
        async with BleakClient(self.address) as client:
            # Activa notificaciones
            await client.start_notify(self.char_uuid, on_notify)

            # Mientras siga corriendo
            while self._running:
                await asyncio.sleep(0.05)

            # Intenta detener notificaciones al salir
            try:
                await client.stop_notify(self.char_uuid)
            except Exception:
                pass

    # Devuelve última muestra BLE
    def read_latest(self) -> Optional[Sample]:
        with self._lock:
            return self._latest



# Widget que representa un monitor individual de señal
class MonitorEMG(QWidget):
    # Constructor
    def __init__(self, title_default="EMG", channel_index=0):
        super().__init__()

        # Índice del canal asociado
        self.channel_index = channel_index

        # Si el trigger está armado
        self.armed = False

        # Si está capturando
        self.capturing = False

        # Si ya se disparó el trigger
        self.triggered = False

        # Máximo de puntos a dibujar (2 segundos a 500 Hz)
        self.max_points = 1000

        # Cola de tiempos
        self.x = deque(maxlen=self.max_points)

        # Cola de amplitudes
        self.y = deque(maxlen=self.max_points)

        # Altura mínima del widget
        self.setMinimumHeight(205)

        # Altura máxima del widget
        self.setMaximumHeight(240)

        # Layout principal del monitor
        outer = QVBoxLayout(self)

        # Márgenes internos
        outer.setContentsMargins(8, 6, 8, 6)

        # Espacio entre elementos
        outer.setSpacing(6)

        # Título fijo no editable
        self.titulo1 = QLabel(title_default)

        # Estilo del título
        self.titulo1.setStyleSheet("""
            background-color: #222222;
            color: white;
            border: 1px solid #333333;
            border-radius: 8px;
            padding: 7px 10px;
            font-weight: 600;
        """)

        # Marco oscuro de la gráfica
        plot_frame = QFrame()

        # Estilo del marco
        plot_frame.setStyleSheet("""
            background-color: #111111;
            border-radius: 10px;
        """)

        # Layout del marco
        plot_layout = QVBoxLayout(plot_frame)

        # Márgenes de la gráfica
        plot_layout.setContentsMargins(6, 6, 6, 6)

        # Crea el widget de gráfica
        self.plot = pg.PlotWidget()

        # Fondo oscuro
        self.plot.setBackground("#111111")

        # Muestra cuadrícula
        self.plot.showGrid(x=True, y=True, alpha=0.20)

        # Desactiva menú contextual
        self.plot.setMenuEnabled(False)

        # Desactiva pan/zoom con mouse
        self.plot.setMouseEnabled(x=False, y=False)

        # Oculta botones de pyqtgraph
        self.plot.getPlotItem().hideButtons()

        # Ajusta alturas
        self.plot.setMinimumHeight(110)
        self.plot.setMaximumHeight(130)

        # Color de texto ejes
        self.plot.getAxis("left").setTextPen("#b8c7e6")
        self.plot.getAxis("bottom").setTextPen("#b8c7e6")

        # Color de líneas ejes
        self.plot.getAxis("left").setPen("#7f8ea3")
        self.plot.getAxis("bottom").setPen("#7f8ea3")

        # Crea curva vacía
        self.curve = self.plot.plot([], [], pen=pg.mkPen("#4f8cff", width=2))

        # Mete la gráfica al layout
        plot_layout.addWidget(self.plot)

        # Layout horizontal para controles
        controls = QHBoxLayout()

        # Espacio entre controles
        controls.setSpacing(6)

        # Botón para armar/desarmar trigger
        self.btn_arm = QPushButton("Armar trigger")

        # Conecta click del botón con método toggle_arm
        self.btn_arm.clicked.connect(self.toggle_arm)

        # Combo de tipo de trigger
        self.cmb_trigger = QComboBox()

        # Agrega opciones
        self.cmb_trigger.addItems(["Manual", "Umbral"])

        # Si cambia el combo, actualiza botones
        self.cmb_trigger.currentTextChanged.connect(self._mode_changed)

        # Spin para umbral
        self.spin_threshold = QDoubleSpinBox()

        # Número de decimales
        self.spin_threshold.setDecimals(3)

        # Rango
        self.spin_threshold.setRange(0.0, 10.0)

        # Paso entre valores
        self.spin_threshold.setSingleStep(0.01)

        # Valor inicial
        self.spin_threshold.setValue(0.25)

        # Botón disparar para trigger manual
        self.btn_fire = QPushButton("Disparar")

        # Conecta a manual_fire
        self.btn_fire.clicked.connect(self.manual_fire)

        # Empieza deshabilitado
        self.btn_fire.setEnabled(False)

        # Etiqueta de estado
        self.lbl_state = QLabel("Estado: en espera")

        # Estilo de estado
        self.lbl_state.setStyleSheet("color: gray; font-weight: 600;")

        # Mete controles al layout
        controls.addWidget(self.btn_arm)
        controls.addWidget(QLabel("Tipo:"))
        controls.addWidget(self.cmb_trigger)
        controls.addWidget(QLabel("Umbral:"))
        controls.addWidget(self.spin_threshold)
        controls.addWidget(self.btn_fire)
        controls.addStretch()
        controls.addWidget(self.lbl_state)

        # Agrega título al monitor
        outer.addWidget(self.titulo1)

        # Agrega gráfica
        outer.addWidget(plot_frame)

        # Agrega fila de controles
        outer.addLayout(controls)

    # Método llamado cuando cambia el tipo de trigger
    def _mode_changed(self, _):
        # Si está armado, habilita disparo manual solo si el modo es Manual
        if self.armed:
            self.btn_fire.setEnabled(self.cmb_trigger.currentText() == "Manual")

    # Arma o desarma trigger
    def toggle_arm(self):
        # Invierte estado
        self.armed = not self.armed

        # Si quedó armado
        if self.armed:
            # Resetea banderas
            self.capturing = False
            self.triggered = False

            # Cambia texto del botón
            self.btn_arm.setText("Desarmar")

            # Habilita o no el botón disparar según el modo
            self.btn_fire.setEnabled(self.cmb_trigger.currentText() == "Manual")

            # Cambia estado visual
            self.lbl_state.setText("Estado: trigger armado")
            self.lbl_state.setStyleSheet("color: #f0a500; font-weight: 600;")
        else:
            # Si se desarma
            self.btn_arm.setText("Armar trigger")
            self.btn_fire.setEnabled(False)
            self.capturing = False
            self.triggered = False
            self.lbl_state.setText("Estado: en espera")
            self.lbl_state.setStyleSheet("color: gray; font-weight: 600;")

    # Dispara manualmente el trigger
    def manual_fire(self):
        # Solo si está armado y en modo manual
        if self.armed and self.cmb_trigger.currentText() == "Manual":
            self._set_triggered()

    # Cambia a estado de captura
    def _set_triggered(self):
        # Marca que se disparó
        self.triggered = True

        # Marca que ya captura
        self.capturing = True

        # Cambia texto de estado
        self.lbl_state.setText("Estado: CAPTURANDO")

        # Color verde
        self.lbl_state.setStyleSheet("color: #22c55e; font-weight: 700;")

        # Limpia datos previos dibujados
        self.x.clear()
        self.y.clear()

    # Recibe una muestra nueva para este monitor
    def push_sample(self, t: float, value: float):
        # Si no está armado, no hace nada
        if not self.armed:
            return

        # Lee modo actual
        mode = self.cmb_trigger.currentText()

        # Si el modo es umbral y aún no se disparó
        if mode == "Umbral" and not self.triggered:
            # Lee el umbral
            thr = float(self.spin_threshold.value())

            # Si el valor rebasa el umbral
            if abs(value) >= thr:
                self._set_triggered()

        # Si ya está capturando, agrega y redibuja
        if self.capturing:
            self.x.append(t)
            self.y.append(value)
            self.curve.setData(list(self.x), list(self.y))

    # Limpia la gráfica visualmente
    def reset_view(self):
        self.x.clear()
        self.y.clear()
        self.curve.setData([], [])




#registo de paciente


# Diálogo para registrar un nuevo paciente
class NuevoPacienteDialog(QDialog):
    # Constructor
    def __init__(self, parent=None):
        super().__init__(parent)

        # Título de la ventana
        self.setWindowTitle("Nuevo paciente")

        # Ancho mínimo
        self.setMinimumWidth(420)

        # Campo nombre
        self.nombre = QLineEdit()

        # Campo apellido
        self.apellido = QLineEdit()

        # Campo fecha
        self.nacimiento = QDateEdit()

        # Habilita calendario emergente
        self.nacimiento.setCalendarPopup(True)

        # Fecha inicial = hoy
        self.nacimiento.setDate(QDate.currentDate())

        # Formato visual de fecha
        self.nacimiento.setDisplayFormat("yyyy-MM-dd")

        # Campo contacto
        self.contacto = QLineEdit()

        # Placeholder
        self.contacto.setPlaceholderText("Solo números")

        # Validador para aceptar hasta 15 dígitos
        self.contacto.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{0,15}$")))

        # Campo de texto largo para padecimiento
        self.padecimiento = QTextEdit()

        # Placeholder
        self.padecimiento.setPlaceholderText("Describe el padecimiento")

        # Layout de formulario
        form = QFormLayout()

        # Agrega filas
        form.addRow("Nombre:", self.nombre)
        form.addRow("Apellido:", self.apellido)
        form.addRow("Fecha de nacimiento:", self.nacimiento)
        form.addRow("Contacto:", self.contacto)
        form.addRow("Padecimiento:", self.padecimiento)

        # Layout horizontal para botones
        btns = QHBoxLayout()

        # Botón cancelar
        self.btn_cancel = QPushButton("Cancelar")

        # Botón guardar
        self.btn_save = QPushButton("Guardar")

        # Cancelar cierra rechazando
        self.btn_cancel.clicked.connect(self.reject)

        # Guardar acepta diálogo
        self.btn_save.clicked.connect(self.accept)

        # Empuja botones a la derecha
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_save)

        # Layout principal
        layout = QVBoxLayout(self)

        # Agrega formulario
        layout.addLayout(form)

        # Agrega fila de botones
        layout.addLayout(btns)

    # Regresa los datos capturados como diccionario
    def get_data(self) -> Dict:
        return {
            "Nombre": self.nombre.text().strip(),
            "Apellido": self.apellido.text().strip(),
            "Nacimiento": self.nacimiento.date().toString("yyyy-MM-dd"),
            "Contacto": self.contacto.text().strip(),
            "Padecimiento": self.padecimiento.toPlainText().strip(),
        }


# =======================
#   TAB SENSOR
# =======================

# Pestaña completa de adquisición por sensor
class SensorTab(QWidget):
    # Constructor
    def __init__(self, nombre_tab: str, source: DataSource, main_window):
        super().__init__()

        # Nombre de la pestaña
        self.nombre_tab = nombre_tab

        # Fuente de datos asociada
        self.source = source

        # Referencia a la ventana principal
        self.main_window = main_window

        # Sesión activa actual
        self.active_session = None

        # Tiempo de la última muestra para no repetir
        self.last_sample_time = None

        # Layout principal
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(8)
        self.main_layout.setContentsMargins(12, 10, 12, 10)

        # Caja para nombre del estudio
        self.titulo_estudio = QLineEdit()

        # Texto sugerido
        self.titulo_estudio.setPlaceholderText("Ej. Flexión de brazo / Prueba 1")

        # Grupo info de sesión
        info_box = QGroupBox("Sesión actual")

        # Layout del grupo
        info_layout = QHBoxLayout(info_box)

        # Etiqueta del paciente activo
        self.lbl_paciente_actual = QLabel("Paciente activo: Ninguno")
        self.lbl_paciente_actual.setStyleSheet("font-weight: 600; color: #2f2f2f;")

        # Etiqueta del ID de sesión
        self.lbl_sesion = QLabel("Sesión: sin iniciar")
        self.lbl_sesion.setStyleSheet("color: #666666;")

        # Agrega al layout
        info_layout.addWidget(self.lbl_paciente_actual)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_sesion)

        # Grupo de adquisición
        ctrl_box = QGroupBox("Adquisición")

        # Layout horizontal
        ctrl_layout = QHBoxLayout(ctrl_box)

        # Botón iniciar
        self.btn_start = QPushButton("Conectar / Iniciar")

        # Botón detener
        self.btn_stop = QPushButton("Detener")

        # Inicia deshabilitado
        self.btn_stop.setEnabled(False)

        # Conecta acciones
        self.btn_start.clicked.connect(self.start_acq)
        self.btn_stop.clicked.connect(self.stop_acq)

        # Etiqueta de estado de conexión
        self.lbl_conn = QLabel("Estado: detenido")
        self.lbl_conn.setStyleSheet("color: gray; font-weight: 600;")

        # Agrega widgets al layout
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.lbl_conn)

        # Crea 3 monitores
        self.m1 = MonitorEMG("EMG 1", channel_index=0)
        self.m2 = MonitorEMG("Giroscopio", channel_index=1)
        self.m3 = MonitorEMG("Acelerómetro", channel_index=2)

        # Timer para refrescar interfaz
        self.timer = QTimer(self)

        # Intervalo 20 ms
        self.timer.setInterval(20)

        # Al expirar, jala la última muestra
        self.timer.timeout.connect(self.pull_and_update)

        # Mete widgets al layout principal
        self.main_layout.addWidget(self.titulo_estudio)
        self.main_layout.addWidget(info_box)
        self.main_layout.addWidget(ctrl_box)
        self.main_layout.addWidget(self.m1)
        self.main_layout.addWidget(self.m2)
        self.main_layout.addWidget(self.m3)
        self.main_layout.addStretch()

    # Actualiza la etiqueta del paciente activo
    def update_selected_patient_label(self):
        # Pregunta a la ventana principal cuál paciente está seleccionado
        p = self.main_window.get_selected_patient()

        # Si sí hay paciente
        if p:
            self.lbl_paciente_actual.setText(
                f"Paciente activo: {p['ID']} - {p['Nombre']} {p['Apellido']}"
            )
        else:
            # Si no hay paciente
            self.lbl_paciente_actual.setText("Paciente activo: Ninguno")

    # Inicia adquisición
    def start_acq(self):
        # Obtiene paciente seleccionado
        paciente = self.main_window.get_selected_patient()

        # Si no hay paciente, no permite iniciar
        if not paciente:
            QMessageBox.warning(
                self,
                "Paciente no seleccionado",
                "Primero selecciona un paciente en la pestaña Registro."
            )
            return

        try:
            # Limpia gráficas antes de arrancar
            self.m1.reset_view()
            self.m2.reset_view()
            self.m3.reset_view()

            # Inicia fuente de datos
            self.source.start()

            # Inicia timer visual
            self.timer.start()

            # Deshabilita iniciar
            self.btn_start.setEnabled(False)

            # Habilita detener
            self.btn_stop.setEnabled(True)

            # Cambia etiqueta de estado
            self.lbl_conn.setText("Estado: recibiendo datos")
            self.lbl_conn.setStyleSheet("color: #22c55e; font-weight: 700;")

            # Actualiza quién es el paciente activo
            self.update_selected_patient_label()

            # Toma nombre del estudio escrito por el usuario
            study_name = self.titulo_estudio.text().strip()

            # Si está vacío, crea uno por defecto
            if not study_name:
                study_name = f"Estudio {self.nombre_tab}"

            # Crea ID de sesión usando fecha y hora
            session_id = f"S{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Crea diccionario de sesión activa
            self.active_session = {
                "session_id": session_id,
                "patient_id": paciente["ID"],
                "patient_name": f"{paciente['Nombre']} {paciente['Apellido']}",
                "sensor_tab": self.nombre_tab,
                "study_name": study_name,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "samples": []
            }

            # Muestra el ID de sesión
            self.lbl_sesion.setText(f"Sesión: {session_id}")

            # Reinicia última muestra
            self.last_sample_time = None

        except Exception as e:
            # Si falla, muestra error
            QMessageBox.critical(self, "Error", f"No se pudo iniciar la adquisición:\n{e}")

    # Detiene adquisición
    def stop_acq(self):
        # Detiene timer
        self.timer.stop()

        # Intenta detener fuente
        try:
            self.source.stop()
        except Exception:
            pass

        # Reactiva botón iniciar
        self.btn_start.setEnabled(True)

        # Desactiva detener
        self.btn_stop.setEnabled(False)

        # Cambia estado visual
        self.lbl_conn.setText("Estado: detenido")
        self.lbl_conn.setStyleSheet("color: gray; font-weight: 600;")

        # Si había sesión y sí tenía muestras
        if self.active_session and len(self.active_session["samples"]) > 0:
            # Guarda sesión dentro del paciente
            self.main_window.save_session_to_patient(self.active_session)

            # Informa al usuario
            QMessageBox.information(
                self,
                "Sesión guardada",
                f"Se guardó la sesión {self.active_session['session_id']} "
                f"con {len(self.active_session['samples'])} muestras."
            )
        elif self.active_session:
            # Si existía sesión pero estaba vacía
            QMessageBox.warning(
                self,
                "Sesión vacía",
                "La sesión no tenía muestras y no se guardó."
            )

        # Limpia sesión activa
        self.active_session = None

        # Restablece etiqueta
        self.lbl_sesion.setText("Sesión: sin iniciar")

        # Limpia última muestra
        self.last_sample_time = None

    # Método llamado periódicamente por el timer — drena todas las muestras acumuladas
    def pull_and_update(self):
        samples = self.source.drain()
        if not samples:
            return

        for s in samples:
            v = s.values
            if len(v) >= 3:
                self.m1.push_sample(s.t, v[0])
                self.m2.push_sample(s.t, v[1])
                self.m3.push_sample(s.t, v[2])

                if self.active_session is not None:
                    self.active_session["samples"].append({
                        "t": float(s.t),
                        "emg": float(v[0]),
                        "gyro": float(v[1]),
                        "accel": float(v[2])
                    })

        self.last_sample_time = samples[-1].t



# Ventana principal del sistema
class VentanaPrincipal(QMainWindow):
    # Constructor
    def __init__(self):
        super().__init__()

        # Título de la ventana
        self.setWindowTitle("Proyecto EMG")

        # Posición y tamaño inicial
        self.setGeometry(100, 100, 1280, 780)

        # Crea widget de tabs
        self.tabs = QTabWidget()

        # Lo pone como contenido central
        self.setCentralWidget(self.tabs)

        # Lista de pacientes
        self.pacientes: List[Dict] = []

        # Contador para IDs
        self.paciente_id_counter = 1

        # ID del paciente actualmente seleccionado
        self.current_patient_id: Optional[str] = None

        # Lista de pestañas de sensor
        self.sensor_tabs: List[SensorTab] = []

        # Crea tabs
        self.crear_tab_registro()
        self.crear_tab_sensor("Sensor 1")
        self.crear_tab_sensor("Sensor 2")
        self.crear_tab_visualizacion()

    # Regresa el paciente seleccionado actualmente
    def get_selected_patient(self) -> Optional[Dict]:
        # Si no hay ID seleccionado, regresa None
        if not self.current_patient_id:
            return None

        # Busca el paciente con ese ID
        for p in self.pacientes:
            if p["ID"] == self.current_patient_id:
                return p

        # Si no lo encuentra, regresa None
        return None

    # Actualiza en todas las pestañas de sensor la etiqueta del paciente
    def actualizar_labels_paciente_en_sensores(self):
        for tab in self.sensor_tabs:
            tab.update_selected_patient_label()

    # Guarda una sesión dentro del paciente correspondiente
    def save_session_to_patient(self, session_data: Dict):
        # Toma el patient_id desde la sesión
        patient_id = session_data["patient_id"]

        # Busca el paciente correcto
        for p in self.pacientes:
            if p["ID"] == patient_id:
                # Agrega la sesión a la lista
                p["Sesiones"].append(session_data)

                # Actualiza panel derecho de registro
                self.actualizar_panel_paciente()
                return

    # Crea pestaña de registro
    def crear_tab_registro(self):
        # Crea widget tab
        tab = QWidget()

        # Layout principal horizontal
        main_layout = QHBoxLayout(tab)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Splitter para panel izquierdo y derecho
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ========= PANEL IZQUIERDO =========

        # Frame izquierdo
        panel_izq = QFrame()

        # Ancho mínimo
        panel_izq.setMinimumWidth(300)

        # Layout vertical izquierdo
        izq_layout = QVBoxLayout(panel_izq)
        izq_layout.setContentsMargins(10, 10, 10, 10)
        izq_layout.setSpacing(10)

        # Título
        titulo_pacientes = QLabel("Pacientes registrados")
        titulo_pacientes.setStyleSheet("font-size: 16px; font-weight: 700;")

        # Lista de pacientes
        self.lista = QListWidget()

        # Al cambiar selección, actualiza paciente activo
        self.lista.currentItemChanged.connect(self.seleccionar_paciente_desde_lista)

        # Botón nuevo paciente
        btn_nuevo_paciente = QPushButton("Nuevo paciente")
        btn_nuevo_paciente.clicked.connect(self.nuevo_paciente)

        # Botón descargar
        btn_descargar = QPushButton("Descargar registros")
        btn_descargar.clicked.connect(self.descargar_registros)

        # Mete widgets
        izq_layout.addWidget(titulo_pacientes)
        izq_layout.addWidget(self.lista)
        izq_layout.addWidget(btn_nuevo_paciente)
        izq_layout.addWidget(btn_descargar)

        # ========= PANEL DERECHO =========

        # Contenedor derecho
        panel_der = QWidget()

        # Layout derecho
        der_layout = QVBoxLayout(panel_der)
        der_layout.setContentsMargins(0, 0, 0, 0)
        der_layout.setSpacing(12)

        # Grupo info paciente
        box_info = QGroupBox("Información del paciente")
        box_info_layout = QVBoxLayout(box_info)

        # Etiqueta de detalle de paciente
        self.lbl_paciente_detalle = QLabel("Selecciona un paciente para ver su información.")
        self.lbl_paciente_detalle.setWordWrap(True)
        self.lbl_paciente_detalle.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_paciente_detalle.setStyleSheet("""
            background: #f7f9fc;
            border: 1px solid #d9e0ea;
            border-radius: 10px;
            padding: 12px;
            font-size: 14px;
        """)

        # Agrega etiqueta
        box_info_layout.addWidget(self.lbl_paciente_detalle)

        # Grupo de sesiones
        box_sesiones = QGroupBox("Sesiones del paciente")
        box_sesiones_layout = QVBoxLayout(box_sesiones)

        # Lista de sesiones
        self.lista_sesiones = QListWidget()

        # Al seleccionar una sesión, muestra detalle
        self.lista_sesiones.currentItemChanged.connect(self.mostrar_detalle_sesion)

        # Agrega lista
        box_sesiones_layout.addWidget(self.lista_sesiones)

        # Grupo detalle de sesión
        box_detalle_sesion = QGroupBox("Detalle de sesión")
        box_detalle_layout = QVBoxLayout(box_detalle_sesion)

        # Etiqueta detalle sesión
        self.lbl_detalle_sesion = QLabel("Selecciona una sesión para ver sus detalles.")
        self.lbl_detalle_sesion.setWordWrap(True)
        self.lbl_detalle_sesion.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_detalle_sesion.setStyleSheet("""
            background: #fcfcfc;
            border: 1px solid #e1e5eb;
            border-radius: 10px;
            padding: 12px;
            font-size: 13px;
        """)

        # Agrega detalle
        box_detalle_layout.addWidget(self.lbl_detalle_sesion)

        # Agrega grupos al layout derecho
        der_layout.addWidget(box_info, 3)
        der_layout.addWidget(box_sesiones, 2)
        der_layout.addWidget(box_detalle_sesion, 2)

        # Mete paneles al splitter
        splitter.addWidget(panel_izq)
        splitter.addWidget(panel_der)

        # Tamaños iniciales
        splitter.setSizes([320, 760])

        # Mete splitter al layout principal
        main_layout.addWidget(splitter)

        # Agrega tab
        self.tabs.addTab(tab, "Registro")

    # Abre diálogo para crear paciente nuevo
    def nuevo_paciente(self):
        # Crea diálogo
        dlg = NuevoPacienteDialog(self)

        # Si el usuario acepta
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Obtiene datos
            data = dlg.get_data()

            # Valida nombre y apellido
            if not data["Nombre"] or not data["Apellido"]:
                QMessageBox.warning(self, "Falta info", "Pon al menos Nombre y Apellido.")
                return

            # Genera ID único
            pid = f"P{self.paciente_id_counter:05d}"

            # Incrementa contador
            self.paciente_id_counter += 1

            # Crea estructura del paciente
            paciente = {
                "ID": pid,
                **data,
                "Sesiones": []
            }

            # Lo guarda en la lista principal
            self.pacientes.append(paciente)

            # Crea ítem visible para la lista
            item = QListWidgetItem(f'{pid} - {data["Nombre"]} {data["Apellido"]}')

            # Guarda el ID dentro del ítem
            item.setData(Qt.ItemDataRole.UserRole, pid)

            # Lo agrega a la lista visual
            self.lista.addItem(item)

            # Lo selecciona automáticamente
            self.lista.setCurrentItem(item)

            # Mensaje de éxito
            QMessageBox.information(self, "Listo", f"Paciente guardado con ID: {pid}")

    # Se ejecuta cuando cambia el paciente seleccionado
    def seleccionar_paciente_desde_lista(self, current, previous):
        # Si no hay ítem actual
        if not current:
            self.current_patient_id = None
        else:
            # Guarda el ID del paciente activo
            self.current_patient_id = current.data(Qt.ItemDataRole.UserRole)

        # Actualiza panel derecho
        self.actualizar_panel_paciente()

        # Actualiza pestañas de sensores
        self.actualizar_labels_paciente_en_sensores()

    # Actualiza el panel derecho con datos del paciente
    def actualizar_panel_paciente(self):
        # Obtiene paciente actual
        paciente = self.get_selected_patient()

        # Limpia lista de sesiones
        self.lista_sesiones.clear()

        # Restablece texto detalle sesión
        self.lbl_detalle_sesion.setText("Selecciona una sesión para ver sus detalles.")

        # Si no hay paciente
        if not paciente:
            self.lbl_paciente_detalle.setText("Selecciona un paciente para ver su información.")
            return

        # Obtiene sesiones del paciente
        sesiones = paciente.get("Sesiones", [])

        # Suma total de muestras entre sesiones
        total_muestras = sum(len(s.get("samples", [])) for s in sesiones)

        # Construye texto HTML del paciente
        texto = (
            f"<b>ID:</b> {paciente['ID']}<br>"
            f"<b>Nombre:</b> {paciente['Nombre']} {paciente['Apellido']}<br>"
            f"<b>Fecha de nacimiento:</b> {paciente['Nacimiento']}<br>"
            f"<b>Contacto:</b> {paciente['Contacto']}<br><br>"
            f"<b>Padecimiento:</b><br>{paciente['Padecimiento']}<br><br>"
            f"<b>Sesiones guardadas:</b> {len(sesiones)}<br>"
            f"<b>Total de muestras:</b> {total_muestras}<br>"
        )

        # Si tiene sesiones, muestra resumen de la última
        if sesiones:
            ultima = sesiones[-1]
            texto += (
                f"<br><b>Última sesión:</b> {ultima.get('session_id', '-')}"
                f"<br><b>Estudio:</b> {ultima.get('study_name', '-')}"
                f"<br><b>Sensor:</b> {ultima.get('sensor_tab', '-')}"
                f"<br><b>Fecha:</b> {ultima.get('created_at', '-')}"
                f"<br><b>Muestras en esa sesión:</b> {len(ultima.get('samples', []))}"
            )

        # Muestra el texto en la interfaz
        self.lbl_paciente_detalle.setText(texto)

        # Recorre sesiones y las agrega a la lista visual
        for sesion in sesiones:
            txt = (
                f"{sesion.get('session_id', '-')}"
                f" | {sesion.get('study_name', '-')}"
                f" | {sesion.get('sensor_tab', '-')}"
            )
            item = QListWidgetItem(txt)
            item.setData(Qt.ItemDataRole.UserRole, sesion)
            self.lista_sesiones.addItem(item)

    # Muestra detalles de la sesión seleccionada
    def mostrar_detalle_sesion(self, current, previous):
        # Si no hay sesión seleccionada
        if not current:
            self.lbl_detalle_sesion.setText("Selecciona una sesión para ver sus detalles.")
            return

        # Recupera el diccionario de sesión guardado en el item
        sesion = current.data(Qt.ItemDataRole.UserRole)

        # Si algo salió mal
        if not sesion:
            self.lbl_detalle_sesion.setText("No se encontró información de la sesión.")
            return

        # Obtiene muestras
        samples = sesion.get("samples", [])

        # Número de muestras
        n = len(samples)

        # Si sí tiene muestras
        if n > 0:
            primero = samples[0]
            ultimo = samples[-1]
            duracion = float(ultimo.get("t", 0)) - float(primero.get("t", 0))
        else:
            primero = None
            ultimo = None
            duracion = 0.0

        # Construye texto base
        texto = (
            f"<b>ID de sesión:</b> {sesion.get('session_id', '-')}<br>"
            f"<b>Paciente:</b> {sesion.get('patient_name', '-')}<br>"
            f"<b>Estudio:</b> {sesion.get('study_name', '-')}<br>"
            f"<b>Origen:</b> {sesion.get('sensor_tab', '-')}<br>"
            f"<b>Fecha:</b> {sesion.get('created_at', '-')}<br>"
            f"<b>Muestras:</b> {n}<br>"
            f"<b>Duración aproximada:</b> {duracion:.2f} s<br>"
        )

        # Si hay muestras, agrega primera y última
        if n > 0 and primero and ultimo:
            texto += (
                "<br><b>Primera muestra:</b><br>"
                f"t={primero.get('t', 0):.4f}, "
                f"EMG={primero.get('emg', 0):.4f}, "
                f"Giro={primero.get('gyro', 0):.4f}, "
                f"Acel={primero.get('accel', 0):.4f}<br><br>"

                "<b>Última muestra:</b><br>"
                f"t={ultimo.get('t', 0):.4f}, "
                f"EMG={ultimo.get('emg', 0):.4f}, "
                f"Giro={ultimo.get('gyro', 0):.4f}, "
                f"Acel={ultimo.get('accel', 0):.4f}"
            )

        # Muestra detalle en interfaz
        self.lbl_detalle_sesion.setText(texto)

    # Exporta todos los datos
    def descargar_registros(self):
        # Si no hay pacientes, avisa
        if not self.pacientes:
            QMessageBox.warning(self, "Sin datos", "No hay pacientes registrados.")
            return

        # Pide una carpeta destino
        carpeta = QFileDialog.getExistingDirectory(
            self, "Selecciona una carpeta para exportar"
        )

        # Si cancela, sale
        if not carpeta:
            return

        try:
            # Ruta del JSON general
            ruta_json = os.path.join(carpeta, "registros_pacientes.json")

            # Guarda JSON de todos los pacientes
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(self.pacientes, f, ensure_ascii=False, indent=4)

            # Carpeta para CSVs de sesiones
            sesiones_dir = os.path.join(carpeta, "sesiones_csv")

            # Crea carpeta si no existe
            os.makedirs(sesiones_dir, exist_ok=True)

            # Recorre pacientes
            for paciente in self.pacientes:
                # Recorre sesiones de cada paciente
                for sesion in paciente.get("Sesiones", []):
                    # Obtiene IDs
                    session_id = sesion.get("session_id", "sin_id")
                    patient_id = paciente["ID"]

                    # Nombre del CSV
                    nombre_archivo = f"{patient_id}_{session_id}.csv"

                    # Ruta completa
                    ruta_csv = os.path.join(sesiones_dir, nombre_archivo)

                    # Abre CSV para escritura
                    with open(ruta_csv, "w", newline="", encoding="utf-8") as csvfile:
                        writer = csv.writer(csvfile)

                        # Encabezados
                        writer.writerow([
                            "patient_id", "patient_name", "session_id", "study_name",
                            "sensor_tab", "created_at", "t", "emg", "gyro", "accel"
                        ])

                        # Escribe una fila por muestra
                        for sample in sesion.get("samples", []):
                            writer.writerow([
                                sesion.get("patient_id", ""),
                                sesion.get("patient_name", ""),
                                sesion.get("session_id", ""),
                                sesion.get("study_name", ""),
                                sesion.get("sensor_tab", ""),
                                sesion.get("created_at", ""),
                                sample.get("t", ""),
                                sample.get("emg", ""),
                                sample.get("gyro", ""),
                                sample.get("accel", "")
                            ])

            # Mensaje de éxito
            QMessageBox.information(
                self,
                "Exportación completada",
                "Se exportaron los pacientes y todas las sesiones correctamente."
            )

        except Exception as e:
            # Si algo falla, avisa
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{e}")

    # Crea una pestaña de sensor
    def crear_tab_sensor(self, nombre):
        # Elige fuente según SOURCE_MODE
        if SOURCE_MODE.lower() == "serial":
            source = NRFSerialSource(SERIAL_PORT, SERIAL_BAUD)
        elif SOURCE_MODE.lower() == "ble":
            source = NRFBLESource(BLE_ADDRESS, BLE_CHAR_UUID)
        else:
            source = SimulatedEMGSource()

        # Crea la pestaña
        tab = SensorTab(nombre, source, self)

        # La guarda en lista de tabs sensor
        self.sensor_tabs.append(tab)

        # La agrega a la interfaz
        self.tabs.addTab(tab, nombre)

    # Crea pestaña de visualización de imagen corporal
    def crear_tab_visualizacion(self):
        # Widget del tab
        tab = QWidget()

        # Layout principal horizontal
        layout = QHBoxLayout(tab)

        # Columna izquierda
        left = QVBoxLayout()

        # Label para imagen
        self.lbl_img = QLabel("No hay imagen cargada")
        self.lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_img.setStyleSheet("""
            border: 1px dashed #cccccc;
            border-radius: 10px;
            background: #fafafa;
        """)
        self.lbl_img.setMinimumSize(420, 520)

        # Botón cargar imagen
        btn_cargar = QPushButton("Cargar imagen del cuerpo")
        btn_cargar.clicked.connect(self.cargar_imagen)

        # Agrega a columna izquierda
        left.addWidget(self.lbl_img)
        left.addWidget(btn_cargar)

        # Columna derecha
        right = QVBoxLayout()

        # Título
        titulo = QLabel("Electrodos / Referencias")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")

        # Texto marcador de posición
        right.addWidget(titulo)
        right.addWidget(QLabel("Músculo 1: ---"))
        right.addWidget(QLabel("Músculo 2: ---"))
        right.addWidget(QLabel("Músculo 3: ---"))
        right.addStretch()

        # Agrega columnas al layout principal
        layout.addLayout(left)
        layout.addLayout(right)

        # Agrega tab
        self.tabs.addTab(tab, "Visualización")

    # Abre archivo de imagen y lo muestra
    def cargar_imagen(self):
        # Pide ruta de imagen
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )

        # Si cancela, sale
        if not ruta:
            return

        # Carga pixmap
        pix = QPixmap(ruta)

        # Si falló la carga
        if pix.isNull():
            QMessageBox.warning(self, "Error", "No se pudo cargar la imagen.")
            return

        # Escala la imagen al tamaño del label
        scaled = pix.scaled(
            self.lbl_img.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Muestra la imagen
        self.lbl_img.setPixmap(scaled)

        # Borra texto "No hay imagen cargada"
        self.lbl_img.setText("")

# RUN

