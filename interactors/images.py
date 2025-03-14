import io

from PIL import Image

from services.images import ImageBuilder, ImageTextBuilder


def image_instagram_process_interactor(image: bytes, text: str, font_size: int = 100):
    image = Image.open(io.BytesIO(image))
    resized_image = ImageBuilder(image).resize_image().blur_image().blur_gradient().add_water_mark().build()
    image_with_text = ImageTextBuilder(resized_image, text=text).add_text_line_shadow().build()
    return image_with_text