# Test for cover_text function
from services.images import cover_text, process_image, image_to_bytes
from services.text import wrap_text, calculate_characters_width


def test_cover_text():
    # Read test image file as bytes
    with open('img_1.png', 'rb') as f:
        image_bytes = f.read()

    # Test parameters
    # test_text = "Test Text"
    test_text = (
    "Это пример текста, который нужно ограничить по ширине в 32 символа. "
    "Он содержит длинные слова, такие как 'саморазвитие' и 'высокотехнологичный', "
    "а также короткие слова."
)
    # test_text = "12345hello, world уцацуукцук"
    test_font_size = 100

    text_width = calculate_characters_width(test_font_size)
    # output_text = test_text
    output_text = wrap_text(test_text, width=text_width)
    # print("Output text is", output_text)
    image_resized = process_image(image_bytes)
    # image_bytes_resized = image_resized.tobytes()
    image_bytes_resized = image_to_bytes(image_resized)
    # Call cover_text function
    result = cover_text(image_bytes_resized, output_text, test_font_size)

    # Verify result is bytes
    assert isinstance(result, bytes)

    # Verify result is not empty
    assert len(result) > 0
    # Save result to file
    with open('result.png', 'wb') as f:
        f.write(result)

test_cover_text()


# test_cover_text()
