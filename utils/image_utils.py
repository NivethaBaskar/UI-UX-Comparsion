from PIL import Image

def resize_images(img1: Image.Image, img2: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Scale img2 to match img1's dimensions for accurate pixel comparison."""
    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.LANCZOS)
    return img1, img2
