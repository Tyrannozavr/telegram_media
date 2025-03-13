def wrap_text(text: str, width: int = 32) -> str:
    """
    Ограничивает текст по ширине, добавляя переносы строк.
    Старается не разбивать слова, но если это необходимо, добавляет символ переноса "-".

    :param text: Входной текст.
    :param width: Максимальная ширина строки (по умолчанию 32 символа).
    :return: Текст с переносами строк.
    """

    words = text.split(' ')  # Разбиваем текст на слова
    wrapped_text = []  # Список для хранения строк
    current_line = ''  # Текущая строка

    for word in words:
        # Если добавление слова не превышает лимит
        if len(current_line) + len(word) <= width:
            current_line += word + ' '
        else:
            # Если слово слишком длинное и не помещается в строку
            if len(word) > width:
                # Разбиваем слово на части
                while len(word) > width:
                    # Добавляем часть слова и символ переноса
                    wrapped_text.append(current_line + word[:width - 1] + '-')
                    word = word[width - 1:]  # Оставшаяся часть слова
                    current_line = ''
                current_line = word + ' '
            else:
                # Если слово не помещается, завершаем текущую строку и начинаем новую
                wrapped_text.append(current_line.rstrip())
                current_line = word + ' '

    # Добавляем последнюю строку
    if current_line:
        wrapped_text.append(current_line.rstrip())

    return '\n'.join(wrapped_text)


from PIL import ImageFont, ImageDraw

def calculate_characters_width(font_size: int, reference_font_size: int = 100, reference_width: int = 28) -> int:
    """
    Рассчитывает количество символов, которые поместятся в строку, на основе размера шрифта.

    :param font_size: Размер шрифта, для которого нужно рассчитать количество символов.
    :param reference_font_size: Эталонный размер шрифта (по умолчанию 100).
    :param reference_width: Количество символов при эталонном размере шрифта (по умолчанию 32).
    :return: Количество символов, которые поместятся в строку.
    """
    # Используем пропорцию для расчета
    # Ширина текста пропорциональна размеру шрифта
    # reference_width / reference_font_size = new_width / font_size
    new_width = (reference_width * font_size) / reference_font_size
    return int(new_width)


# Пример использования
# font_size = 150  # Новый размер шрифта
# characters_width = calculate_characters_width(font_size)
# print(f"Количество символов при font_size={font_size}: {characters_width}")

# Пример использования
# input_text = (
#     "Это пример текста, который нужно ограничить по ширине в 32 символа. "
#     "Он содержит длинные слова, такие как 'саморазвитие' и 'высокотехнологичный', "
#     "а также короткие слова."
# )

# wrapped_text = wrap_text(input_text)
# print(wrapped_text)