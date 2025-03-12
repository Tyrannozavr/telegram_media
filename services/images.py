from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

def render(image_file: bytes, text: str, font_size: int) -> bytes:
    """
    Создает изображение с текстом, размещенным внизу слева, и белой полосой.

    :param image_file: Байты загруженного изображения.
    :param text: Текст для наложения.
    :param font_size: Размер шрифта.
    :return: Байты результирующего изображения.
    """
    # Загружаем изображение из байтов
    image = Image.open(BytesIO(image_file))

    # Создаем объект для рисования на изображении
    draw = ImageDraw.Draw(image)

    # Загружаем шрифт (убедитесь, что шрифт доступен в системе)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        # Если шрифт не найден, используем стандартный
        font = ImageFont.load_default()

    # Разбиваем текст на строки, если он содержит переносы
    lines = text.split("\n")

    # Вычисляем размеры текста
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total_text_height = sum(line_heights) + (len(lines) - 1) * 5  # 5px между строками
    max_text_width = max(draw.textbbox((0, 0), line, font=font)[2] for line in lines)

    # Определяем позицию текста
    padding = 10  # Отступ от краев
    text_x = padding + 10  # 10px для белой полосы + 10px отступ
    text_y = image.height - total_text_height - padding  # Размещаем текст внизу

    # Рисуем белую полосу
    stripe_x1 = padding
    stripe_x2 = padding + 10  # Ширина полосы 10px
    stripe_y1 = text_y
    stripe_y2 = image.height - padding
    draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill="white")

    # Добавляем текст на изображение
    for line in lines:
        draw.text((text_x, text_y), line, font=font, fill="black")  # fill - цвет текста
        text_y += line_heights[lines.index(line)] + 5  # Переход на следующую строку

    # Сохраняем результат в байты
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output.getvalue()