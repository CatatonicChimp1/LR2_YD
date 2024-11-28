from gui import main_window

if __name__ == "__main__":
    main_window()

try:
    from gui import main_window
    print("Импорт прошёл успешно")
except ImportError as e:
    print(f"Ошибка импорта: {e}")
