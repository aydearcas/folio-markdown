# Folio icon

White F interpreted as a folded page, with a mint fold on a deep-teal field. The simple silhouette relates the brand to documents and remains recognizable at small sizes.

- Application asset: `folio/assets/folio.png` (opaque square).
- Windows asset: `folio/assets/folio.ico` (16, 24, 32, 48, 64, 128 and 256 pixels).
- Rebuild the ICO from the PNG with `python tools/build_icon.py` (requires Pillow).
- Qt uses the PNG so its icon does not depend on an optional ICO image-format plugin.

Generated with the built-in image-generation tool, using iterative edits. The final generation prompt was:

> Final production correction to the supplied Folio app icon: preserve the white F with the mint folded corner exactly, and preserve its centered scale. Replace the ENTIRE background, including every checkerboard pixel, with solid flat deep teal #216B60 extending all the way to all FOUR image edges. Output a completely opaque square teal icon. NO TRANSPARENCY, NO CHECKERBOARD, NO ROUNDED OUTER CORNERS, NO GRADIENT, NO SHADOW. The final image must have just three colors with anti-aliased edges: solid teal field, white F, mint corner fold. This should look like a simple professionally designed Windows application icon, not a rendering or mockup.

The generated PNG is used as delivered; the ICO is a format/size conversion using Pillow, not a separately drawn icon. The prompt describes the intended design, not an assertion of exact output pixel colors.
