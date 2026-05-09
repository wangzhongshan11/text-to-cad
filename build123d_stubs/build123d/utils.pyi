from build123d.build_enums import FontStyle as FontStyle
from dataclasses import dataclass

@dataclass(frozen=True)
class FontInfo:
    name: str
    styles: tuple[FontStyle, ...]

def available_fonts() -> list[FontInfo]: ...
