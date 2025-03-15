import io

import pillow_heif
from PIL import Image, UnidentifiedImageError

from config import logger
from services.images import ImageBuilder, ImageTextBuilder

pillow_heif.register_heif_opener()

def image_instagram_process_interactor(image: bytes, text: str, font_size: int = 100) -> bytes:
    try:
        blur_top = 480
        gradient_top = 600
        if text is not None:
            text = text.upper()

        # Пытаемся открыть изображение
        image = Image.open(io.BytesIO(image))

        if image.width < image.height:
            blur_top = 0
            gradient_top = blur_top + 0

        resized_image = (ImageBuilder(image)
                         .resize_image()
                         .blur_image(blur_top=blur_top)
                         .blur_gradient(blur_top=gradient_top, blur_bottom=blur_top)
                         .add_water_mark()
                         .build()
                         )

        image_with_text = (ImageTextBuilder(resized_image, text=text, font_size=font_size)
                           .add_text_line_shadow(text_line_interval=15)
                           .to_bytes())

        return image_with_text

    except UnidentifiedImageError as e:
        logger.error(f"Unidentified image error: {e}")
        raise ValueError("Невозможно обработать файл. Убедитесь, что файл является изображением.")
    except Exception as e:
        logger.error(f"Error in image processing: {e}")
        raise


def print_size(image: Image.Image):
    with io.BytesIO() as output:
        image.save(output, format="JPEG")  # Можно использовать "JPEG" или другой формат
        image_bytes = output.getvalue()
        image_size_bytes = len(image_bytes)  # Вес изображения в байтах
        image_size_mb = image_size_bytes / (1024 * 1024)  # Переводим в мегабайты
        print(f"Вес изображения: {image_size_bytes} байт ({image_size_mb:.2f} МБ)")