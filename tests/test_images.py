# Test for cover_text function
import io

from PIL import Image

from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor
from services.images import ImageBuilder, ImageTextBuilder

def test_image_builder():
    with open(IMAGES_DIR / 'test.JPG', 'rb') as f:
        text = "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        image_with_text = image_instagram_process_interactor(image=f.read(), text=text)
        # image = Image.open(io.BytesIO(f.read()))
        # resized_image = ImageBuilder(image).resize_image().blur_image().blur_gradient().add_water_mark().build()
        # image_with_text = ImageTextBuilder(resized_image, text=text).add_text_line_shadow().build()
    with open(IMAGES_DIR / 'result.png', 'wb') as f:
        f.write(image_with_text)

test_image_builder()