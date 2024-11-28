import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter import filedialog
import os
import json
import shutil
import pandas as pd

selected_file = None

def select_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database files", "*.db")])
    return file_path

def read_db(file_path):
    try:
        with open(file_path, "r") as db_file:
            db_data = json.load(db_file)
            return db_data.get("fields", []), db_data.get("data", []), db_data.get("key_fields", [])
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
        return [], [], []



def write_db(file_path, fields, data, key_fields=None):
    try:
        # Формирование данных для сохранения
        db_data = {"fields": fields, "data": data}
        if key_fields is not None:
            db_data["key_fields"] = key_fields

        # Запись данных в файл
        with open(file_path, "w", encoding="utf-8") as db_file:
            json.dump(db_data, db_file, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось записать в файл: {e}")

def get_key_fields(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
        if "key_fields" not in db or not db["key_fields"]:
            raise ValueError("Ключевые поля не указаны!")
        return db["key_fields"]


def is_unique(file_path, new_record, key_fields):
    with open(file_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
        for record in db["data"]:
            if all(record[field] == new_record[field] for field in key_fields):
                return False  # Дублирование найдено
    return True


# Создание индексов по ключевым полям
def create_indices(data, key_fields):
    indices = {}
    for key_field in key_fields:
        index = {}
        for record in data:
            key = record.get(key_field)
            if key in index:
                index[key].append(record)
            else:
                index[key] = [record]
        indices[key_field] = index
    return indices


# Обновление индексов при добавлении или удалении записей
def update_index(index, record, field_name, operation="add"):
    key = record.get(field_name)
    if operation == "add":
        if key in index:
            index[key].append(record)
        else:
            index[key] = [record]
    elif operation == "remove":
        if key in index and record in index[key]:
            index[key].remove(record)
            if not index[key]:
                del index[key]


def build_index(file_path):
    with open(file_path, 'r+', encoding='utf-8') as f:
        db = json.load(f)
        key_fields = db["key_fields"]

        # Создаем индекс как словарь
        index = {}
        for i, record in enumerate(db["data"]):
            key = tuple(record[field] for field in key_fields)
            if key in index:
                raise ValueError(f"Дублирование ключа: {key}")
            index[key] = i  # Сохраняем индекс строки

        # Сохраняем индекс в файл
        db["index"] = index
        f.seek(0)
        json.dump(db, f, ensure_ascii=False, indent=4)
        f.truncate()

def save_index_to_file(db_file_path, index_file_path):
    with open(db_file_path, 'r', encoding='utf-8') as db_file:
        db = json.load(db_file)
        key_fields = db["key_fields"]

        # Построение индекса
        index = {}
        for i, record in enumerate(db["data"]):
            key = tuple(record[field] for field in key_fields)
            if key in index:
                raise ValueError(f"Дублирование ключа: {key}")
            index[key] = i

    # Сохраняем индекс в отдельный файл
    with open(index_file_path, 'w', encoding='utf-8') as index_file:
        json.dump(index, index_file, ensure_ascii=False, indent=4)


def add_record(file_path, new_record):
    with open(file_path, 'r+', encoding='utf-8') as f:
        db = json.load(f)

        # Проверка уникальности по ключевым полям
        key_fields = db["key_fields"]
        if not is_unique(file_path, new_record, key_fields):
            raise ValueError("Запись с такими ключевыми полями уже существует!")

        # Добавляем запись
        db["data"].append(new_record)

        # Перезаписываем файл
        f.seek(0)
        json.dump(db, f, ensure_ascii=False, indent=4)
        f.truncate()

def delete_record_dialog(selected_file, root):
    # Проверка, что файл выбран
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    # Чтение данных из базы
    fields, data, key_fields = read_db(selected_file)
    if not data:
        messagebox.showerror("Ошибка", "База данных пуста или не может быть прочитана.")
        return

    def delete_record():
        # Получение ключевого значения от пользователя
        key_value = key_entry.get().strip()
        filtered_data = [record for record in data if str(record[key_field]) != key_value]

        if len(filtered_data) == len(data):
            messagebox.showwarning("Не найдено", f"Запись с ключом {key_value} не найдена.")
        else:
            try:
                # Запись изменений в файл
                write_db(selected_file, fields, filtered_data, key_fields)
                messagebox.showinfo("Успех", f"Запись с ключом {key_value} удалена.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить запись: {str(e)}")

    # Создание диалогового окна
    dialog = tk.Toplevel(root)
    dialog.title("Удалить запись")
    dialog.geometry("300x200")

    # Поля ввода
    tk.Label(dialog, text=f"Введите значение ключевого поля ({key_fields[0]}):").pack(pady=10)
    key_field = key_fields[0]  # Используем первое ключевое поле
    key_entry = tk.Entry(dialog)
    key_entry.pack(pady=10)

    # Кнопка удаления
    delete_button = tk.Button(dialog, text="Удалить", command=delete_record)
    delete_button.pack(pady=20)



# Функция удаления записи по значению произвольного поля
def delete_record_by_field():
    global indices  # Для работы с индексами

    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    fields, data, key_fields = read_db(selected_file)

    if not fields:
        messagebox.showerror("Ошибка", "Не удалось загрузить поля из базы данных!")
        return

    # Получаем имя поля для удаления
    field_name = simple_input_dialog("Введите имя поля для удаления записей по значению")
    if not field_name or not any(f['name'] == field_name for f in fields):  # Проверяем, существует ли поле
        messagebox.showerror("Ошибка", f"Поле '{field_name}' не существует в базе данных!")
        return

    field_value = simple_input_dialog(f"Введите значение для поля '{field_name}' для удаления")
    if not field_value:
        return

    # Ищем записи, которые нужно удалить
    records_to_remove = [record for record in data if str(record.get(field_name)) == field_value]

    if not records_to_remove:
        messagebox.showinfo("Результат", "Записи не найдены.")
        return

    # Удаляем найденные записи
    data = [record for record in data if str(record.get(field_name)) != field_value]

    # Обновляем индекс, если поле индексировано
    if field_name in indices:
        for record in records_to_remove:
            update_index(indices[field_name], record, field_name, operation="remove")

    # Записываем изменения в файл
    write_db(selected_file, fields, data, key_fields)
    messagebox.showinfo("Успех", "Записи успешно удалены!")

# Функция создания диалога для ввода данных
def simple_input_dialog(prompt):
    dialog = tk.Toplevel(root)
    dialog.title(prompt)
    dialog.geometry("300x150")

    label = tk.Label(dialog, text=prompt)
    label.pack(pady=10)

    entry = tk.Entry(dialog, width=30)
    entry.pack(pady=10)

    result = None  # Переменная для хранения результата

    def close_dialog():
        nonlocal result
        result = entry.get().strip()  # Получаем значение из поля
        dialog.destroy()

    button = tk.Button(dialog, text="OK", command=close_dialog)
    button.pack(pady=10)

    dialog.wait_window(dialog)  # Ожидаем закрытия окна
    return result

def search_record_dialog():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    fields, data, key_fields = read_db(selected_file)
    if not data:
        messagebox.showerror("Ошибка", "База данных пуста или не может быть прочитана.")
        return

    def perform_search():
        search_field = field_var.get()
        search_value = search_entry.get().strip()

        results = [
            record for record in data if str(record[search_field]) == search_value
        ]

        if results:
            result_text.delete(1.0, tk.END)
            for result in results:
                result_text.insert(tk.END, f"{result}\n")
        else:
            messagebox.showinfo("Результат", "Записи не найдены.")

    dialog = tk.Toplevel(root)
    dialog.title("Поиск записи")
    dialog.geometry("400x300")

    tk.Label(dialog, text="Выберите поле для поиска:").pack(pady=5)
    field_var = tk.StringVar(dialog)
    field_var.set(fields[0]["name"])
    field_menu = tk.OptionMenu(dialog, field_var, *[f["name"] for f in fields])
    field_menu.pack(pady=5)

    tk.Label(dialog, text="Введите значение для поиска:").pack(pady=5)
    search_entry = tk.Entry(dialog)
    search_entry.pack(pady=5)

    search_button = tk.Button(dialog, text="Искать", command=perform_search)
    search_button.pack(pady=10)

    result_text = tk.Text(dialog, width=50, height=10)
    result_text.pack(pady=5)


def search_record_by_field():
    global indices  # Индексы для быстрого доступа

    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    # Читаем данные из файла
    fields, data, key_fields = read_db(selected_file)

    # Проверяем, что есть данные
    if not fields or not data:
        messagebox.showerror("Ошибка", "База данных пуста или не содержит полей.")
        return

    # Выбор поля для поиска
    field_name = simple_input_dialog("Введите имя поля для поиска записей")
    if not field_name or field_name not in [field["name"] for field in fields]:
        messagebox.showerror("Ошибка", f"Поле '{field_name}' отсутствует в базе данных!")
        return

    # Ввод значения для поиска
    field_value = simple_input_dialog(f"Введите значение для поля '{field_name}' для поиска")
    if not field_value:
        return

    # Если поле ключевое, используем индекс
    if field_name in key_fields:
        if field_value.isdigit():
            field_value = int(field_value)  # Приводим к числовому типу, если требуется
        matching_records = indices.get(field_name, {}).get(field_value, [])
    else:
        # Для неключевого поля — полный перебор
        matching_records = [
            record for record in data if str(record.get(field_name)) == str(field_value)
        ]

    # Вывод результата
    if matching_records:
        result_text = "\n".join(str(record) for record in matching_records)
        messagebox.showinfo("Результаты поиска", f"Найдено {len(matching_records)} совпадений:\n{result_text}")
    else:
        messagebox.showinfo("Результаты поиска", "Совпадений не найдено.")


def simple_input_dialog(prompt):
    dialog = tk.Toplevel(root)
    dialog.title(prompt)
    dialog.geometry("300x150")

    label = tk.Label(dialog, text=prompt)
    label.pack(pady=10)

    entry = tk.Entry(dialog, width=30)
    entry.pack(pady=10)

    result = None  # Переменная для хранения результата

    def close_dialog():
        nonlocal result
        result = entry.get().strip()  # Получаем значение из поля
        dialog.destroy()

    button = tk.Button(dialog, text="OK", command=close_dialog)
    button.pack(pady=10)

    dialog.wait_window(dialog)  # Ожидаем закрытия окна
    return result



    def get_input():
        value = entry.get().strip()
        if value:
            close_dialog()
            return value
        return None

    button = tk.Button(dialog, text="OK", command=get_input)
    button.pack(pady=10)

    dialog.wait_window(dialog)
    return get_input()

# Создание backup-файла БД
def create_backup():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    backup_file = selected_file.replace(".json", "-backup.json")
    try:
        shutil.copy(selected_file, backup_file)
        messagebox.showinfo("Успех", f"Резервная копия сохранена как {backup_file}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось создать резервную копию: {e}")


# Восстановление БД из backup-файла
def restore_from_backup():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    backup_file = askopenfilename(filetypes=[("JSON files", "*.json")])
    if not backup_file:
        return

    try:
        shutil.copy(backup_file, selected_file)
        messagebox.showinfo("Успех", "База данных успешно восстановлена!")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось восстановить базу данных: {e}")


def import_from_excel():
    # Выбор Excel-файла
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not file_path:
        messagebox.showwarning("Предупреждение", "Файл не был выбран!")
        return

    # Указание файла для сохранения
    selected_file = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("JSON files", "*.json")])
    if not selected_file:
        messagebox.showwarning("Предупреждение", "Файл для сохранения не был выбран!")
        return

    try:
        # Чтение данных из Excel
        df = pd.read_excel(file_path)

        # Преобразование данных в формат для записи
        fields = [{"name": col, "type": "str"} for col in df.columns]
        data = df.to_dict(orient="records")

        # Сохранение данных
        write_db(selected_file, fields, data)
        messagebox.showinfo("Успех", "Данные успешно импортированы из Excel!")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось импортировать данные: {e}")



def import_from_excel():
    # Выбор Excel-файла
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if not file_path:
        messagebox.showwarning("Предупреждение", "Файл не был выбран!")
        return

    # Указание файла для сохранения
    selected_file = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Database files", "*.json")])
    if not selected_file:
        messagebox.showwarning("Предупреждение", "Файл для сохранения не был выбран!")
        return

    try:
        # Чтение данных из Excel
        df = pd.read_excel(file_path)

        # Преобразование данных в формат для записи
        fields = [{"name": col, "type": "str"} for col in df.columns]
        data = df.to_dict(orient="records")

        # Сохранение данных
        write_db(selected_file, fields, data)
        messagebox.showinfo("Успех", "Данные успешно импортированы из Excel!")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось импортировать данные: {e}")



def create_db():
    def define_fields():
        try:
            nonlocal num_fields
            num_fields = int(entry_num_fields.get().strip())
            if num_fields <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное количество столбцов!")
            return

        # Переходим к этапу задания названий столбцов и типов данных
        request_fields()

    def request_fields():
        create_window.destroy()

        def save_fields():
            nonlocal fields
            for i in range(num_fields):
                name = field_entries[i][0].get().strip()
                data_type = field_entries[i][1].get()
                if not name:
                    messagebox.showerror("Ошибка", "Все поля должны быть заполнены!")
                    return
                if data_type not in ['str', 'int', 'float']:
                    messagebox.showerror("Ошибка", "Неверный тип данных!")
                    return
                fields.append({"name": name, "type": data_type})  # Присваиваем тип, выбранный пользователем
            fields_window.destroy()

            key_field_names = simple_input_dialog("Введите названия ключевых полей (через запятую):")
            if key_field_names:
                key_fields = [key.strip() for key in key_field_names.split(',')]
            else:
                messagebox.showerror("Ошибка", "Не указаны ключевые поля для создания индекса!")
                return

            fields_window.destroy()

            # Создание базы данных
            data = []
            write_db(file_path, fields, data, key_fields)
            messagebox.showinfo("Успех", "База данных создана!")

        fields_window = tk.Toplevel(root)
        fields_window.title("Создание полей базы данных")
        fields_window.geometry("400x400")

        tk.Label(fields_window, text="Введите названия столбцов и выберите типы данных", font=("Arial", 12)).pack(pady=10)

        field_entries = []
        for i in range(num_fields):
            tk.Label(fields_window, text=f"Поле {i + 1}:", font=("Arial", 10)).pack()

            field_name = tk.Entry(fields_window, width=30)
            field_name.pack(pady=5)

            # Создаем комбобокс для выбора типа данных
            data_type = ttk.Combobox(fields_window, values=["str", "int", "float"], width=10)
            data_type.set("str")  # Значение по умолчанию
            data_type.pack(pady=5)

            field_entries.append((field_name, data_type))

        tk.Button(fields_window, text="Сохранить", command=save_fields).pack(pady=20)

    file_path = asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if not file_path:
        return

    # Инициализируем переменные
    fields = []
    num_fields = 0

    create_window = tk.Toplevel(root)
    create_window.title("Создание новой базы данных")
    create_window.geometry("300x200")

    tk.Label(create_window, text="Введите количество столбцов", font=("Arial", 12)).pack(pady=10)
    entry_num_fields = tk.Entry(create_window, width=10)
    entry_num_fields.pack(pady=5)

    tk.Button(create_window, text="Далее", command=define_fields).pack(pady=20)

def add_new_record_dialog():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    fields, data, key_fields = read_db(selected_file)

    if not fields:
        messagebox.showerror("Ошибка", "Не удалось получить поля из базы данных.")
        return

    new_record = {}

    def save_record():
        try:
            for field in fields:
                value = entries[field["name"]].get().strip()
                if field["type"] == "int":
                    value = int(value)
                elif field["type"] == "float":
                    value = float(value)
                new_record[field["name"]] = value

            add_record(selected_file, new_record)
            dialog.destroy()
            messagebox.showinfo("Успех", "Запись успешно добавлена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении записи: {str(e)}")

    dialog = tk.Toplevel(root)
    dialog.title("Добавить запись")
    dialog.geometry("300x400")

    entries = {}
    for field in fields:
        label = tk.Label(dialog, text=f"{field['name']} ({field['type']}):")
        label.pack(pady=5)
        entry = tk.Entry(dialog)
        entry.pack(pady=5)
        entries[field["name"]] = entry

    save_button = tk.Button(dialog, text="Сохранить", command=save_record)
    save_button.pack(pady=20)


def delete_db():
    file_path = askopenfilename(filetypes=[("JSON files", "*.json")])
    if not file_path:
        return

    if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите удалить файл {os.path.basename(file_path)}?"):
        try:
            os.remove(file_path)
            messagebox.showinfo("Успех", "База данных успешно удалена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить файл: {e}")

def edit_record_dialog():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    fields, data, key_fields = read_db(selected_file)
    if not data:
        messagebox.showerror("Ошибка", "База данных пуста или не может быть прочитана.")
        return

    def edit_record():
        # Получение ключевого значения от пользователя
        key_value = key_entry.get().strip()
        key_field = key_fields[0]  # Используем первое ключевое поле для поиска
        record_to_edit = next((record for record in data if str(record[key_field]) == key_value), None)

        if not record_to_edit:
            messagebox.showwarning("Не найдено", f"Запись с ключом {key_value} не найдена.")
            return

        # Открытие окна редактирования
        edit_window = tk.Toplevel(root)
        edit_window.title("Редактирование записи")
        edit_window.geometry("400x400")

        tk.Label(edit_window, text="Измените значения полей", font=("Arial", 12)).pack(pady=10)

        entries = {}
        for field in fields:
            tk.Label(edit_window, text=field["name"], font=("Arial", 10)).pack(pady=5)
            entry = tk.Entry(edit_window, width=30)
            entry.insert(0, str(record_to_edit.get(field["name"], "")))  # Заполняем текущими значениями
            entry.pack(pady=5)
            entries[field["name"]] = entry

        def save_changes():
            for field in fields:
                value = entries[field["name"]].get().strip()
                if field["type"] == "int":
                    value = int(value)
                elif field["type"] == "float":
                    value = float(value)
                record_to_edit[field["name"]] = value

            try:
                write_db(selected_file, fields, data, key_fields)
                messagebox.showinfo("Успех", "Запись успешно изменена!")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изменения: {e}")

        tk.Button(edit_window, text="Сохранить", command=save_changes).pack(pady=20)

    # Окно выбора записи для редактирования
    dialog = tk.Toplevel(root)
    dialog.title("Редактировать запись")
    dialog.geometry("300x200")

    tk.Label(dialog, text=f"Введите значение ключевого поля ({key_fields[0]}):").pack(pady=10)
    key_entry = tk.Entry(dialog)
    key_entry.pack(pady=10)

    edit_button = tk.Button(dialog, text="Редактировать", command=edit_record)
    edit_button.pack(pady=20)

def clear_database():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите очистить базу данных?"):
        fields, _, key_fields = read_db(selected_file)
        try:
            write_db(selected_file, fields, [], key_fields)
            messagebox.showinfo("Успех", "База данных успешно очищена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить базу данных: {e}")


def open_db_window():
    global selected_file, indices
    selected_file = askopenfilename(filetypes=[("JSON files", "*.json")])
    if not selected_file:
        return

    fields, data, key_fields = read_db(selected_file)

    if key_fields:
        indices = create_indices(data, key_fields)  # Создаем индексы
    else:
        indices = {}  # Если ключевые поля не заданы, индексы отсутствуют

    display_db_window()



def display_db_window():
    if not selected_file:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных!")
        return

    fields, data, key_fields = read_db(selected_file)  # Исправлено: распаковываем три значения

    if not data:
        messagebox.showinfo("Нет данных", "В базе данных нет записей.")
        return

    db_window = tk.Toplevel(root)
    db_window.title("Просмотр данных базы")
    db_window.geometry("600x400")

    treeview = ttk.Treeview(db_window, columns=[field["name"] for field in fields], show="headings")
    for field in fields:
        treeview.heading(field["name"], text=field["name"])
        treeview.column(field["name"], width=100)

    for record in data:
        treeview.insert("", "end", values=[record.get(field["name"], "") for field in fields])

    treeview.pack(fill="both", expand=True)



root = tk.Tk()
root.title("Менеджер базы данных")
root.geometry("300x400")

selected_file = None

menu = tk.Menu(root)
root.config(menu=menu)

db_menu = tk.Menu(menu, tearoff=0)
menu.add_cascade(label="База данных", menu=db_menu)
db_menu.add_command(label="Создать", command=create_db)
db_menu.add_command(label="Открыть", command=open_db_window)
db_menu.add_command(label="Добавить запись", command=add_new_record_dialog)
db_menu.add_command(label="Удалить", command=delete_db)

tools_menu = tk.Menu(menu, tearoff=0)
menu.add_cascade(label="Инструменты", menu=tools_menu)
tools_menu.add_command(label="Импорт из Excel", command=import_from_excel)
tools_menu.add_command(label="Удалить запись по ключу", command=lambda: delete_record_dialog(selected_file, root))
tools_menu.add_command(label="Удалить запись по полю", command=delete_record_by_field)
tools_menu.add_command(label="Поиск по полю", command=search_record_dialog)
tools_menu.add_command(label="Создать резервную копию", command=create_backup)
tools_menu.add_command(label="Восстановить из резерва", command=restore_from_backup)
tools_menu.add_command(label="Редактировать запись", command=edit_record_dialog)
tools_menu.add_command(label="Очистить базу данных", command=clear_database)

root.mainloop()