import io
from io import BytesIO

from PIL import Image, ImageFilter, ImageEnhance
from PIL import ImageDraw, ImageFont
from PIL.ImageFile import ImageFile


class ImageResizeProcess:
    @staticmethod
    def process_image(image_file: bytes) -> Image.Image:
        # Открываем изображение из байтов
        image = Image.open(io.BytesIO(image_file))

        # Определяем желаемый размер
        target_width, target_height = 2000, 2500

        # Определяем соотношение сторон исходного изображения
        width, height = image.size
        aspect_ratio = width / height

        # Если изображение прямоугольное (ширина больше высоты), обрезаем его до квадрата
        if width > height:
            # Вычисляем координаты для обрезки до квадрата
            left = (width - height) / 2
            top = 0
            right = (width + height) / 2
            bottom = height
            image = image.crop((left, top, right, bottom))
            width, height = image.size  # Обновляем размеры после обрезки

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

            # # Размываем зеркальную часть
            # blurred_mirrored = mirrored_image.filter(ImageFilter.GaussianBlur(20))

            # Затемняем зеркальную часть
            # enhancer = ImageEnhance.Brightness(blurred_mirrored)
            # darkened_mirrored = enhancer.enhance(0.5)  # Уменьшаем яркость на 50%

            # Вставляем затемнённую и размытую зеркальную часть
            final_image.paste(mirrored_image, (0, resized_image.height))
            blured_image = ImageResizeProcess._blur_image(final_image)
            with open("/home/user/PycharmProjects/Telegram/storage/pattern.png", "rb") as pattern_file:
                pattern = Image.open(pattern_file)
                final_image = ImageResizeProcess._add_pattern(image=blured_image, pattern=pattern)
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

    @staticmethod
    def _add_pattern(image: Image.Image, pattern: Image.Image) -> Image.Image:
        """
        Накладывает шаблон поверх основного изображения.
        Шаблон содержит затемнение и логотип.

        :param image: Основное изображение.
        :param pattern: Шаблон с затемнением и логотипом.
        :return: Изображение с наложенным шаблоном.
        """
        # Изменяем размер шаблона, чтобы он соответствовал ширине основного изображения
        pattern = pattern.resize((image.width, image.height))

        # Конвертируем изображения в режим RGBA для работы с прозрачностью
        image = image.convert("RGBA")
        pattern = pattern.convert("RGBA")

        # Накладываем шаблон поверх основного изображения
        result = Image.alpha_composite(image, pattern)

        # Конвертируем результат в RGB перед сохранением в JPEG
        result = result.convert("RGB")

        return result


    @staticmethod
    def _blur_image(image: Image.Image) -> Image.Image:
        """
        Размывает изображение: 500px снизу — полное размытие,
        а в диапазоне 500–550px снизу — градиентное размытие.

        :param image: Входное изображение.
        :return: Изображение с применённым размытием.
        """
        width, height = image.size

        # Создаем копию изображения для размытия
        blurred_image = image.copy()

        # Применяем полное размытие к нижним 500px
        bottom_part = blurred_image.crop((0, height - 500, width, height))
        bottom_part = bottom_part.filter(ImageFilter.GaussianBlur(radius=20))  # Сильное размытие
        blurred_image.paste(bottom_part, (0, height - 500))

        # Применяем градиентное размытие к диапазону 500–550px
        for y in range(height - 550, height - 500):
            # Вычисляем коэффициент размытия (от 0 до 1)
            blur_strength = (y - (height - 550)) / 50  # Градиент от 0 до 1
            radius = int(20 * blur_strength)  # Радиус размытия зависит от положения

            # Вырезаем строку и применяем размытие
            row = blurred_image.crop((0, y, width, y + 1))
            row = row.filter(ImageFilter.GaussianBlur(radius=radius))
            blurred_image.paste(row, (0, y))

        # Создаем маску для плавного перехода
        mask = Image.new("L", (width, height), 0)  # Черная маска (прозрачная)
        draw = ImageDraw.Draw(mask)

        # Нижние 500px — полностью размытые (маска = 255)
        draw.rectangle((0, height - 500, width, height), fill=255)

        # Диапазон 500–550px — градиентная маска
        for y in range(height - 550, height - 500):
            alpha = int(255 * ((y - (height - 550)) / 50))  # Градиент от 0 до 255
            draw.rectangle((0, y, width, y + 1), fill=alpha)

        # Накладываем размытую часть на исходное изображение с использованием маски
        result = Image.composite(blurred_image, image, mask)

        return result

# Преобразуем изображение в байты
def image_to_bytes(image: Image.Image, format: str = 'JPEG') -> bytes:
    img_byte_arr = io.BytesIO()  # Создаем байтовый поток
    image.save(img_byte_arr, format=format)  # Сохраняем изображение в поток
    img_byte_arr.seek(0)  # Перемещаем указатель в начало потока
    return img_byte_arr.getvalue()  # Возвращаем байты


def cover_text(image_file: bytes, text: str, font_size: int, logo: str = "@northossetia") -> bytes:
    """
    Создает изображение с текстом, размещенным внизу слева, и белой полосой.
    Добавляет размытую тень для текста и вертикальной линии.

    :param logo:
    :param image_file: Байты загруженного изображения.
    :param text: Текст для наложения.
    :param font_size: Размер шрифта.
    :return: Байты результирующего изображения.
    """
    # Загружаем изображение из байтов
    image = Image.open(BytesIO(image_file)).convert("RGBA")  # Конвертируем в RGBA для работы с прозрачностью
    draw = ImageDraw.Draw(image)

    # Загружаем шрифт
    font_path = "arial-bold_tt.ttf"
    try:
        font = ImageFont.truetype(font_path, size=font_size)
    except IOError:
        # Если шрифт не найден, используем стандартный
        font = ImageFont.load_default()

    # Разбиваем текст на строки
    lines = text.split("\n")

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
    text_y = image.height - total_text_height - padding_bottom - 20  # Позиция текста по вертикали

    # Параметры тени
    shadow_offset = 10  # Смещение тени (в пикселях)
    shadow_blur_radius = 4  # Радиус размытия тени
    shadow_color = (0, 0, 0, 255)

    # Создаем временное изображение для тени текста и линии
    shadow_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_image)

    # Рисуем тень для вертикальной линии
    stripe_x1 = padding_left + shadow_offset
    stripe_x2 = stripe_x1 + line_weight
    stripe_y1 = text_y + shadow_offset
    stripe_y2 = image.height - padding_bottom + shadow_offset
    shadow_draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=shadow_color)

    # Рисуем тень для текста
    temp_text_y = text_y + shadow_offset
    for line in lines:
        shadow_draw.text((text_x + shadow_offset, temp_text_y), line, font=font, fill=shadow_color)
        temp_text_y += line_heights[lines.index(line)] + 5  # Переход на следующую строку

    # Применяем размытие к теням
    shadow_image = shadow_image.filter(ImageFilter.GaussianBlur(shadow_blur_radius))
    # Накладываем размытую тень на основное изображение
    # image.paste(shadow_image, (0, 0), shadow_image)

    image = Image.alpha_composite(image, shadow_image)
    draw = ImageDraw.Draw(image)

    # # Накладываем размытую тень на основное изображение
    # combined_image = Image.alpha_composite(base_image, shadow_image)
    #
    # # Создаем объект для рисования на комбинированном изображении
    # draw = ImageDraw.Draw(combined_image)
    #
    # # Рисуем текст на комбинированном изображении
    # for i, line in enumerate(text_lines):
    #     draw.text((text_position[0], text_position[1] + i * line_height), line, font=font, fill="white")
    #
    # Рисуем белую полосу (основная линия)
    stripe_x1 = padding_left
    stripe_x2 = stripe_x1 + line_weight
    stripe_y1 = text_y
    stripe_y2 = image.height - padding_bottom
    draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill="white")

    # logo_size = 45
    # logo_font = ImageFont.truetype(font_path, size=logo_size)
    # bbox = draw.textbbox((0, 0), logo, font=logo_font)
    # additional_text_width = bbox[2] - bbox[0]
    # additional_text_height = bbox[3] - bbox[1]

    # Рисуем основной текст
    temp_text_y = text_y
    for line in lines:
        draw.text((text_x, temp_text_y), line, font=font, fill="white")  # fill - цвет текста
        temp_text_y += line_heights[lines.index(line)] + 5  # Переход на следующую строку

    # Позиция дополнительного текста
    # additional_text_x = (image.width - additional_text_width) // 2  # Центрируем по горизонтали
    # additional_text_y = image.height - additional_text_height - 70  # Отступ снизу 30px
    #
    # draw.text((additional_text_x, additional_text_y), logo, font=logo_font, fill=(255, 255, 255, 128))

    # Сохраняем результат в байты
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output.getvalue()
