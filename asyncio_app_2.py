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


async def get_cpu_usage():
    """
    Получает процент загрузки процессора.

    Возвращает:
        float: Загрузка процессора в процентах.
    """
    await asyncio.sleep(0.1)
    return psutil.cpu_percent(interval=None)


async def get_memory_usage():
    """
    Получает процент использования оперативной памяти.

    Возвращает:
        float: Использование памяти в процентах.
    """
    await asyncio.sleep(0.1)
    memory = psutil.virtual_memory()
    return memory.percent


async def get_gpu_usage():
    """
    Получает информацию о загрузке GPU.

    Возвращает:
        str: Список с названиями GPU и их загрузкой в процентах,
             либо сообщение "ГП не найден", если GPU отсутствует.
    """
    await asyncio.sleep(0.1)
    gpus = GPUtil.getGPUs()
    if not gpus:
        return "ГП не найден"
    return [(gpu.name, gpu.load * 100) for gpu in gpus]


async def collect_performance_data(queue, db_name, stop_event):
    """
    Собирает данные о производительности (CPU, RAM, GPU) и записывает их в базу данных.

    Аргументы:
        queue (asyncio.Queue): Очередь для передачи данных в интерфейс.
        db_name (str): Имя файла базы данных SQLite.
        stop_event (asyncio.Event): Событие для остановки сбора данных.
    """
    setup_database(db_name)
    while not stop_event.is_set():
        start_time = datetime.now()  # Начало измерения времени

        cpu_usage = await get_cpu_usage()
        memory_usage = await get_memory_usage()
        gpu_usage = await get_gpu_usage()

        end_time = datetime.now()  # Конец измерения времени
        elapsed_time = (end_time - start_time).total_seconds()  # Время выполнения одного цикла

        data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "gpu_usage": gpu_usage,
            "cycle_time": elapsed_time,
        }

        await queue.put(data)
        log_to_database(db_name, cpu_usage, memory_usage, gpu_usage, elapsed_time, commit=True)

        print(f"Время выполнения цикла: {elapsed_time:.4f} секунд")

        await asyncio.sleep(1)


class AsyncioLoggerApp(QMainWindow):
    """
    Графический интерфейс для логгера данных о производительности, использующего Asyncio.

    Атрибуты:
        queue (asyncio.Queue): Очередь для передачи данных между сборщиком и интерфейсом.
        stop_event (asyncio.Event): Событие для остановки сбора данных.
        db_name (str): Имя файла базы данных SQLite.
        logging_task (asyncio.Task): Асинхронная задача для сбора данных.
        label_status (QLabel): Метка для отображения состояния логгера.
        label_data (QLabel): Метка для отображения последних собранных данных.
        button_start_log (QPushButton): Кнопка для запуска логгирования.
        button_stop_log (QPushButton): Кнопка для остановки логгирования.
        timer (QTimer): Таймер для регулярного обновления интерфейса.
    """

    def __init__(self):
        """
        Инициализирует интерфейс приложения, задает основные компоненты и их связь.
        """
        super().__init__()
        self.setWindowTitle("Логгер на основе Asyncio")
        self.setGeometry(100, 100, 300, 200)

        self.queue = asyncio.Queue()
        self.stop_event = asyncio.Event()
        self.db_name = "asyncio_logger.db"
        self.logging_task = None

        # Создание элементов интерфейса
        self.label_status = QLabel("Логирование: выключено", self)
        self.label_data = QLabel("Данные: Нет данных", self)
        self.button_start_log = QPushButton("Включить лог", self)
        self.button_stop_log = QPushButton("Отключить лог", self)

        # Создание компоновки интерфейса
        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_data)
        layout.addWidget(self.button_start_log)
        layout.addWidget(self.button_stop_log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Подключение сигналов к обработчикам
        self.button_start_log.clicked.connect(self.start_logging)
        self.button_stop_log.clicked.connect(self.stop_logging)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)

    def start_logging(self):
        """
        Запускает асинхронную задачу сбора данных и обновляет состояние интерфейса.
        """
        if self.logging_task is None or self.logging_task.done():
            self.label_status.setText("Логирование: включено")
            self.stop_event.clear()
            self.logging_task = asyncio.create_task(
                collect_performance_data(self.queue, self.db_name, self.stop_event)
            )
            self.timer.start(1000)

    def stop_logging(self):
        """
        Останавливает асинхронную задачу сбора данных и обновляет состояние интерфейса.
        """
        if self.logging_task and not self.logging_task.done():
            self.stop_event.set()
            self.logging_task.cancel()
        self.logging_task = None
        self.label_status.setText("Логирование: выключено")
        self.timer.stop()

    def update_ui(self):
        """
        Обновляет отображение данных в интерфейсе из очереди данных.
        """
        while not self.queue.empty():
            data = self.queue.get_nowait()
            self.label_data.setText(
                f"Данные: CPU {data['cpu_usage']}%, RAM {data['memory_usage']}%, GPU {data['gpu_usage']}"
            )


if __name__ == "__main__":
    """
    Точка входа в программу. Инициализирует приложение, запускает цикл событий и отображает интерфейс.
    """
    # Создание экземпляра приложения PyQt5
    app = QApplication([])

    # Установка события цикла обработки для работы с асинхронным кодом через qasync
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Создание основного окна приложения
    window = AsyncioLoggerApp()
    window.show()

    # Запуск цикла обработки событий
    with loop:
        loop.run_forever()
