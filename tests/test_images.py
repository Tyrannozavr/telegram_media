# Test for cover_text function
import io

from PIL import Image

from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor
from services.images import ImageBuilder, ImageTextBuilder


def test_cover_text():
    with open(IMAGES_DIR / 'test.JPG', 'rb') as f:
        image_bytes = f.read()
        test_text = (
            "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        )
        result = image_instagram_process_interactor(image_bytes, test_text, 100)
    with open(IMAGES_DIR / 'result.png', 'wb') as f:
        f.write(result)

# test_cover_text()


# test_cover_text()
def test_image_builder():
    with open(IMAGES_DIR / 'test.JPG', 'rb') as f:
        text = "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        image = Image.open(io.BytesIO(f.read()))
        resized_image = ImageBuilder(image).resize_image().blur_image().blur_gradient().add_water_mark().build()
        image_with_text = ImageTextBuilder(resized_image, text=text).add_text_line_shadow().build()
    with open(IMAGES_DIR / 'result.png', 'wb') as f:
        f.write(ImageBuilder.image_to_bytes(image_with_text))

test_image_builder()