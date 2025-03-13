# Test for cover_text function
from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor


def test_cover_text():
    with open(IMAGES_DIR / 'img1.PNG', 'rb') as f:
        image_bytes = f.read()
        test_text = (
            "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        )
        result = image_instagram_process_interactor(image_bytes, test_text, 100)
    with open(IMAGES_DIR / 'result.png', 'wb') as f:
        f.write(result)

test_cover_text()


# test_cover_text()
