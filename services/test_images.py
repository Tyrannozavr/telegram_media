# Test for cover_text function
from interactors.images import image_instagram_process_interactor


def test_cover_text():
    with open('img.png', 'rb') as f:
        image_bytes = f.read()
        test_text = (
            "Это пример текста, который нужно ограничить по ширине в 32 символа. "
            "Он содержит длинные слова, такие как 'саморазвитие' и 'высокотехнологичный', "
            "а также короткие слова."
        )
        result = image_instagram_process_interactor(image_bytes, test_text, 100)
    with open('result.png', 'wb') as f:
        f.write(result)

test_cover_text()


# test_cover_text()
