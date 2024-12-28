import asyncio
import psutil
import GPUtil
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer
import qasync

# Настройка базы данных
def setup_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cpu_usage REAL,
            memory_usage REAL,
            gpu_usage TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, commit=False):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO performance (timestamp, cpu_usage, memory_usage, gpu_usage) VALUES (?, ?, ?, ?)",
        (timestamp, cpu_usage, memory_usage, str(gpu_usage)),
    )
    if commit:
        conn.commit()
    conn.close()

async def get_cpu_usage():
    await asyncio.sleep(0.1)
    return psutil.cpu_percent(interval=None)

async def get_memory_usage():
    await asyncio.sleep(0.1)
    memory = psutil.virtual_memory()
    return memory.percent

async def get_gpu_usage():
    await asyncio.sleep(0.1)
    gpus = GPUtil.getGPUs()
    if not gpus:
        return "ГП не найден"
    return [(gpu.name, gpu.load * 100) for gpu in gpus]

async def collect_performance_data(queue, db_name, stop_event):
    setup_database(db_name)
    while not stop_event.is_set():
        cpu_usage = await get_cpu_usage()
        memory_usage = await get_memory_usage()
        gpu_usage = await get_gpu_usage()

        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage,
        }

        await queue.put(data)
        log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, commit=True)
        await asyncio.sleep(1)

class AsyncioLoggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Логгер на основе Asyncio")
        self.setGeometry(100, 100, 300, 200)

        self.queue = asyncio.Queue()
        self.stop_event = asyncio.Event()
        self.db_name = "asyncio_logger.db"
        self.logging_task = None

        self.label_status = QLabel("Логирование: выключено", self)
        self.label_data = QLabel("Данные: Нет данных", self)
        self.button_start_log = QPushButton("Включить лог", self)
        self.button_stop_log = QPushButton("Отключить лог", self)

        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_data)
        layout.addWidget(self.button_start_log)
        layout.addWidget(self.button_stop_log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.button_start_log.clicked.connect(self.start_logging)
        self.button_stop_log.clicked.connect(self.stop_logging)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)

    def start_logging(self):
        if self.logging_task is None or self.logging_task.done():
            self.label_status.setText("Логирование: включено")
            self.stop_event.clear()
            self.logging_task = asyncio.create_task(
                collect_performance_data(self.queue, self.db_name, self.stop_event)
            )
            self.timer.start(1000)

    def stop_logging(self):
        if self.logging_task and not self.logging_task.done():
            self.stop_event.set()
            self.logging_task.cancel()
        self.logging_task = None
        self.label_status.setText("Логирование: выключено")
        self.timer.stop()

    def update_ui(self):
        while not self.queue.empty():
            data = self.queue.get_nowait()
            self.label_data.setText(
                f"Данные: CPU {data['cpu_usage']}%, RAM {data['memory_usage']}%, GPU {data['gpu_usage']}"
            )

if __name__ == "__main__":
    app = QApplication([])
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = AsyncioLoggerApp()
    window.show()

    with loop:
        loop.run_forever()
