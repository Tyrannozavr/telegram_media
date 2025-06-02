import io

from PIL import Image, ImageFilter
from PIL import ImageDraw

from config import IMAGES_DIR


class ImageBuilder:
    def __init__(self, image: Image.Image):
        self._image = image.copy()
        # Ensure image is in RGBA mode
        if self._image.mode != 'RGBA':
            self._image = self._image.convert('RGBA')

    def resize_image(self, target_width: int = 2000, target_height: int = 2500) -> "ImageBuilder":
        image = self._image

        # Если высота изображения больше целевой высоты, обрезаем по центру
        if image.height > target_height:
            # Вычисляем координаты для обрезки по центру
            top = (image.height - target_height) / 2
            bottom = top + target_height
            image = image.crop((0, top, image.width, bottom))

        if image.height > image.width * 1.25:
            # Если высота непропорционально больше ширины - обрезаем
            local_target_height = image.width * 1.25
            top = (image.height - local_target_height) / 2
            bottom = top + local_target_height
            image = image.crop((0, top, image.width, bottom))

        # Если изображение прямоугольное (ширина больше высоты), обрезаем его до квадрата
        if image.width > image.height:
            # Вычисляем координаты для обрезки до квадрата
            left = (image.width - image.height) // 2  # Используем целочисленное деление
            top = 0
            right = left + image.height  # Правая граница = левая граница + высота
            bottom = image.height
            image = image.crop((left, top, right, bottom))

        if image.width == image.height:
            # если квадрат (или был прямоугольником, но обрезали до квадрата)
            resized_image = image.resize((target_width, target_width), Image.Resampling.LANCZOS)
            # Создаем прозрачное изображение
            final_image = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
            final_image.paste(resized_image, (0, 0))

            mirrored_image = resized_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            # Создаем маску для зеркального отражения с градиентом прозрачности
            mask = Image.new("L", mirrored_image.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            for y in range(mirrored_image.height):
                alpha = int(255 * (1 - y / mirrored_image.height))
                mask_draw.line([(0, y), (mirrored_image.width, y)], fill=alpha)
            
            # Накладываем зеркальное отражение с маской
            final_image.paste(mirrored_image, (0, resized_image.height), mask)
            image = final_image

        if image.width < target_width or image.height < target_height:
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
        # Создаем маску для плавного перехода
        mask = Image.new("L", (width, blur_top), 0)
        mask_draw = ImageDraw.Draw(mask)
        for y in range(blur_top):
            alpha = int(255 * (y / blur_top))
            mask_draw.line([(0, y), (width, y)], fill=alpha)
        image.paste(bottom_part, (0, height - blur_top), mask)
        self._image = image
        return self

    def blur_gradient(self, blur_top: int = 500, blur_bottom: int = 550, radius: int = 10):
        """
        :param blur_top: верхняя граница размытия считая в пикселях снизу
        :param blur_bottom: нижняя граница размытия считая в пикселях снизу
        :param radius: радиус самого сильного размытия
        :return: Размывает изображение градиентом в указанном диапазоне уменьшая интенсивность при продвижении вверх
        """
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
        image = self._image
        width, height = image.size
        pattern = pattern.resize((width, height))
        # Убедимся, что паттерн в режиме RGBA
        if pattern.mode != 'RGBA':
            pattern = pattern.convert('RGBA')
        # Накладываем паттерн с сохранением прозрачности
        image = Image.alpha_composite(image, pattern)
        self._image = image
        return self

    @staticmethod
    def image_to_bytes(image: Image.Image, image_format: str = 'JPEG') -> bytes:
        # Сохраняем изображение в указанном формате, сохраняя прозрачность для PNG
        img_byte_arr = io.BytesIO()
        if image_format.upper() == 'PNG':
            # Для PNG сохраняем как есть (с прозрачностью)
            image.save(img_byte_arr, format='PNG')
        else:
            # Для других форматов конвертируем в RGB
            image = image.convert('RGB')
            image.save(img_byte_arr, format=image_format)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    def build(self) -> Image:
        return self._image

    def reset(self):
        self._image = None

    def to_bytes(self) -> bytes:
        image = self._image
        self.reset()
        return ImageBuilder.image_to_bytes(image, image_format='PNG')  # По умолчанию используем PNG для сохранения прозрачности


