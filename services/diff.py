from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch
from utils.image_utils import resize_images

def generate_diff(img1_path: str, img2_path: str, output_path: str = "diff.png") -> float:
    """Compares two images and generates a diff image. Returns mismatch percentage."""
    img1 = Image.open(img1_path).convert("RGBA")
    img2 = Image.open(img2_path).convert("RGBA")

    img1, img2 = resize_images(img1, img2)
    
    diff_img = Image.new("RGBA", img1.size)
    mismatch = pixelmatch(img1, img2, diff_img, includeAA=True)
    diff_img.save(output_path)
    
    total_pixels = img1.width * img1.height
    mismatch_percentage = (mismatch / total_pixels) * 100
    
    return mismatch_percentage
