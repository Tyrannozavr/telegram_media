from PIL import Image, ImageFilter
from PIL import ImageDraw, ImageFont

from config import FONTS_DIR
from services.images import ImageBuilder


class ImageTextBuilder:
    def __init__(
            self,
            image: Image.Image,
            text: str,
            font_size: int = 100,
            reference_font_size: int = 150,
            reference_width: int = 17,
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
            # Если добавление слова превышает лимит, завершаем текущую строку
            if len(current_line) + len(word) + 1 > width:  # +1 для пробела
                if current_line:
                    wrapped_text.append(current_line.rstrip())
                current_line = ''

            # Добавляем слово в текущую строку
            current_line += word + ' '

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
            second_shadow_offset: int = -4,
            shadow_blur_radius: int = 4,
            second_shadow_blur_radius: int = 12,  # Новый параметр для второй тени
            shadow_color: tuple = (0, 0, 0, 255),
            text_color: str = "white",
            text_line_interval: int = 0
    ) -> "ImageTextBuilder":
        """
        Создает изображение с текстом, размещенным внизу слева, и белой полосой.
        Добавляет размытую тень для текста и вертикальной линии.

        :param second_shadow_offset:
        :param second_shadow_blur_radius: Радиус размытия второй тени
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

        line_heights = [self.font_size + text_line_interval] * len(text_array)
        # Общая высота текста с учетом отступов между строками
        total_text_height = sum(line_heights) + (len(text_array) - 1) * text_line_interval  # 5px между строками
        # Определяем позицию текста
        text_x = padding_left + 40  # Отступ текста от полосы
        text_y = image.height - padding_bottom - total_text_height + 20 # Позиция текста по вертикали
        # Создаем временное изображение для первой тени текста и линии
        shadow_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_image)

        # Рисуем первую тень для вертикальной линии
        stripe_x1 = padding_left + shadow_offset_x
        stripe_x2 = stripe_x1 + strip_width
        stripe_y1 = text_y + shadow_offset_y - 30
        stripe_y2 = image.height - padding_bottom + shadow_offset_y
        shadow_draw.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=shadow_color)
        # Рисуем первую тень для текста
        temp_text_y = round(text_y - self.font_size / 5) + shadow_offset_y
        for line in text_array:
            shadow_draw.text((text_x + shadow_offset_x, temp_text_y), line, font=self.font, fill=shadow_color)
            temp_text_y += self.font_size + text_line_interval # Переход на следующую строку

        # Применяем размытие к первой тени
        shadow_image = shadow_image.filter(ImageFilter.GaussianBlur(shadow_blur_radius))

        # Накладываем первую тень на основное изображение
        image = Image.alpha_composite(image, shadow_image)

        # Создаем временное изображение для второй тени (без смещения)
        shadow_image2 = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw2 = ImageDraw.Draw(shadow_image2)

        # Рисуем вторую тень для вертикальной линии (без смещения)
        stripe_x1 = padding_left
        stripe_x2 = stripe_x1 + strip_width
        stripe_y1 = text_y - 30
        stripe_y2 = image.height - padding_bottom
        shadow_draw2.rectangle([stripe_x1, stripe_y1, stripe_x2, stripe_y2], fill=shadow_color)

        # Рисуем вторую тень для текста (без смещения)
        temp_text_y = round(text_y - self.font_size / 5) + second_shadow_offset
        for line in text_array:
            shadow_draw2.text((text_x + second_shadow_offset, temp_text_y), line, font=self.font, fill=shadow_color)
            temp_text_y += self.font_size + text_line_interval # Переход на следующую строку

        # Применяем размытие ко второй тени
        shadow_image2 = shadow_image2.filter(ImageFilter.GaussianBlur(second_shadow_blur_radius))

        # Накладываем вторую тень на основное изображение
        image = Image.alpha_composite(image, shadow_image2)

        # Обновляем объект ImageDraw для основного изображения
        draw = ImageDraw.Draw(image)

        # Рисуем текст
        temp_text_y = round(text_y - self.font_size / 5)
        for line in text_array:
            draw.text((text_x, temp_text_y), line, font=self.font, fill=text_color)  # fill - цвет текста
            temp_text_y += self.font_size + text_line_interval # Переход на следующую строку
            # temp_text_y += line_heights[text_array.index(line)] + text_line_interval  # Переход на следующую строку

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