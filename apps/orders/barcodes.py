from io import BytesIO

try:
    import barcode
    from barcode.writer import SVGWriter
except Exception:  # pragma: no cover
    barcode = None
    SVGWriter = None


def code128_svg(value: str) -> str:
    if barcode is None or SVGWriter is None:
        return ""
    stream = BytesIO()
    barcode.get("code128", value, writer=SVGWriter()).write(stream)
    return stream.getvalue().decode("utf-8")
