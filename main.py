import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
import plotly.graph_objs as go
import plotly.io as pio

# Создаём Flask-приложение
app = Flask(__name__)

# Устанавливаем секретный ключ для использования flash-сообщений (для уведомлений на странице)
# app.secret_key = "your_secret_key"

# Папка для загрузки файлов
UPLOAD_FOLDER = "uploads"

# Конфигурация папки для загрузки файлов
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Разрешённые расширения файлов, которые можно загружать
ALLOWED_EXTENSIONS = {"db"}

# Если папка для загрузок не существует, создаём её
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    """
    Проверяет, имеет ли файл допустимое расширение.
    Возвращает True, если расширение файла содержится в списке ALLOWED_EXTENSIONS.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def upload_file():
    """
    Обрабатывает загрузку файлов через веб-форму.
    Если файл загружен корректно, сохраняет его и перенаправляет на страницу просмотра данных.
    """
    if request.method == "POST":
        # Проверяем, есть ли файл в запросе
        if "file" not in request.files:
            flash("Файл не найден в запросе")  # Выводим сообщение об ошибке
            return redirect(request.url)

        file = request.files["file"]

        # Проверяем, выбран ли файл
        if file.filename == "":
            flash("Файл не выбран")  # Выводим сообщение об ошибке
            return redirect(request.url)

        # Проверяем расширение файла и сохраняем его
        if file and allowed_file(file.filename):
            # Защищаем имя файла от потенциальных уязвимостей
            filename = secure_filename(file.filename)
            # Формируем полный путь к файлу
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            # Сохраняем файл в папку UPLOAD_FOLDER
            file.save(file_path)
            # Перенаправляем на страницу просмотра данных из файла
            return redirect(url_for("view_data", filename=filename))

    # Если метод GET, отображаем форму загрузки файла
    return render_template("upload.html")


@app.route("/view/<filename>")
def view_data(filename):
    """
    Загружает данные из выбранного файла базы данных (.db),
    извлекает таблицу "data" и отображает её содержимое на веб-странице вместе с графиками.
    """
    # Формируем полный путь к загруженному файлу
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    # Проверяем, существует ли файл
    if not os.path.exists(file_path):
        flash("Файл не найден")  # Выводим сообщение об ошибке
        return redirect(url_for("upload_file"))

    try:
        # Подключаемся к базе данных SQLite
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        # Выполняем SQL-запрос для получения всех данных из таблицы "data"
        cursor.execute("SELECT * FROM performance")
        rows = cursor.fetchall()  # Получаем все строки результата
        column_names = [description[0] for description in cursor.description]  # Названия столбцов таблицы
        conn.close()  # Закрываем соединение с базой данных

        # Извлекаем данные для построения графиков
        timestamps = [row[0] for row in rows]  # Столбец с временными метками
        cpu_usage = [row[1] for row in rows]  # Столбец с загрузкой CPU
        memory_usage = [row[2] for row in rows]  # Столбец с загрузкой памяти
        gpu_usage = [row[3] for row in rows]  # Столбец с загрузкой GPU

        # Создаём интерактивные графики с использованием Plotly
        graphs = {
            "cpu": create_graph(timestamps, cpu_usage, "Загрузка CPU (%)", "Время", "Загрузка (%)"),
            "memory": create_graph(timestamps, memory_usage, "Загрузка памяти (%)", "Время", "Загрузка (%)"),
            "gpu": create_graph(timestamps, gpu_usage, "Загрузка GPU (%)", "Время", "Загрузка (%)"),
        }

        # Формируем данные для передачи в шаблон
        data = {"columns": column_names, "rows": rows, "graphs": graphs}
    except Exception as e:
        # В случае ошибки (например, если структура файла некорректна) выводим сообщение
        flash(f"Ошибка при чтении базы данных: {e}")
        return redirect(url_for("upload_file"))

    # Отображаем страницу с таблицей и графиками
    return render_template("view.html", data=data)


def create_graph(x, y, title, x_label, y_label):
    """
    Создаёт интерактивный график с использованием библиотеки Plotly.

    Параметры:
    - x: значения по оси X (например, временные метки).
    - y: значения по оси Y (например, данные о загрузке).
    - title: заголовок графика.
    - x_label: подпись оси X.
    - y_label: подпись оси Y.

    Возвращает HTML-код графика.
    """
    # Создаём объект Figure
    fig = go.Figure()

    # Добавляем данные в виде линии
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=title))

    # Настраиваем оформление графика
    fig.update_layout(
        title=title,  # Заголовок графика
        xaxis_title=x_label,  # Подпись оси X
        yaxis_title=y_label,  # Подпись оси Y
        template="plotly_dark",  # Тёмная тема оформления
    )

    # Преобразуем график в HTML-код
    return pio.to_html(fig, full_html=False)


# Запуск приложения
if __name__ == "__main__":
    app.run(debug=True)
