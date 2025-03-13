# Test for cover_text function
import io

from PIL import Image

from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor
from services.images import ImageBuilder


def test_cover_text():
    with open(IMAGES_DIR / 'img1.PNG', 'rb') as f:
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
    with open(IMAGES_DIR / 'img1.PNG', 'rb') as f:
        image = Image.open(io.BytesIO(f.read()))
        result = ImageBuilder(image).resize_image().blur_image().blur_gradient().add_water_mark().build()
    with open(IMAGES_DIR / 'result.png', 'wb') as f:
        f.write(ImageBuilder.image_to_bytes(result))

test_image_builder()