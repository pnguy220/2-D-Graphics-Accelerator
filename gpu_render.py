from PIL import Image


def rgb332_to_rgb888(pixel):
    """Expand one RGB332 byte into an (R, G, B) tuple of 8-bit channels."""
    red = (pixel >> 5) & 0x07
    green = (pixel >> 2) & 0x07
    blue = pixel & 0x03

    return (
        red * 255 // 7,
        green * 255 // 7,
        blue * 255 // 3,
    )


def save_framebuffer(pixels, filename="gpu_output.png", scale=8):
    """Convert 4096 RGB332 pixels to RGB888 and save a scaled PNG."""
    if len(pixels) != 4096:
        raise ValueError(f"expected 4096 pixels, received {len(pixels)}")
    if scale < 1:
        raise ValueError("scale must be at least 1")

    image = Image.new("RGB", (64, 64))
    image.putdata([rgb332_to_rgb888(pixel) for pixel in pixels])
    if scale != 1:
        image = image.resize((64 * scale, 64 * scale), Image.Resampling.NEAREST)
    image.save(filename)
    return filename
