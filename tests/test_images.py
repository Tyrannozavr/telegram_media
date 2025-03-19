# Test for cover_text function

from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor

def test_image_builder():
    with open(IMAGES_DIR / 'sample1.heic', 'rb') as f:
        # text = "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        text = "31 марта в дк ггау пройдет молодежный концерт артистов tara202,andi,mendiga"
        text1 = "карты инфраструктуры мира дают полное визуальное представление"
        image_with_text = image_instagram_process_interactor(image=f.read(), text=text, font_size=100)
    with open(IMAGES_DIR / 'result.jpg', 'wb') as f:
        f.write(image_with_text)

test_image_builder()