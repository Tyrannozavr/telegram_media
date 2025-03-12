import io
from io import BytesIO

from PIL import Image, ImageFilter, ImageEnhance
from PIL import ImageDraw, ImageFont


def process_image(image_file: bytes) -> Image.Image:
    # Открываем изображение из байтов
    image = Image.open(io.BytesIO(image_file))

    # Определяем желаемый размер
    target_width, target_height = 2000, 2500

    # Определяем соотношение сторон исходного изображения
    width, height = image.size
    aspect_ratio = width / height

    # Если ширина недостаточна, растягиваем изображение по ширине
    if width < target_width:
        # Масштабируем изображение до ширины 2000
        new_width = target_width
        new_height = int(new_width / aspect_ratio)
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        # Если ширина достаточна, масштабируем по высоте
        new_height = target_height
        new_width = int(new_height * aspect_ratio)
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Если высота недостаточна, добавляем зеркальное отражение, размытие и затемнение
    if resized_image.height < target_height:
        # Создаем новое изображение с высотой 2500
        final_image = Image.new('RGB', (resized_image.width, target_height), (0, 0, 0))
        final_image.paste(resized_image, (0, 0))

        # Зеркально отражаем изображение вниз
        mirrored_image = resized_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        # Размываем зеркальную часть
        blurred_mirrored = mirrored_image.filter(ImageFilter.GaussianBlur(20))

        # Затемняем зеркальную часть
        enhancer = ImageEnhance.Brightness(blurred_mirrored)
        darkened_mirrored = enhancer.enhance(0.5)  # Уменьшаем яркость на 50%

        # Вставляем затемнённую и размытую зеркальную часть
        final_image.paste(darkened_mirrored, (0, resized_image.height))
    else:
        final_image = resized_image

    # Если ширина или высота превышают целевые, обрезаем изображение
    if final_image.width > target_width or final_image.height > target_height:
        left = (final_image.width - target_width) / 2
        top = (final_image.height - target_height) / 2
        right = (final_image.width + target_width) / 2
        bottom = (final_image.height + target_height) / 2
        final_image = final_image.crop((left, top, right, bottom))

    return final_image


# Преобразуем изображение в байты
def image_to_bytes(image: Image.Image, format: str = 'JPEG') -> bytes:
    img_byte_arr = io.BytesIO()  # Создаем байтовый поток
    image.save(img_byte_arr, format=format)  # Сохраняем изображение в поток
    img_byte_arr.seek(0)  # Перемещаем указатель в начало потока
    return img_byte_arr.getvalue()  # Возвращаем байты



def cover_text(image_file: bytes, text: str, font_size: int) -> bytes:
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
    font_path = "arial-bold_tt.ttf"

    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        # Если шрифт не найден, используем стандартный
        font = ImageFont.load_default()

    # Разбиваем текст на строки, если он содержит переносы
    lines = text.split("\n")
    # print("Lines are:", lines)

    # Вычисляем размеры текста
    line_heights = []
    max_text_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]  # Ширина строки
        line_height = bbox[3] - bbox[1]  # Высота строки
        line_heights.append(line_height)
        if line_width > max_text_width:
            max_text_width = line_width

    # Общая высота текста с учетом отступов между строками
    total_text_height = sum(line_heights) + (len(lines) - 1) * 5  # 5px между строками

    # Определяем позицию текста
    line_weight = 20  # Ширина белой полосы
    padding_left = line_weight + 33  # Отступ слева
    padding_bottom = 251  # Отступ снизу
    text_x = padding_left + 40  # Отступ текста от полосы
    text_y = image.height - total_text_height - padding_bottom  # Позиция текста по вертикали

    # Рисуем белую полосу
    stripe_x1 = padding_left
    stripe_x2 = padding_left + line_weight  # Ширина полосы
    stripe_y1 = text_y
    stripe_y2 = image.height - padding_bottom
    draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill="white")
    # Добавляем текст на изображение
    for line in lines:
        draw.text((text_x, text_y), line, font=font, fill="white")  # fill - цвет текста
        text_y += line_heights[lines.index(line)] + 5  # Переход на следующую строку


    # Сохраняем результат в байты
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output.getvalue()