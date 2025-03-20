# Test for cover_text function

from config import IMAGES_DIR
from interactors.images import image_instagram_process_interactor

def test_image_builder():
    with open(IMAGES_DIR / 'sample1.heic', 'rb') as f:
        # text = "Инал Тасоев и Мадина Таймазова выступят на тбилисском «Большом шлеме»"
        text = "ОБЬЯВЛЕНА РОВНО 5 ЛЕТ НАЗАД БЫЛА ОБЬЯВЛЕНА ОФИЦИАЛЬНАЯ ГЛОБАЛЬНАЯ ПАНДЕМИЯ COVID-19"
        image_with_text = image_instagram_process_interactor(image=f.read(), text=text, font_size=100)
    with open(IMAGES_DIR / 'result.jpg', 'wb') as f:
        f.write(image_with_text)

test_image_builder()