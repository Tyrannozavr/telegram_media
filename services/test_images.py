# Test for cover_text function
from interactors.images import image_instagram_process_interactor


def test_cover_text():
    with open('img.png', 'rb') as f:
        image_bytes = f.read()
        test_text = (
            "Инал тасоев и мадина таймазова выступят на тбилисском большом шлеме"
        )
        result = image_instagram_process_interactor(image_bytes, test_text, 100)
    with open('result.png', 'wb') as f:
        f.write(result)

test_cover_text()


# test_cover_text()
