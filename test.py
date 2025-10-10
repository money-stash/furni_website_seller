import re


def convert_html_paths(html_content):
    """
    Анализирует HTML и конвертирует пути в атрибутах href и src
    для WordPress ресурсов в Flask url_for синтаксис
    """
    # Ключевые слова для поиска
    keywords = ["wp-content", "wp-includes", "wp-json", "imgs", "css"]

    def replace_path(match):
        """Функция замены для регулярного выражения"""
        attr_name = match.group(1)  # href или src
        quote = match.group(2)  # ' или "
        path = match.group(3)  # путь к файлу

        # Проверяем, содержит ли путь одно из ключевых слов
        if any(keyword in path for keyword in keywords):
            # Пропускаем абсолютные URL (http://, https://, //)
            if re.match(r"^(https?:)?//", path):
                return match.group(0)  # Возвращаем без изменений

            # Удаляем начальный слеш если есть
            clean_path = path.lstrip("/")

            # Создаем новое значение с Flask url_for
            new_value = (
                f"{attr_name}=\"{{{{url_for('static', filename='{clean_path}')}}}}\""
            )

            print(f"Заменено: {attr_name}={quote}{path}{quote} -> {new_value}")
            return new_value

        # Если ключевое слово не найдено, возвращаем без изменений
        return match.group(0)

    # Паттерн для поиска href="..." или src="..." (с одинарными и двойными кавычками)
    pattern = r'(href|src)\s*=\s*(["\'])([^"\']*?)\2'

    # Заменяем все совпадения
    converted_html = re.sub(pattern, replace_path, html_content)

    return converted_html


def convert_html_file(input_file, output_file):
    """
    Читает HTML из файла, конвертирует пути и сохраняет результат
    """
    try:
        # Читаем входной файл
        with open(input_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        print(f"Обработка файла: {input_file}")
        print("-" * 50)

        # Конвертируем пути
        converted_html = convert_html_paths(html_content)

        # Сохраняем результат
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(converted_html)

        print("-" * 50)
        print(f"Результат сохранен в: {output_file}")

    except FileNotFoundError:
        print(f"Ошибка: Файл {input_file} не найден")
    except Exception as e:
        print(f"Ошибка при обработке: {str(e)}")


# Пример использования
if __name__ == "__main__":
    # # Пример 1: Обработка строки HTML
    # html_example = """
    # <link rel='stylesheet' id='wp_head_style6-css' href='wp-content/themes/simplexxagency/build/css/bootstrap.css' type='text/css' media='all' />
    # <script src='/wp-includes/js/jquery.min.js'></script>
    # <img src="imgs/logo.png" alt="Logo">
    # <link href="css/style.css" rel="stylesheet">
    # <a href="https://example.com/page">External Link</a>
    # """

    # print("Пример обработки HTML строки:")
    # print("=" * 50)
    # converted = convert_html_paths(html_example)
    # print("\nРезультат:")
    # print(converted)

    # print("\n" + "=" * 50)
    # print("\nПример обработки файла:")
    # print("=" * 50)

    # Пример 2: Обработка файла
    # Раскомментируйте и укажите свои файлы:
    convert_html_file("templates/index.html", "output.html")
