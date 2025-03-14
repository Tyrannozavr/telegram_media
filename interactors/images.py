import io

from PIL import Image

from services.images import ImageBuilder, ImageTextBuilder


def image_instagram_process_interactor(image: bytes, text: str, font_size: int = 100) -> bytes:
    blur_top = 480
    gradient_top = 600
    text = text.upper()
    image = Image.open(io.BytesIO(image))
    resized_image = (ImageBuilder(image)
                     .resize_image()
                     .blur_image(blur_top=blur_top)
                     .blur_gradient(blur_top=gradient_top, blur_bottom=blur_top)
                     .add_water_mark()
                     .build()
                     )
    image_with_text = (ImageTextBuilder(resized_image, text=text, font_size=font_size, )
                       .add_text_line_shadow()
                       .to_bytes())
    return image_with_text
