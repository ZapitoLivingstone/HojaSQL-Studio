from pathlib import Path

from PIL import Image, ImageOps


SOURCE_JPG = Path("chopper.jpg")
SOURCE_ICO = Path("chopper.ico")
OUTPUT_ICO = Path("chopper.ico")
OUTPUT_PNG = Path("assets/hojasql.png")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    if SOURCE_JPG.exists():
        image = Image.open(SOURCE_JPG).convert("RGBA")
        icons = []

        for size in SIZES:
            canvas = Image.new("RGBA", size, (18, 18, 24, 255))
            fitted = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
            x = (size[0] - fitted.width) // 2
            y = (size[1] - fitted.height) // 2
            canvas.alpha_composite(fitted, (x, y))
            icons.append(canvas)

        icons[-1].save(OUTPUT_ICO, sizes=SIZES)
        image = icons[-1]
        print(f"Icono ICO generado: {OUTPUT_ICO}")
    elif SOURCE_ICO.exists():
        image = Image.open(SOURCE_ICO).convert("RGBA")
        print(f"Usando icono existente: {SOURCE_ICO}")
    else:
        raise SystemExit("No existe una fuente de icono utilizable: chopper.jpg o chopper.ico")

    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PNG, format="PNG")
    print(f"Icono PNG generado: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
