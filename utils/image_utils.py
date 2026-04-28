from PIL import Image

def resize_images(img1: Image.Image, img2: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Resizes both images to the maximum dimensions of the two for comparison."""
    max_width = max(img1.width, img2.width)
    max_height = max(img1.height, img2.height)
    
    img1_resized = Image.new("RGBA", (max_width, max_height), (255, 255, 255, 0))
    img1_resized.paste(img1, (0, 0))
    
    img2_resized = Image.new("RGBA", (max_width, max_height), (255, 255, 255, 0))
    img2_resized.paste(img2, (0, 0))
    
    return img1_resized, img2_resized
