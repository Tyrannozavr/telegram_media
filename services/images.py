import io
from abc import ABC, abstractmethod
from io import BytesIO

from PIL import Image, ImageFilter, ImageEnhance
from PIL import ImageDraw, ImageFont
from PIL.ImageFile import ImageFile

from config import FONTS_DIR


def image_to_bytes(self, image: Image.Image, image_format: str = 'JPEG') -> bytes:
    # Если изображение в режиме RGBA, преобразуем его в RGB
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    img_byte_arr = io.BytesIO()  # Создаем байтовый поток
    image.save(img_byte_arr, format=image_format)  # Сохраняем изображение в поток
    img_byte_arr.seek(0)  # Перемещаем указатель в начало потока
    return img_byte_arr.getvalue()  # Возвращаем байты

class ImageResizeProcess:
    @staticmethod
    def process_image(image_file: bytes) -> Image.Image:
        # Открываем изображение из байтов
        image = Image.open(io.BytesIO(image_file))

        # Определяем желаемый размер
        target_width, target_height = 2000, 2500

        # Определяем соотношение сторон исходного изображения
        # width, height = image.size
        # aspect_ratio = width / height
        #
        # # Если изображение прямоугольное (ширина больше высоты), обрезаем его до квадрата
        # if width > height:
        #     # Вычисляем координаты для обрезки до квадрата
        #     left = (width - height) / 2
        #     top = 0
        #     right = (width + height) / 2
        #     bottom = height
        #     image = image.crop((left, top, right, bottom))
        #     # print("if")
        #     # image = image.resize((width, height*3), Image.Resampling.LANCZOS)
        #
        #     width, height = image.size  # Обновляем размеры после обрезки
        #     # print(width, height)
        #
        # # Если ширина недостаточна, растягиваем изображение по ширине
        # if width < target_width:
        #     # Масштабируем изображение до ширины 2000
        #     new_width = target_width
        #     new_height = int(new_width / aspect_ratio)
        #     resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        # else:
        #     # Если ширина достаточна, масштабируем по высоте
        #     new_height = target_height
        #     new_width = int(new_height * aspect_ratio)
        #     resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        #
        # # Если высота недостаточна, добавляем зеркальное отражение, размытие и затемнение
        # if resized_image.height < target_height:
        #     # Создаем новое изображение с высотой 2500
        #     final_image = Image.new('RGB', (resized_image.width, target_height), (0, 0, 0))
        #     final_image.paste(resized_image, (0, 0))
        #
        #     # Зеркально отражаем изображение вниз
        #     mirrored_image = resized_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        #
        #     # # Размываем зеркальную часть
        #     # blurred_mirrored = mirrored_image.filter(ImageFilter.GaussianBlur(20))
        #
        #     # Затемняем зеркальную часть
        #     # enhancer = ImageEnhance.Brightness(blurred_mirrored)
        #     # darkened_mirrored = enhancer.enhance(0.5)  # Уменьшаем яркость на 50%
        #
        #     # Вставляем затемнённую и размытую зеркальную часть
        #     final_image.paste(mirrored_image, (0, resized_image.height))
        #     final_image = ImageResizeProcess._blur_image(final_image)
        #
        # else:
        #     final_image = resized_image
        #
        # # Если ширина или высота превышают целевые, обрезаем изображение
        # if final_image.width > target_width or final_image.height > target_height:
        #     left = (final_image.width - target_width) / 2
        #     top = (final_image.height - target_height) / 2
        #     right = (final_image.width + target_width) / 2
        #     bottom = (final_image.height + target_height) / 2
        #     final_image = final_image.crop((left, top, right, bottom))
        #
        # with open("/home/user/PycharmProjects/Telegram/storage/pattern.png", "rb") as pattern_file:
        #     pattern = Image.open(pattern_file)
        #     final_image = ImageResizeProcess._add_pattern(image=final_image, pattern=pattern)
        # return final_image

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
        bottom_part = bottom_part.filter(ImageFilter.GaussianBlur(radius=10))  # Сильное размытие
        blurred_image.paste(bottom_part, (0, height - 500))

        # Применяем градиентное размытие к диапазону 500–550px
        for y in range(height - 550, height - 500):
            # Вычисляем коэффициент размытия (от 0 до 1)
            blur_strength = (y - (height - 550)) / 50  # Градиент от 0 до 1
            radius = int(10 * blur_strength)  # Радиус размытия зависит от положения

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
    font_path = FONTS_DIR / "arial-bold_tt.ttf"
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
    shadow_offset = 1  # Смещение тени (в пикселях)
    shadow_blur_radius = 7  # Радиус размытия тени
    shadow_color = (0, 0, 0, 255)

    # Создаем временное изображение для тени текста и линии
    shadow_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_image)

    # Рисуем тень для вертикальной линии
    stripe_x1 = padding_left + shadow_offset
    stripe_x2 = stripe_x1 + line_weight
    stripe_y1 = text_y + shadow_offset - 30
    stripe_y2 = image.height - padding_bottom + shadow_offset
    shadow_draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=shadow_color)

    text_line_interval = 11
    # Рисуем тень для текста
    temp_text_y = text_y + shadow_offset
    for line in lines:
        shadow_draw.text((text_x + shadow_offset, temp_text_y), line, font=font, fill=shadow_color)
        temp_text_y += line_heights[lines.index(line)] + text_line_interval  # Переход на следующую строку

    # Применяем размытие к теням
    shadow_image = shadow_image.filter(ImageFilter.GaussianBlur(shadow_blur_radius))
    # Накладываем размытую тень на основное изображение
    # image.paste(shadow_image, (0, 0), shadow_image)

    image = Image.alpha_composite(image, shadow_image)
    draw = ImageDraw.Draw(image)

    # Рисуем белую полосу (основная линия)
    stripe_x1 = padding_left
    stripe_x2 = stripe_x1 + line_weight
    stripe_y1 = text_y - 30
    stripe_y2 = image.height - padding_bottom
    draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill="white")

    temp_text_y = round(text_y - font_size / 5)
    for line in lines:
        draw.text((text_x, temp_text_y), line, font=font, fill="white")  # fill - цвет текста
        temp_text_y += line_heights[lines.index(line)] + text_line_interval  # Переход на следующую строку


    # Сохраняем результат в байты
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return output.getvalue()


class ImageBuilder:
    def __init__(self, image: Image.Image):
        self._image = image
        self.result = image.copy()


    def resize_image(self, target_width: int = 2000, target_height: int = 2500) -> "ImageBuilder":
        image = self._image
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

        if image.width == image.height:
            # если квадрат (или был прямоугольником, но обрезали до квадрата)
            resized_image = image.resize((target_width, int(target_width*1.125)), Image.Resampling.LANCZOS)
            # image 2000 * 2250
            final_image = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            final_image.paste(resized_image, (0, 0) )

            mirrored_image = resized_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            final_image.paste(mirrored_image, (0, resized_image.height))
        else:
            # Если высота больше, чем ширина растягиваем вширь
            resized_image = image.resize((target_width, int(target_width / aspect_ratio)), Image.Resampling.LANCZOS)
            final_image = resized_image
        self._image = final_image
        return self


    def blur_image(self, blur_top: int = 500, radius: int = 10):
        image = self._image
        width, height = image.size
        bottom_part = image.crop((0, height - blur_top, width, height))
        bottom_part = bottom_part.filter(ImageFilter.GaussianBlur(radius=radius))  # размытие
        image.paste(bottom_part, (0, height - blur_top))
        self._image = image
        return self

    def blur_gradient(self, blur_top: int = 500, blur_bottom: int = 550, radius: int = 10):
        image = self._image
        width, height = image.size

        # Создаем маску для плавного перехода
        mask = Image.new("L", (width, height), 0)  # Черная маска (прозрачная)
        draw = ImageDraw.Draw(mask)

        # Градиентная маска в диапазоне blur_top – blur_bottom
        gradient_length = blur_bottom - blur_top
        for y in range(height - blur_bottom, height - blur_top):
            alpha = int(255 * ((y - (height - blur_bottom)) / gradient_length))
            draw.rectangle((0, y, width, y + 1), fill=alpha)

        # Применяем размытие ко всему изображению
        blurred_image = image.filter(ImageFilter.GaussianBlur(radius))

        # Накладываем размытую часть на исходное изображение с использованием маски
        result = Image.composite(blurred_image, image, mask)
        self._image = result
        return self

    @staticmethod
    def image_to_bytes(image: Image.Image, image_format: str = 'JPEG') -> bytes:
        # Если изображение в режиме RGBA, преобразуем его в RGB
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        img_byte_arr = io.BytesIO()  # Создаем байтовый поток
        image.save(img_byte_arr, format=image_format)  # Сохраняем изображение в поток
        img_byte_arr.seek(0)  # Перемещаем указатель в начало потока
        return img_byte_arr.getvalue()  # Возвращаем байты

    def build(self) -> Image:
        return self._image


# class ImageProcessor(ABC):
#     @abstractmethod
#     def process(self) -> bytes:
#         pass
#
    # def image_to_bytes(self, image: Image.Image, image_format: str = 'JPEG') -> bytes:
    #     # Если изображение в режиме RGBA, преобразуем его в RGB
    #     if image.mode == 'RGBA':
    #         image = image.convert('RGB')
    #     img_byte_arr = io.BytesIO()  # Создаем байтовый поток
    #     image.save(img_byte_arr, format=image_format)  # Сохраняем изображение в поток
    #     img_byte_arr.seek(0)  # Перемещаем указатель в начало потока
    #     return img_byte_arr.getvalue()  # Возвращаем байты
#
#
#
# class ImageResizeProcessor(ImageProcessor):
#     def __init__(self, target_width: int = 2000, target_height: int = 2500):
#         """
#         :param target_width: width output image
#         :param target_height: height output image
#         """
#         self.target_width = target_width
#         self.target_height = target_height
#
#     def process(self) -> bytes:
#         pass
#
# class ImageWaterMarkProcess:
#     def __init__(self):
#         pass