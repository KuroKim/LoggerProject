import multiprocessing
import psutil
import GPUtil
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import QTimer


# Настройка базы данных
# Создаёт таблицу для хранения метрик производительности, если её ещё нет
def setup_database(db_name):
    """
    Создает таблицу для хранения данных о производительности, если она еще не существует.

    Аргументы:
        db_name (str): Имя файла базы данных SQLite.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cpu_usage REAL,
            memory_usage REAL,
            gpu_usage TEXT,
            elapsed_time REAL
        )
        """
    )
    conn.commit()
    conn.close()


# Добавляет данные о производительности в базу данных SQLite
def log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, elapsed_time, commit=False):
    """
    Записывает данные о производительности в базу данных.

    Аргументы:
        db_name (str): Имя файла базы данных SQLite.
        cpu_usage (float): Загрузка процессора в процентах.
        memory_usage (float): Использование оперативной памяти в процентах.
        gpu_usage (str): Информация о загрузке GPU.
        elapsed_time (float): Время выполнения цикла в секундах.
        commit (bool): Указывает, следует ли зафиксировать изменения в базе данных.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO performance (timestamp, cpu_usage, memory_usage, gpu_usage, elapsed_time) VALUES (?, ?, ?, ?, ?)",
        (timestamp, cpu_usage, memory_usage, str(gpu_usage), elapsed_time),
    )
    if commit:
        conn.commit()
    conn.close()


# Функция для сбора данных о производительности
# Считывает загрузку ЦП, ОЗУ и GPU и сохраняет их в очередь и базу данных
def collect_performance_data(queue, db_name):
    """
    Функция для сбора данных о производительности.
    Считывает загрузку ЦП, ОЗУ и GPU и сохраняет их в очередь и базу данных.

    Аргументы:
    queue (multiprocessing.Queue): Очередь для хранения данных о производительности.
    db_name (str): Имя файла базы данных SQLite.

    Возвращаемое значение:
    None.

    Примечание:
    Функция запускается в отдельном процессе и бесконечно считывает данные о производительности,
    добавляя их в очередь и записывая в базу данных.
    """
    setup_database(db_name)
    while True:
        start_time = datetime.now()  # Начало измерения времени

        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        gpus = GPUtil.getGPUs()
        gpu_usage = [(gpu.name, gpu.load * 100) for gpu in gpus] if gpus else "ГП не найден"

        end_time = datetime.now()  # Конец измерения времени
        elapsed_time = (end_time - start_time).total_seconds()  # Время выполнения одного цикла

        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage,
            "cycle_time": elapsed_time,
        }

        # Добавление данных в очередь
        queue.put(data)

        # Запись в базу данных
        log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, elapsed_time, commit=True)

        print(f"Время выполнения цикла: {elapsed_time:.4f} секунд")


# Основное приложение
# Класс приложения с графическим интерфейсом для управления логированием
class MultiprocessingLoggerApp(QMainWindow):
    """
    Класс приложения с графическим интерфейсом для управления логированием на основе Multiprocessing.
    """

    def __init__(self):
        """
        Конструктор класса, инициализирующий окно приложения и его элементы.

        Args:
        self: Объект класса MultiprocessingLoggerApp.

        Returns:
        None.
        """
        super().__init__()
        self.setWindowTitle("Логгер на основе Multiprocessing")
        self.setGeometry(100, 100, 300, 200)

        self.queue = multiprocessing.Queue()
        self.logging_process = None
        self.db_name = "multiprocessing_logger.db"

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

    # Запускает процесс логирования и обновляет статус интерфейса
    def start_logging(self):
        """
        Метод для запуска процесса логирования и обновления статуса интерфейса.

        Args:
        self: Объект класса MultiprocessingLoggerApp.

        Returns:
        None.
        """
        if self.logging_process is None or not self.logging_process.is_alive():
            self.label_status.setText("Логирование: включено")
            self.logging_process = multiprocessing.Process(
                target=collect_performance_data, args=(self.queue, self.db_name)
            )
            self.logging_process.start()
            self.timer.start(1000)  # Обновление интерфейса каждую секунду

    # Останавливает процесс логирования и обновляет статус интерфейса
    def stop_logging(self):
        """
        Метод для остановки процесса логирования и обновления статуса интерфейса.

        Args:
        self: Объект класса MultiprocessingLoggerApp.

        Returns:
        None.
        """
        if self.logging_process and self.logging_process.is_alive():
            self.logging_process.terminate()
            self.logging_process.join()
        self.logging_process = None
        self.label_status.setText("Логирование: выключено")
        self.timer.stop()

    # Обновляет данные на пользовательском интерфейсе, получая их из очереди
    def update_ui(self):
        """
        Метод для обновления данных на пользовательском интерфейсе, получая их из очереди.

        Args:
        self: Объект класса MultiprocessingLoggerApp.

        Returns:
        None.
        """
        while not self.queue.empty():
            data = self.queue.get()
            self.label_data.setText(
                f"Данные: CPU {data['cpu_usage']}%, RAM {data['memory_usage']}%, GPU {data['gpu_usage']}"
            )


# Основной блок
# Запускает приложение и обеспечивает совместимость с Windows через freeze_support
if __name__ == "__main__":
    multiprocessing.freeze_support()  # Для совместимости с Windows

    app = QApplication([])
    window = MultiprocessingLoggerApp()
    window.show()
    app.exec_()
