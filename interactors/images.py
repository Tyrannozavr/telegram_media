import io

import pillow_heif
from PIL import Image, UnidentifiedImageError

from config import logger
from services.images import ImageBuilder
from services.text import ImageTextBuilder

pillow_heif.register_heif_opener()

TARGET_WIDTH = 2000
TARGET_HEIGHT = 2500

def _debug_image_info(image: Image.Image, stage: str):
    """Debug function to check image properties"""
    logger.info(f"Image at {stage}:")
    logger.info(f"Mode: {image.mode}")
    logger.info(f"Size: {image.size}")
    if image.mode == 'RGBA':
        # Check if image has any transparent pixels
        alpha = image.split()[3]
        transparent_pixels = sum(1 for pixel in alpha.getdata() if pixel == 0)
        total_pixels = image.size[0] * image.size[1]
        transparency_percentage = (transparent_pixels / total_pixels) * 100
        logger.info(f"Transparent pixels: {transparent_pixels} ({transparency_percentage:.2f}%)")

def image_instagram_process_interactor(text: str, font_size: int = 100, image: bytes = None) -> bytes:
    try:
        # Define standard size for all images


        if image is not None:
            # Existing code for when an image is provided
            blur_top = 480
            gradient_top = 600
            if text is not None:
                text = text.upper()

            # Пытаемся открыть изображение
            image = Image.open(io.BytesIO(image))
            _debug_image_info(image, "input")

            if image.width < image.height:
                blur_top = 0
                gradient_top = blur_top + 0

            resized_image = (ImageBuilder(image)
                             .resize_image(target_width=TARGET_WIDTH, target_height=TARGET_HEIGHT)
                             .blur_image(blur_top=blur_top)
                             .blur_gradient(blur_top=gradient_top, blur_bottom=blur_top)
                             .add_water_mark()
                             .build()
                             )
            _debug_image_info(resized_image, "after processing")
        else:
            # Create a transparent image with the same size as processed images
            resized_image = Image.new('RGBA', (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
            _debug_image_info(resized_image, "new transparent")

        # Process text for both cases (with or without image)
        if text is not None:
            text = text.upper()

        # When no image is provided, we want to ensure the text is added with transparency
        if image is None:
            # Create a new transparent image for text
            image_with_text = (ImageTextBuilder(resized_image, text=text, font_size=font_size)
                              .add_text_line_shadow()
                              .build())
            _debug_image_info(image_with_text, "final with text")
            # Convert to bytes using PNG format to preserve transparency
            output = io.BytesIO()
            image_with_text.save(output, format='PNG')
            return output.getvalue()
        else:
            image_with_text = (ImageTextBuilder(resized_image, text=text, font_size=font_size)
                              .add_text_line_shadow()
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