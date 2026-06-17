# config.py

# PATHS
PATH_ICONS  = "widgets/icons/"
PATH_LOGS   = "data/logs/"
PATH_CSV    = "data/logs/"
PATH_IMAGES = ""

# WINDOW
WINDOW_HEIGHT           = 1080
WINDOW_WIDTH            = 1920
WINDOW_BACKGROUND_COLOR = "#000020"

# SURFACES  (darker → lighter)
SURFACE_NAV    = "#02021a"   # sidebar
SURFACE_CARD   = "#0a0a2e"   # panel/card background
SURFACE_RAISED = "#111138"   # hover, elevated elements
BORDER_COLOR   = "#1a1a50"   # dividers and borders

# ACCENTS
ACCENT        = "#00aaff"    # primary blue
ACCENT_PURPLE = "#aa44ff"    # secondary purple
ACCENT_GREEN  = "#00e5a0"    # success / teal
ACCENT_AMBER  = "#ffaa00"    # warning
ACCENT_RED    = "#ff3355"    # danger

# TEXT
TEXT_COLOR = "#e8eaff"       # primary
TEXT_MUTED = "#55558a"       # secondary / labels

# BUTTON
BUTTON_HEIGHT = 52
BUTTON_WIDTH  = 260

# BUTTON STATE BACKGROUNDS
BACKGROUND_COLOR   = "transparent"
BACKGROUND_HOVER   = "#111138"
BACKGROUND_PRESSED = "#1a1a50"
BACKGROUND_ACTIVE  = "#0a0a35"

# FONT
FONT_FAMILY = "Quantico"
FONT_SIZE   = 20

# SHARED PANEL CARD STYLE  (used by every QGroupBox panel)
PANEL_STYLE = f"""
    QGroupBox {{
        background-color: {SURFACE_CARD};
        border: 1px solid {BORDER_COLOR};
        border-top: 2px solid {ACCENT};
        border-radius: 8px;
        margin-top: 22px;
        padding-top: 14px;
        font-family: {FONT_FAMILY};
        font-size: 11px;
        font-weight: normal;
        color: {TEXT_MUTED};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 3px 10px;
        background-color: {SURFACE_CARD};
        color: {ACCENT};
        font-family: {FONT_FAMILY};
        font-size: 11px;
    }}
"""
