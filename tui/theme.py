"""
Exhaustive Accent Theme Palette Engine for Ally.
Author: Bright da dev
"""

THEMES = {
    "cobalt": {
        "name": "Cobalt Blue (Default)",
        "primary": "#005a9e",
        "primary_hover": "#007acc",
        "accent": "#007acc",
        "cursor_bg": "#002b4d",
        "border": "#004070",
    },
    "monochrome": {
        "name": "Graphite Stealth",
        "primary": "#333333",
        "primary_hover": "#555555",
        "accent": "#ffffff",
        "cursor_bg": "#1c1c1c",
        "border": "#444444",
    },
    "amber": {
        "name": "Amber Gold",
        "primary": "#b87004",
        "primary_hover": "#e08906",
        "accent": "#f59e0b",
        "cursor_bg": "#331c00",
        "border": "#7a4a02",
    },
    "emerald": {
        "name": "Terminal Emerald",
        "primary": "#0e7a53",
        "primary_hover": "#129c6a",
        "accent": "#10b981",
        "cursor_bg": "#032418",
        "border": "#084e34",
    },
    "cyan": {
        "name": "Electric Cyan",
        "primary": "#0088a8",
        "primary_hover": "#00b4d8",
        "accent": "#00e5ff",
        "cursor_bg": "#002633",
        "border": "#005570",
    },
    "purple": {
        "name": "Tokyo Purple",
        "primary": "#6d3bcc",
        "primary_hover": "#864def",
        "accent": "#a78bfa",
        "cursor_bg": "#231147",
        "border": "#462287",
    },
}

DEFAULT_THEME = "cobalt"


def get_theme(theme_name: str = "cobalt") -> dict:
    return THEMES.get(theme_name.lower(), THEMES[DEFAULT_THEME])