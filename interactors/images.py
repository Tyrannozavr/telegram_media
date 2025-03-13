from services.images import process_image, image_to_bytes, cover_text
from services.text import wrap_text, calculate_characters_width


def image_instagram_process_interactor(image: bytes, text: str, font_size: int = 100):
    text_width = calculate_characters_width(font_size)
    text_split = wrap_text(text, width=text_width)
    image_resized = process_image(image)
    image_bytes_resized = image_to_bytes(image_resized)
    output_image = cover_text(image_bytes_resized, text=text_split, font_size=font_size)
    return output_image