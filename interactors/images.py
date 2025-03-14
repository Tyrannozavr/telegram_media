import io

from PIL import Image

from services.images import ImageBuilder, ImageTextBuilder


def image_instagram_process_interactor(image: bytes, text: str, font_size: int = 100) -> bytes:
    blur_top = 480
    gradient_top = 600
    if text is not None:
        text = text.upper()
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
    image_with_text = (ImageTextBuilder(resized_image, text=text, font_size=font_size, )
                       .add_text_line_shadow()
                       .to_bytes())
    return image_with_text


def print_size(image: Image.Image):
    with io.BytesIO() as output:
        image.save(output, format="JPEG")  # Можно использовать "JPEG" или другой формат
        image_bytes = output.getvalue()
        image_size_bytes = len(image_bytes)  # Вес изображения в байтах
        image_size_mb = image_size_bytes / (1024 * 1024)  # Переводим в мегабайты
        print(f"Вес изображения: {image_size_bytes} байт ({image_size_mb:.2f} МБ)")