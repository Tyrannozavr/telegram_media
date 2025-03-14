import io

from PIL import Image, ImageFilter
from PIL import ImageDraw, ImageFont

from config import FONTS_DIR, IMAGES_DIR


class ImageBuilder:
    def __init__(self, image: Image.Image):
        self._image = image.copy()

    def resize_image(self, target_width: int = 2000, target_height: int = 2500) -> "ImageBuilder":
        image = self._image
        width, height = image.size
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
            resized_image = image.resize((target_width, target_width), Image.Resampling.LANCZOS)
            # resized_image = image.resize((target_width, int(target_width*1.125)), Image.Resampling.LANCZOS)
            # image 2000 * 2250
            final_image = Image.new("RGB", (target_width, target_height), (0, 0, 0))
            final_image.paste(resized_image, (0, 0))

            mirrored_image = resized_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            final_image.paste(mirrored_image, (0, resized_image.height))
            image = final_image

        # Если высота изображения больше целевой высоты, обрезаем по центру
        if height > target_height:
            # Вычисляем координаты для обрезки по центру
            top = (height - target_height) / 2
            bottom = top + target_height
            image = image.crop((0, top, width, bottom))

        if width < target_width:
            # Если высота больше, чем ширина растягиваем вширь
            resized_image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            image = resized_image
        self._image = image
        return self

    def blur_image(self, blur_top: int = 500, radius: int = 10):
        """
        :param blur_top: верхняя граница размытия считая в пикселях снизу
        :param radius: радиус размытия
        :return:
        """
        image = self._image
        width, height = image.size
        bottom_part = image.crop((0, height - blur_top, width, height))
        bottom_part = bottom_part.filter(ImageFilter.GaussianBlur(radius=radius))  # размытие
        image.paste(bottom_part, (0, height - blur_top))
        self._image = image
        return self

    def blur_gradient(self, blur_top: int = 500, blur_bottom: int = 550, radius: int = 10):
        """
        :param blur_top: верхняя граница размытия считая в пикселях снизу
        :param blur_bottom: нижняя граница размытия считая в пикселях снизу
        :param radius: радиус самого сильного размытия
        :return: Размывает изображение градиентом в указанном диапазоне уменьшая интенсивность при продвижении вверх
        """
        # """Поменять местами top и bottom"""
        image = self._image
        width, height = image.size

        # Создаем маску для плавного перехода
        mask = Image.new("L", (width, height), 0)  # Черная маска (прозрачная)
        draw = ImageDraw.Draw(mask)

        # Градиентная маска в диапазоне blur_top – blur_bottom
        gradient_length = blur_top - blur_bottom
        for y in range(height - blur_top, height - blur_bottom):
            alpha = int(255 * ((y - (height - blur_top)) / gradient_length))
            draw.rectangle((0, y, width, y + 1), fill=alpha)

        # Применяем размытие ко всему изображению
        blurred_image = image.filter(ImageFilter.GaussianBlur(radius))

        # Накладываем размытую часть на исходное изображение с использованием маски
        result = Image.composite(blurred_image, image, mask)
        self._image = result
        return self

    def add_water_mark(self, pattern: Image.Image = Image.open(IMAGES_DIR / "official/pattern.png")):
        image = self._image.convert("RGBA")
        width, height = image.size
        pattern = pattern.resize((width, height))
        image = Image.alpha_composite(image, pattern)
        self._image = image.convert("RGB")
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

    def reset(self):
        self._image = None

    def to_bytes(self) -> bytes:
        image = self._image
        self.reset()
        return ImageBuilder.image_to_bytes(image)

class ImageTextBuilder:
    def __init__(
            self,
            image: Image.Image,
            text: str,
            font_size: int = 100,
            reference_font_size: int = 110,
            reference_width: int = 25,
            font_path: str = FONTS_DIR / "arial-bold_tt.ttf"):
        """

        :param image:
        :param text:
        :param font_size:
        :param reference_width: Количество символов допустимое на строке при заданной ширине reference_font_size
        :param reference_font_size: Шрифт для определения максимальной ширины строки
        """
        self._image = image.copy()
        self.text = text
        self.font_size = font_size
        self.reference_width = reference_width
        self.reference_font_size = reference_font_size
        # Загружаем шрифт
        try:
            self.font = ImageFont.truetype(font_path, size=font_size)
        except IOError:
            # Если шрифт не найден, используем стандартный
            self.font = ImageFont.load_default()

    def _calculate_characters_width(self) -> int:
        """
        Рассчитывает количество символов, которые поместятся в строку, на основе размера шрифта.

        :return: Количество символов, которые поместятся в строку.
        """
        # Используем пропорцию для расчета
        # Ширина текста пропорциональна размеру шрифта
        new_width = (self.reference_width * self.reference_font_size) / self.font_size
        return int(new_width)

    def _split_text(self, text: str, width: int) -> list:
        """
        Ограничивает текст по ширине, добавляя переносы строк.
        Старается не разбивать слова, но если это необходимо, добавляет символ переноса "-".

        :param text: Входной текст.
        :param width: Максимальная ширина строки (по умолчанию равна reference font size).
        :return: Текст с переносами строк.
        """
        if width is None:
            width = self.reference_width

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

        return wrapped_text

    def add_text_line_shadow(
            self,
            text_array=None,
            strip_width: int = 20,
            padding_bottom: int = 251,
            padding_left: int = 33,
            shadow_offset_x: int = 12,
            shadow_offset_y: int = 12,
            shadow_blur_radius: int = 4,
            shadow_color: tuple = (0, 0, 0, 255),
            text_color: str = "white",
            text_line_interval: int = 13
    ) -> "ImageTextBuilder":
        """
        Создает изображение с текстом, размещенным внизу слева, и белой полосой.
        Добавляет размытую тень для текста и вертикальной линии.

        :param shadow_offset_y: Смещение тени px
        :param shadow_offset_x: Смещение тени px
        :param text_line_interval:
        :param text_color: Цвет текста и линии
        :param shadow_color: Цвет тени в RGBA формате
        :param shadow_blur_radius: Радиус размытия тени
        :param padding_left: Отступ слева
        :param padding_bottom: Отступ снизу
        :param strip_width: Ширина белой полосы
        :param text_array: Список строк, которые нужно добавить
        :return: Байты результирующего изображения.
        """
        text_line_width = self._calculate_characters_width()
        if text_array is None:
            text_array = self._split_text(self.text, width=text_line_width)

        # Конвертируем изображение в RGBA (с прозрачностью)
        image = self._image.convert("RGBA")
        draw = ImageDraw.Draw(image)
        padding_left += strip_width

        line_height = 0
        # Вычисляем размеры текста
        if len(text_array) > 0:
            line = text_array[0]
            bbox = draw.textbbox((0, 0), line, font=self.font)
            line_height = bbox[3] - bbox[1] # высота строки
        line_heights = [line_height] * len(text_array)

        # Общая высота текста с учетом отступов между строками
        total_text_height = sum(line_heights) + (len(text_array) - 1) * text_line_interval  # 5px между строками

        # Определяем позицию текста
        text_x = padding_left + 40  # Отступ текста от полосы
        text_y = image.height - total_text_height - padding_bottom - 20  # Позиция текста по вертикали

        # Создаем временное изображение для тени текста и линии
        shadow_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_image)

        # Рисуем тень для вертикальной линии
        stripe_x1 = padding_left + shadow_offset_x
        stripe_x2 = stripe_x1 + strip_width
        stripe_y1 = text_y + shadow_offset_y - 30
        stripe_y2 = image.height - padding_bottom + shadow_offset_y
        shadow_draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=shadow_color)

        # Рисуем тень для текста
        temp_text_y = round(text_y - self.font_size / 5) + shadow_offset_y
        for line in text_array:
            shadow_draw.text((text_x+shadow_offset_x, temp_text_y), line, font=self.font, fill=shadow_color)
            temp_text_y += line_heights[text_array.index(line)] + text_line_interval  # Переход на следующую строку

        # Применяем размытие к теням
        shadow_image = shadow_image.filter(ImageFilter.GaussianBlur(shadow_blur_radius))

        # Накладываем размытую тень на основное изображение
        image = Image.alpha_composite(image, shadow_image)
        draw = ImageDraw.Draw(image)

        # Рисуем текст
        temp_text_y = round(text_y - self.font_size / 5)
        for line in text_array:
            draw.text((text_x, temp_text_y), line, font=self.font, fill=text_color)  # fill - цвет текста
            temp_text_y += line_heights[text_array.index(line)] + text_line_interval  # Переход на следующую строку

        # Рисуем белую полосу (основная линия)
        stripe_x1 = padding_left
        stripe_x2 = stripe_x1 + strip_width
        stripe_y1 = text_y - 30
        stripe_y2 = image.height - padding_bottom
        draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=text_color)



        # Возвращаем измененное изображение
        self._image = image
        return self

    def reset(self):
        self._image = None

    def build(self) -> Image.Image:
        image = self._image
        self.reset()
        return image

    def to_bytes(self) -> bytes:
        image = self._image
        self.reset()
        return ImageBuilder.image_to_bytes(image)
