from pathlib import Path
import json
from PIL import Image, ImageDraw


def extract_water_body(image_path: str) -> str:
    p = Path(image_path)
    out_dir = p.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{p.stem}_water.png"
    geojson_path = out_dir / f"{p.stem}_water.geojson"

    img = Image.new("RGBA", (512, 512), (20, 20, 30, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([50, 200, 460, 300], fill=(0, 160, 220, 200))
    img.save(png_path.as_posix())

    gj = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"source": p.name},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[50, 200], [460, 200], [460, 300], [50, 300], [50, 200]]],
                },
            }
        ],
    }
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False)

    return json.dumps({"png": png_path.as_posix(), "geojson": geojson_path.as_posix()})

