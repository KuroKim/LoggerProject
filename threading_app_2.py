import threading
import psutil
import GPUtil
import sqlite3
from datetime import datetime
from queue import Queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer


# Настройка базы данных
# Создаёт таблицу для хранения метрик производительности, если её ещё нет
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

# Добавляет данные о производительности в базу данных SQLite
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


# Функция для сбора данных о производительности
# Считывает загрузку ЦП, ОЗУ и GPU и сохраняет их в очередь и базу данных
def collect_performance_data(queue, db_name, stop_event):
    setup_database(db_name)
    while not stop_event.is_set():
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        gpus = GPUtil.getGPUs()
        gpu_usage = [(gpu.name, gpu.load * 100) for gpu in gpus] if gpus else "ГП не найден"

        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage,
        }

        # Добавление данных в очередь
        queue.put(data)

        # Запись в базу данных
        log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, commit=True)


# Основное приложение
# Класс приложения с графическим интерфейсом для управления логированием
class ThreadingLoggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Логгер на основе Threading")
        self.setGeometry(100, 100, 300, 200)

        self.queue = Queue()
        self.logging_thread = None
        self.stop_event = threading.Event()
        self.db_name = "threading_logger.db"

        # Элементы интерфейса
        self.label_status = QLabel("Логирование: выключено", self)
        self.label_data = QLabel("Данные: Нет данных", self)
        self.button_start_log = QPushButton("Включить лог", self)
        self.button_stop_log = QPushButton("Отключить лог", self)

        # Макет
        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_data)
        layout.addWidget(self.button_start_log)
        layout.addWidget(self.button_stop_log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Привязка кнопок
        self.button_start_log.clicked.connect(self.start_logging)
        self.button_stop_log.clicked.connect(self.stop_logging)

        # Таймер для обновления интерфейса
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)

    # Запускает поток логирования и обновляет статус интерфейса
    def start_logging(self):
        if self.logging_thread is None or not self.logging_thread.is_alive():
            self.label_status.setText("Логирование: включено")
            self.stop_event.clear()
            self.logging_thread = threading.Thread(
                target=collect_performance_data, args=(self.queue, self.db_name, self.stop_event)
            )
            self.logging_thread.start()
            self.timer.start(1000)  # Обновление интерфейса каждую секунду

    # Останавливает поток логирования и обновляет статус интерфейса
    def stop_logging(self):
        if self.logging_thread and self.logging_thread.is_alive():
            self.stop_event.set()
            self.logging_thread.join()
        self.logging_thread = None
        self.label_status.setText("Логирование: выключено")
        self.timer.stop()

    # Обновляет данные на пользовательском интерфейсе, получая их из очереди
    def update_ui(self):
        while not self.queue.empty():
            data = self.queue.get()
            self.label_data.setText(
                f"Данные: CPU {data['cpu_usage']}%, RAM {data['memory_usage']}%, GPU {data['gpu_usage']}"
            )


# Основной блок
# Запускает приложение
if __name__ == "__main__":
    app = QApplication([])
    window = ThreadingLoggerApp()
    window.show()
    app.exec_()
import threading
import psutil
import GPUtil
import sqlite3
from datetime import datetime
from queue import Queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer


# Настройка базы данных
# Создаёт таблицу для хранения метрик производительности, если её ещё нет
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

# Добавляет данные о производительности в базу данных SQLite
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


# Функция для сбора данных о производительности
# Считывает загрузку ЦП, ОЗУ и GPU и сохраняет их в очередь и базу данных
def collect_performance_data(queue, db_name, stop_event):
    setup_database(db_name)
    while not stop_event.is_set():
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        gpus = GPUtil.getGPUs()
        gpu_usage = [(gpu.name, gpu.load * 100) for gpu in gpus] if gpus else "ГП не найден"

        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage,
        }

        # Добавление данных в очередь
        queue.put(data)

        # Запись в базу данных
        log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, commit=True)


# Основное приложение
# Класс приложения с графическим интерфейсом для управления логированием
class ThreadingLoggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Логгер на основе Threading")
        self.setGeometry(100, 100, 300, 200)

        self.queue = Queue()
        self.logging_thread = None
        self.stop_event = threading.Event()
        self.db_name = "threading_logger.db"

        # Элементы интерфейса
        self.label_status = QLabel("Логирование: выключено", self)
        self.label_data = QLabel("Данные: Нет данных", self)
        self.button_start_log = QPushButton("Включить лог", self)
        self.button_stop_log = QPushButton("Отключить лог", self)

        # Макет
        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_data)
        layout.addWidget(self.button_start_log)
        layout.addWidget(self.button_stop_log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Привязка кнопок
        self.button_start_log.clicked.connect(self.start_logging)
        self.button_stop_log.clicked.connect(self.stop_logging)

        # Таймер для обновления интерфейса
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)

    # Запускает поток логирования и обновляет статус интерфейса
    def start_logging(self):
        if self.logging_thread is None or not self.logging_thread.is_alive():
            self.label_status.setText("Логирование: включено")
            self.stop_event.clear()
            self.logging_thread = threading.Thread(
                target=collect_performance_data, args=(self.queue, self.db_name, self.stop_event)
            )
            self.logging_thread.start()
            self.timer.start(1000)  # Обновление интерфейса каждую секунду

    # Останавливает поток логирования и обновляет статус интерфейса
    def stop_logging(self):
        if self.logging_thread and self.logging_thread.is_alive():
            self.stop_event.set()
            self.logging_thread.join()
        self.logging_thread = None
        self.label_status.setText("Логирование: выключено")
        self.timer.stop()

    # Обновляет данные на пользовательском интерфейсе, получая их из очереди
    def update_ui(self):
        while not self.queue.empty():
            data = self.queue.get()
            self.label_data.setText(
                f"Данные: CPU {data['cpu_usage']}%, RAM {data['memory_usage']}%, GPU {data['gpu_usage']}"
            )


# Основной блок
# Запускает приложение
if __name__ == "__main__":
    app = QApplication([])
    window = ThreadingLoggerApp()
    window.show()
    app.exec_()