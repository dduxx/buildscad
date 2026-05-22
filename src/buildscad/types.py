from enum import Enum


class ColorScheme(Enum):
    CORNFIELD = "Cornfield"
    SUNSET = "Sunset"
    METALLIC = "Metallic"
    STARLIGHT = "Starlight"
    BEFORE_DAWN = "BeforeDawn"
    NATURE = "Nature"
    DEEP_OCEAN = "DeepOcean"
    SOLARIZED = "Solarized"


class OutputType(Enum):
    STL = "stl"
    THREE_MF = "3mf"
    AMF = "amf"
    OFF = "off"
    DXF = "dxf"
    SVG = "svg"
    PNG = "png"
    CSG = "csg"
    ECHO = "echo"
    AST = "ast"
