from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, PrintHistory, SavedSetting
from datetime import datetime
import os
import io

app = Flask(__name__)
app.secret_key = 'optimalprint-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///optimalprint.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

FILAMENT_SETTINGS = {
    "PLA": {
        "nozzle_temp": 210, "bed_temp": 60, "cooling": 100,
        "warp_risk": "low", "max_speed": 80, "retraction": 6,
        "retraction_speed": 45, "density": 1.24,
        "description": "The easiest filament to print. Perfect for beginners, prototypes and decorative models.",
        "beginner_friendly": True, "needs_enclosure": False, "food_safe": False,
        "flexible": False, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Easiest to print", "No warp", "Biodegradable", "Sharp detail", "Cheap"],
        "cons": ["Brittle under stress", "Softens at 60C", "UV sensitive"],
        "best_for": "Prototypes, display models, low-stress parts",
        "brands": ["Hatchbox PLA", "eSUN PLA+", "Polymaker PolyLite", "Prusament PLA"],
        "dry_temp": 50, "dry_time": 4, "color": "#5DCAA5", "difficulty": 1,
        "community_tips": ["PLA prints best with a clean PEI sheet — no glue needed.", "If bridging looks bad, increase cooling fan to 100% and slow down 20%.", "Store PLA in a zip-lock bag with silica gel — it lasts years.", "PLA+ is worth the small price difference for functional parts.", "First layer at 20mm/s gives the best bed adhesion."]
    },
    "PLA+": {
        "nozzle_temp": 215, "bed_temp": 60, "cooling": 100,
        "warp_risk": "low", "max_speed": 75, "retraction": 6,
        "retraction_speed": 45, "density": 1.24,
        "description": "Improved PLA with better toughness. Almost as easy as regular PLA.",
        "beginner_friendly": True, "needs_enclosure": False, "food_safe": False,
        "flexible": False, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Tougher than PLA", "Easy to print", "Low warp", "Good detail"],
        "cons": ["Slightly harder to tune", "Not heat resistant", "UV sensitive"],
        "best_for": "Functional prototypes, everyday parts",
        "brands": ["eSUN PLA+", "Polymaker PolyMax PLA", "Hatchbox PLA"],
        "dry_temp": 50, "dry_time": 4, "color": "#4DBBA5", "difficulty": 1,
        "community_tips": ["PLA+ needs 5C more than regular PLA.", "Great for snap-fit parts that would crack with regular PLA.", "Slower speeds give noticeably better layer adhesion.", "Some brands string more than regular PLA — tune retraction carefully."]
    },
    "PETG": {
        "nozzle_temp": 235, "bed_temp": 80, "cooling": 50,
        "warp_risk": "low", "max_speed": 60, "retraction": 7,
        "retraction_speed": 40, "density": 1.27,
        "description": "Strong, slightly flexible, food-safe. The best all-rounder for functional parts.",
        "beginner_friendly": True, "needs_enclosure": False, "food_safe": True,
        "flexible": False, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Strong and tough", "Food safe", "Low warp", "Chemical resistant"],
        "cons": ["Strings easily", "Needs dry storage", "Tricky first layer"],
        "best_for": "Functional parts, containers, mechanical components",
        "brands": ["Prusament PETG", "Polymaker PolyLite PETG", "eSUN PETG"],
        "dry_temp": 65, "dry_time": 6, "color": "#378ADD", "difficulty": 2,
        "community_tips": ["PETG sticks too well to PEI — use a thin layer of glue stick as release agent.", "Enable combing in your slicer to massively reduce stringing.", "Dry PETG before every print — it absorbs moisture very fast.", "Lower cooling to 30-50% for stronger layer bonding."]
    },
    "ABS": {
        "nozzle_temp": 240, "bed_temp": 100, "cooling": 20,
        "warp_risk": "high", "max_speed": 60, "retraction": 5,
        "retraction_speed": 40, "density": 1.04,
        "description": "Heat resistant and tough but challenging. Needs enclosure and ventilation.",
        "beginner_friendly": False, "needs_enclosure": True, "food_safe": False,
        "flexible": False, "heat_resistant": True, "outdoor_safe": False,
        "pros": ["Heat resistant up to 100C", "Impact resistant", "Sandable", "Lightweight"],
        "cons": ["High warp risk", "Needs enclosure", "Toxic fumes", "Hard for beginners"],
        "best_for": "Car parts, enclosures, high-temperature environments",
        "brands": ["Hatchbox ABS", "eSUN ABS+", "Polymaker PolyLite ABS"],
        "dry_temp": 80, "dry_time": 4, "color": "#D85A30", "difficulty": 4,
        "community_tips": ["ABS juice on glass bed gives excellent adhesion.", "Enclosure temperature should reach at least 45C.", "Never breathe ABS fumes — always print in ventilated room.", "Acetone smoothing after printing gives a professional glossy finish."]
    },
    "ASA": {
        "nozzle_temp": 245, "bed_temp": 100, "cooling": 20,
        "warp_risk": "high", "max_speed": 55, "retraction": 5,
        "retraction_speed": 40, "density": 1.07,
        "description": "Like ABS but UV and weather resistant. The only good choice for outdoor parts.",
        "beginner_friendly": False, "needs_enclosure": True, "food_safe": False,
        "flexible": False, "heat_resistant": True, "outdoor_safe": True,
        "pros": ["UV resistant", "Weather resistant", "Heat resistant", "Strong"],
        "cons": ["High warp risk", "Needs enclosure", "Fumes", "Expensive"],
        "best_for": "Outdoor parts, garden tools, automotive exterior",
        "brands": ["Prusament ASA", "Polymaker PolyLite ASA", "eSUN ASA"],
        "dry_temp": 80, "dry_time": 4, "color": "#7F77DD", "difficulty": 4,
        "community_tips": ["ASA behaves very similarly to ABS — ABS profiles are a good starting point.", "PEI sheet with glue stick works well for ASA.", "ASA is worth the extra cost over ABS for anything outside.", "Keep cooling very low — ASA layer adhesion suffers with high fan speeds."]
    },
    "TPU": {
        "nozzle_temp": 225, "bed_temp": 40, "cooling": 80,
        "warp_risk": "low", "max_speed": 25, "retraction": 2,
        "retraction_speed": 20, "density": 1.21,
        "description": "Flexible rubber-like material. Perfect for phone cases, gaskets and grips.",
        "beginner_friendly": False, "needs_enclosure": False, "food_safe": False,
        "flexible": True, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Flexible", "Impact absorbing", "Chemical resistant", "Waterproof"],
        "cons": ["Very slow", "Strings badly", "Hard to retract", "Difficult to tune"],
        "best_for": "Phone cases, gaskets, flexible joints, grips",
        "brands": ["Polymaker PolyFlex TPU", "Ninjatek Cheetah", "eSUN TPU"],
        "dry_temp": 50, "dry_time": 4, "color": "#D4537E", "difficulty": 3,
        "community_tips": ["Direct drive printers handle TPU dramatically better than Bowden.", "Disable retraction almost completely.", "Print slower than you think — 20-30mm/s gives best results.", "TPU sticks well to PEI without any adhesion helpers."]
    },
    "Nylon": {
        "nozzle_temp": 250, "bed_temp": 80, "cooling": 30,
        "warp_risk": "high", "max_speed": 50, "retraction": 6,
        "retraction_speed": 40, "density": 1.14,
        "description": "Extremely strong and wear resistant. Used in engineering and industrial applications.",
        "beginner_friendly": False, "needs_enclosure": True, "food_safe": False,
        "flexible": False, "heat_resistant": True, "outdoor_safe": False,
        "pros": ["Very strong", "Wear resistant", "Flexible yet tough", "Chemical resistant"],
        "cons": ["Absorbs moisture fast", "High warp", "Needs enclosure", "Expensive"],
        "best_for": "Gears, bearings, hinges, industrial parts",
        "brands": ["Taulman Nylon 645", "Polymaker PolyMide", "Prusament Nylon"],
        "dry_temp": 90, "dry_time": 12, "color": "#E8A030", "difficulty": 5,
        "community_tips": ["Nylon MUST be bone dry — print immediately after drying.", "Garolite (FR4) sheet is the best bed surface for Nylon.", "Nylon is self-lubricating — ideal for gears.", "Chamber temperature of 50C+ dramatically reduces warping."]
    },
    "Wood PLA": {
        "nozzle_temp": 200, "bed_temp": 55, "cooling": 100,
        "warp_risk": "low", "max_speed": 40, "retraction": 5,
        "retraction_speed": 40, "density": 1.20,
        "description": "PLA mixed with wood fibres. Gives a real wood look and feel when sanded and stained.",
        "beginner_friendly": True, "needs_enclosure": False, "food_safe": False,
        "flexible": False, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Wood-like appearance", "Sandable and stainable", "Easy to print", "Unique aesthetic"],
        "cons": ["Clogs 0.4mm nozzles", "Weaker than PLA", "Expensive", "Limited uses"],
        "best_for": "Decorative items, art, figurines, architectural models",
        "brands": ["Hatchbox Wood PLA", "eSUN Wood PLA", "Polymaker PolyWood"],
        "dry_temp": 50, "dry_time": 4, "color": "#A0714F", "difficulty": 2,
        "community_tips": ["Use a 0.6mm or larger nozzle to avoid clogging.", "Higher temperatures (210-220C) give a darker wood colour.", "Sand with 120 then 240 grit before staining.", "Water-based wood stains work beautifully on Wood PLA."]
    },
    "Carbon Fibre PLA": {
        "nozzle_temp": 220, "bed_temp": 60, "cooling": 100,
        "warp_risk": "low", "max_speed": 50, "retraction": 5,
        "retraction_speed": 40, "density": 1.30,
        "description": "PLA reinforced with carbon fibre. Extremely stiff and lightweight with a premium look.",
        "beginner_friendly": False, "needs_enclosure": False, "food_safe": False,
        "flexible": False, "heat_resistant": False, "outdoor_safe": False,
        "pros": ["Very stiff and rigid", "Lightweight", "Premium matte finish", "Dimensionally stable"],
        "cons": ["Wears brass nozzles fast", "Brittle", "Expensive", "Needs hardened nozzle"],
        "best_for": "Stiff structural parts, drone frames, lightweight brackets",
        "brands": ["Polymaker PolyMax CF", "Prusament CF PLA", "Bambu Lab CF PLA"],
        "dry_temp": 50, "dry_time": 4, "color": "#444455", "difficulty": 3,
        "community_tips": ["Hardened steel nozzle is mandatory.", "0.6mm nozzle recommended for better flow.", "CF PLA is very stiff but brittle — not good for parts that flex.", "The matte black finish looks extremely premium."]
    }
}

NOZZLE_LAYER = {
    "0.2": {"min": 0.08, "max": 0.15, "default": 0.1},
    "0.4": {"min": 0.1, "max": 0.28, "default": 0.2},
    "0.6": {"min": 0.2, "max": 0.45, "default": 0.3},
    "0.8": {"min": 0.3, "max": 0.6, "default": 0.4}
}

PRINTER_PROFILES = {
    "bedslinger": {"name": "Bed slinger (Ender 3, CR-10)", "speed_multiplier": 1.0, "max_speed": 80, "notes": "Keep speeds moderate. High speeds cause ringing on bed slingers."},
    "corexY": {"name": "CoreXY (Bambu, Voron, Prusa XL)", "speed_multiplier": 1.8, "max_speed": 200, "notes": "CoreXY handles much higher speeds with minimal ringing."},
    "delta": {"name": "Delta (Anycubic Kossel)", "speed_multiplier": 1.2, "max_speed": 100, "notes": "Great for tall objects. Keep retraction tuned carefully."},
    "direct": {"name": "Direct drive (Prusa MK4)", "speed_multiplier": 1.3, "max_speed": 120, "notes": "Direct drive handles flexible filaments much better than Bowden."}
}

PRINTER_FILAMENT_COMPATIBILITY = {
    "bedslinger": ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "Wood PLA", "Carbon Fibre PLA"],
    "corexY": ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "Nylon", "Wood PLA", "Carbon Fibre PLA"],
    "delta": ["PLA", "PLA+", "PETG", "ABS", "ASA", "Wood PLA"],
    "direct": ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "Nylon", "Wood PLA", "Carbon Fibre PLA"]
}

PRINTER_WARNINGS = {
    ("bedslinger", "TPU"): "Bowden tube makes TPU very difficult. Use slow speeds and minimal retraction.",
    ("bedslinger", "Nylon"): "Nylon needs an enclosure mod and active chamber heating on bed slingers.",
    ("bedslinger", "Carbon Fibre PLA"): "Use a 0.6mm hardened steel nozzle — CF destroys brass nozzles in hours.",
    ("delta", "TPU"): "Long Bowden path on delta printers makes TPU nearly impossible.",
    ("delta", "Nylon"): "Nylon needs enclosure — very difficult on stock delta printers.",
    ("corexY", "Carbon Fibre PLA"): "Use a hardened steel nozzle. CF is abrasive.",
    ("direct", "Carbon Fibre PLA"): "Use a hardened steel nozzle. CF is abrasive."
}

COMMON_PRINTS = {
    "phone_case": {"name": "Phone case", "emoji": "📱", "purpose": "flexible", "size": "small", "priority": "strongest", "filament": "TPU", "notes": "TPU is the only real choice — flexible and shock absorbing.", "printer": "direct"},
    "vase": {"name": "Decorative vase", "emoji": "🏺", "purpose": "visual", "size": "medium", "priority": "smoothest", "filament": "PLA", "notes": "Use vase mode in your slicer for a seamless spiral.", "printer": "bedslinger"},
    "bracket": {"name": "Structural bracket", "emoji": "🔩", "purpose": "functional", "size": "small", "priority": "strongest", "filament": "PETG", "notes": "PETG gives best strength with minimal warp risk.", "printer": "bedslinger"},
    "gear": {"name": "Mechanical gear", "emoji": "⚙️", "purpose": "functional", "size": "small", "priority": "strongest", "filament": "Nylon", "notes": "Nylon is self-lubricating — perfect for gears.", "printer": "corexY"},
    "outdoor_clip": {"name": "Outdoor clip", "emoji": "🌤️", "purpose": "functional", "size": "small", "priority": "balanced", "filament": "ASA", "notes": "ASA handles UV and rain — the only outdoor filament.", "printer": "bedslinger"},
    "figurine": {"name": "Figurine", "emoji": "🗿", "purpose": "visual", "size": "medium", "priority": "smoothest", "filament": "PLA", "notes": "Use tree supports and 0.1mm layers for max detail.", "printer": "corexY"},
    "cable_organiser": {"name": "Cable organiser", "emoji": "🔌", "purpose": "prototype", "size": "small", "priority": "fastest", "filament": "PLA", "notes": "Print fast — detail does not matter here.", "printer": "bedslinger"},
    "enclosure": {"name": "Electronics enclosure", "emoji": "🖥️", "purpose": "functional", "size": "medium", "priority": "strongest", "filament": "ABS", "notes": "ABS handles heat from electronics safely.", "printer": "bedslinger"},
    "drone_frame": {"name": "Drone frame part", "emoji": "🚁", "purpose": "functional", "size": "medium", "priority": "strongest", "filament": "Carbon Fibre PLA", "notes": "CF PLA is stiff and light — ideal for drones.", "printer": "corexY"},
    "art_piece": {"name": "Wood art piece", "emoji": "🪵", "purpose": "visual", "size": "medium", "priority": "smoothest", "filament": "Wood PLA", "notes": "Sand and stain after printing for real wood finish.", "printer": "bedslinger"},
    "gasket": {"name": "Rubber gasket", "emoji": "⭕", "purpose": "flexible", "size": "small", "priority": "balanced", "filament": "TPU", "notes": "TPU creates excellent waterproof flexible gaskets.", "printer": "direct"},
    "tool_handle": {"name": "Tool handle grip", "emoji": "🔧", "purpose": "functional", "size": "small", "priority": "strongest", "filament": "TPU", "notes": "Soft TPU grip is comfortable and non-slip.", "printer": "direct"},
    "plant_pot": {"name": "Plant pot", "emoji": "🌱", "purpose": "visual", "size": "medium", "priority": "balanced", "filament": "PLA", "notes": "PLA biodegrades slowly — fine for indoor plants.", "printer": "bedslinger"},
    "hinge": {"name": "Living hinge", "emoji": "🚪", "purpose": "flexible", "size": "small", "priority": "balanced", "filament": "PETG", "notes": "PETG flex hinges survive thousands of cycles.", "printer": "bedslinger"},
    "rc_part": {"name": "RC car body part", "emoji": "🏎️", "purpose": "functional", "size": "medium", "priority": "strongest", "filament": "PLA+", "notes": "PLA+ gives good impact resistance for RC parts.", "printer": "bedslinger"},
    "wall_mount": {"name": "Wall mount / hook", "emoji": "🪝", "purpose": "functional", "size": "small", "priority": "strongest", "filament": "PETG", "notes": "PETG handles sustained load better than PLA.", "printer": "bedslinger"},
    "cookie_cutter": {"name": "Cookie cutter", "emoji": "🍪", "purpose": "visual", "size": "small", "priority": "fastest", "filament": "PLA", "notes": "PLA is food-adjacent safe for dry foods.", "printer": "bedslinger"},
    "architectural_model": {"name": "Architectural model", "emoji": "🏛️", "purpose": "visual", "size": "large", "priority": "smoothest", "filament": "PLA", "notes": "Fine detail at 0.1mm layers for presentation models.", "printer": "corexY"},
    "cable_chain": {"name": "Cable chain", "emoji": "⛓️", "purpose": "functional", "size": "medium", "priority": "strongest", "filament": "PETG", "notes": "PETG survives repeated flexing without cracking.", "printer": "bedslinger"},
    "fan_duct": {"name": "Printer fan duct", "emoji": "💨", "purpose": "functional", "size": "small", "priority": "strongest", "filament": "ABS", "notes": "ABS handles the heat near the hotend safely.", "printer": "bedslinger"},
}

TROUBLESHOOTING = {
    "warping": {"problem": "Print lifting off bed or warping at corners", "emoji": "🌡️", "causes": ["Bed not level", "Bed temp too low", "No brim", "Cooling too high for first layers", "Damp filament"], "fixes": ["Level your bed carefully", "Increase bed temp by 5C", "Add 8mm brim in slicer", "Turn fan off for first 3 layers", "Dry your filament"]},
    "stringing": {"problem": "Thin strings of plastic between parts", "emoji": "🕸️", "causes": ["Retraction too low", "Temp too high", "Travel speed too slow", "Wet filament"], "fixes": ["Increase retraction by 0.5mm steps", "Lower temp by 5C", "Increase travel speed to 150mm/s", "Enable combing mode", "Dry filament overnight"]},
    "layer_splitting": {"problem": "Layers separating or cracking apart", "emoji": "💔", "causes": ["Temp too low", "Speed too fast", "Layer height too thick", "Damp filament"], "fixes": ["Increase temp by 5C", "Reduce speed by 20%", "Max layer height is 75% of nozzle diameter", "Check for moisture — popping sounds means wet filament"]},
    "clogged_nozzle": {"problem": "Filament not coming out or under-extrusion", "emoji": "🚫", "causes": ["Burnt filament", "Wrong temperature", "Filament ground down", "Partial clog"], "fixes": ["Cold pull — heat to 200C, cool to 90C, pull firmly", "Heat 10C above normal and push through manually", "Clean extruder gear", "Replace nozzle"]},
    "bad_first_layer": {"problem": "First layer not sticking or looking rough", "emoji": "📐", "causes": ["Nozzle too far from bed", "Dirty bed", "Wrong bed temp", "Speed too fast"], "fixes": ["Re-level — nozzle should grip paper with slight resistance", "Clean with isopropyl alcohol", "Max 20mm/s for first layer", "Use glue stick on glass beds"]},
    "overheating": {"problem": "Print looks melted, droopy or has blobs", "emoji": "🔥", "causes": ["Temp too high", "Speed too slow", "Cooling not working", "Small object cooling slowly"], "fixes": ["Lower temp by 5C", "Increase speed slightly", "Check fan is spinning", "Set minimum layer time to 10 seconds"]},
    "elephant_foot": {"problem": "Bottom layers wider than the rest of the print", "emoji": "🐘", "causes": ["Nozzle too close", "First layer squish too high", "Bed temp too high"], "fixes": ["Raise Z offset slightly", "Reduce first layer squish", "Lower bed temp by 5C", "Enable elephant foot compensation in slicer"]}
}

SLICER_GUIDE = {
    "Cura": {"layer_height": "Quality > Layer Height", "speed": "Speed > Print Speed", "infill": "Infill > Infill Density", "walls": "Walls > Wall Line Count", "temp": "Material > Printing Temperature", "bed_temp": "Material > Build Plate Temperature", "cooling": "Cooling > Fan Speed", "retraction": "Travel > Retraction Distance", "tip": "Enable Combing Mode set to Within Infill to reduce stringing significantly."},
    "PrusaSlicer": {"layer_height": "Print Settings > Layers > Layer Height", "speed": "Print Settings > Speed > Perimeters", "infill": "Print Settings > Infill > Fill Density", "walls": "Print Settings > Layers > Perimeters", "temp": "Filament Settings > Filament > Nozzle Temperature", "bed_temp": "Filament Settings > Filament > Bed Temperature", "cooling": "Filament Settings > Cooling > Fan Speed", "retraction": "Printer Settings > Extruder > Retraction Length", "tip": "Use Detect Thin Walls for small detailed parts to avoid gaps in narrow features."},
    "Bambu Studio": {"layer_height": "Process > Quality > Layer Height", "speed": "Process > Speed > Print Speed", "infill": "Process > Strength > Sparse Infill Density", "walls": "Process > Strength > Wall Loops", "temp": "Filament > Nozzle Temperature", "bed_temp": "Filament > Bed Temperature", "cooling": "Filament > Cooling > Fan Speed", "retraction": "Printer > Extruder > Retraction Length", "tip": "Run Flow Dynamics Calibration before printing PETG for best results."},
    "OrcaSlicer": {"layer_height": "Process > Quality > Layer Height", "speed": "Process > Speed > Print Speed", "infill": "Process > Strength > Sparse Infill Density", "walls": "Process > Strength > Wall Loops", "temp": "Filament > Nozzle Temperature", "bed_temp": "Filament > Bed Temperature", "cooling": "Filament > Cooling > Fan Speed", "retraction": "Printer > Extruder > Retraction Length", "tip": "OrcaSlicer has built-in calibration tools — run PA and flow calibration for any new filament."}
}

CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar"},
    "EUR": {"symbol": "€", "name": "Euro"},
    "GBP": {"symbol": "£", "name": "British Pound"},
    "QAR": {"symbol": "QR", "name": "Qatari Riyal"},
    "AED": {"symbol": "AED", "name": "UAE Dirham"},
    "SAR": {"symbol": "SAR", "name": "Saudi Riyal"},
    "INR": {"symbol": "₹", "name": "Indian Rupee"},
    "CAD": {"symbol": "CA$", "name": "Canadian Dollar"},
    "AUD": {"symbol": "A$", "name": "Australian Dollar"},
    "JPY": {"symbol": "¥", "name": "Japanese Yen"},
}

GLOSSARY = [
    {"term": "FDM", "def": "Fused Deposition Modelling — the most common 3D printing method. Melts plastic filament and deposits it layer by layer."},
    {"term": "Layer height", "def": "How thick each printed layer is in mm. Thinner = smoother surface but longer print time."},
    {"term": "Infill", "def": "The internal structure inside your print. 0% is hollow, 100% is completely solid. Most parts only need 15-40%."},
    {"term": "Retraction", "def": "Pulling filament back into the nozzle during travel moves to prevent strings and blobs."},
    {"term": "Bed adhesion", "def": "How well your print sticks to the build plate. Critical for preventing warping and failed prints."},
    {"term": "Supports", "def": "Temporary structures printed under overhangs to hold them up during printing. Removed after."},
    {"term": "Overhang", "def": "Part of your model that sticks out horizontally without anything below it. Over 45 degrees usually needs supports."},
    {"term": "Bridging", "def": "Printing across a gap with no support below. Works up to about 50-80mm with good cooling."},
    {"term": "Stringing", "def": "Thin threads of plastic left between parts of your print caused by oozing during travel moves."},
    {"term": "Warping", "def": "When corners or edges of a print lift off the bed due to thermal contraction as the material cools."},
    {"term": "Brim", "def": "Extra lines printed around the base of your model to improve bed adhesion and prevent warping."},
    {"term": "Raft", "def": "A thick sacrificial base printed under your model for extra adhesion. Slower and uses more filament than a brim."},
    {"term": "Nozzle", "def": "The small metal tip filament is extruded through. Standard size is 0.4mm. Larger = faster, smaller = more detail."},
    {"term": "Extruder", "def": "The mechanism that pushes filament into the hotend. Can be Bowden (remote) or direct drive (on the printhead)."},
    {"term": "Hotend", "def": "The heated assembly that melts filament. Consists of heater block, heat break, and nozzle."},
    {"term": "PEI", "def": "Polyetherimide — a popular bed surface coating that provides excellent adhesion when hot and releases prints when cool."},
    {"term": "Bowden", "def": "A setup where the extruder motor is separate from the printhead, connected by a PTFE tube."},
    {"term": "Direct drive", "def": "Extruder motor mounted directly on the printhead. Heavier but much better for flexible filaments."},
    {"term": "CoreXY", "def": "A printer motion system where both X and Y motors work together. Allows very high speeds."},
    {"term": "Slicing", "def": "Converting a 3D model into layers and generating the printer instructions (G-code)."},
    {"term": "G-code", "def": "The machine language your printer reads. Contains instructions for every movement, temperature, and fan speed."},
    {"term": "First layer", "def": "The most critical layer of any print. Gets squished onto the bed to create strong adhesion for all layers above."},
    {"term": "Z offset", "def": "The distance between the nozzle and the bed at the home position. Critical for first layer quality."},
    {"term": "Flow rate", "def": "How much plastic is extruded relative to what the slicer expects. Under 100% = under-extrusion."},
    {"term": "Vase mode", "def": "A slicer setting that prints the outer wall as one continuous spiral. Creates seamless hollow objects."},
    {"term": "Tree supports", "def": "Smart supports that grow like tree branches, touching the model minimally. Easier to remove than normal supports."},
    {"term": "Elephant foot", "def": "When the bottom layers are wider than the rest of the print. Caused by nozzle too close to bed."},
    {"term": "Cold pull", "def": "A nozzle cleaning technique — heat to print temp, cool to 90C, pull firmly. Drags debris out of the nozzle."},
    {"term": "PA / Pressure Advance", "def": "A firmware setting that compensates for filament pressure buildup in the nozzle, reducing blobs at corners."},
    {"term": "Volumetric flow", "def": "The amount of filament pushed through the nozzle per second. The real limit of print speed."}
]

BED_ADHESION = [
    {"surface": "PEI Sheet", "emoji": "🟠", "best_for": ["PLA", "PLA+", "PETG", "ABS", "ASA", "TPU"], "avoid": [], "tip": "The gold standard. Sticks well when hot, releases when cool. Clean with IPA regularly.", "glue_needed": False, "difficulty": "Easy"},
    {"surface": "Glass (plain)", "emoji": "🔵", "best_for": ["PLA", "PLA+"], "avoid": ["ABS", "ASA", "Nylon"], "tip": "Clean with IPA and print at 60C. PLA releases cleanly when cool. Very flat surface.", "glue_needed": False, "difficulty": "Easy"},
    {"surface": "Glass + glue stick", "emoji": "🟢", "best_for": ["PLA", "PLA+", "PETG", "ABS", "ASA"], "avoid": [], "tip": "Thin layer of Pritt Stick or similar. Excellent adhesion. PETG needs glue to prevent surface damage.", "glue_needed": True, "difficulty": "Easy"},
    {"surface": "Glass + hairspray", "emoji": "🟡", "best_for": ["PLA", "ABS", "ASA"], "avoid": ["PETG"], "tip": "Aquanet or cheap supermarket hairspray works. Spray thin, let dry before printing.", "glue_needed": True, "difficulty": "Easy"},
    {"surface": "BuildTak", "emoji": "🟤", "best_for": ["PLA", "PLA+", "PETG"], "avoid": ["ABS", "Nylon"], "tip": "Aggressive adhesion — good for PLA. PETG can bond permanently if too hot.", "glue_needed": False, "difficulty": "Medium"},
    {"surface": "Garolite (FR4)", "emoji": "⚫", "best_for": ["Nylon"], "avoid": ["PLA", "PETG"], "tip": "The only reliable surface for Nylon. Nylon bonds strongly and releases cleanly.", "glue_needed": False, "difficulty": "Medium"},
    {"surface": "Kapton tape", "emoji": "🟠", "best_for": ["ABS", "ASA"], "avoid": ["PLA"], "tip": "Apply smoothly with no bubbles. ABS adheres well especially with ABS juice.", "glue_needed": False, "difficulty": "Hard"},
]

SUPPORTS_GUIDE = {
    "when": [
        {"rule": "Over 45 degrees overhang", "detail": "Anything past 45 degrees from vertical will need support. Most slicers detect this automatically."},
        {"rule": "Horizontal holes facing up", "detail": "Circular holes on the top face of a print need supports unless they are small (under 15mm)."},
        {"rule": "Bridges over 60mm", "detail": "Shorter bridges (under 60mm) can print unsupported with good cooling. Longer ones need supports."},
        {"rule": "Thin floating features", "detail": "Anything that starts mid-air and isn't connected to the base needs a support structure underneath."},
    ],
    "types": [
        {"name": "Normal supports", "emoji": "📦", "pros": ["Simple", "Works everywhere", "Fast to generate"], "cons": ["Hard to remove", "Leaves marks", "Uses lots of material"], "best_for": "Simple geometries where supports won't be trapped"},
        {"name": "Tree supports", "emoji": "🌳", "pros": ["Easy to remove", "Less material", "Minimal surface marks"], "cons": ["Slower to generate", "Can tip over on tall prints"], "best_for": "Organic shapes, figurines, complex geometry"},
        {"name": "Support enforcers", "emoji": "🎯", "pros": ["Supports only where you specify", "Saves material", "Better surface finish"], "cons": ["Manual placement required", "Takes more setup time"], "best_for": "When auto-detect puts supports in wrong places"},
        {"name": "Raft", "emoji": "🛶", "pros": ["Maximum adhesion", "Levels out uneven beds"], "cons": ["Hard to remove", "Rough bottom surface", "Uses lots of material"], "best_for": "Very small contact area prints, warping-prone materials"},
    ],
    "settings": [
        {"setting": "Support density", "value": "15-20%", "detail": "Higher density = stronger support but harder to remove. 15% is usually enough."},
        {"setting": "Z distance", "value": "0.2mm", "detail": "Gap between support top and model. Too small = fused. Too large = bad overhang quality."},
        {"setting": "Interface layers", "value": "2 layers", "detail": "Denser layers at the top of support for better overhang quality. Highly recommended."},
        {"setting": "Support pattern", "value": "Lines or Zig-Zag", "detail": "Lines are easiest to remove. Grid is stronger but harder to pull off."},
    ]
}

DRYING_GUIDE = [
    {"filament": "PLA", "color": "#5DCAA5", "temp": "45-50°C", "time": "4-6 hrs", "signs": "Popping/crackling sounds, rough surface texture, weak layer adhesion", "storage": "Zip-lock bag with silica gel. PLA is fairly moisture resistant but still benefits from dry storage.", "method": "Food dehydrator at 45C is ideal. Oven with door cracked works. Avoid temps above 55C."},
    {"filament": "PLA+", "color": "#4DBBA5", "temp": "45-50°C", "time": "4-6 hrs", "signs": "Popping sounds, inconsistent extrusion, bubbles in filament", "storage": "Same as PLA. Zip-lock with silica gel.", "method": "Food dehydrator at 45C. Same process as regular PLA."},
    {"filament": "PETG", "color": "#378ADD", "temp": "60-65°C", "time": "6-8 hrs", "signs": "Stringing much worse than normal, surface looks glossy/bubbly, weak prints", "storage": "PETG absorbs moisture fast. Dry box or sealed container with silica gel between prints.", "method": "Food dehydrator or oven at 60-65C. Dry before every print if stored open."},
    {"filament": "ABS", "color": "#D85A30", "temp": "75-80°C", "time": "4-6 hrs", "signs": "Popping, poor layer adhesion, warping worse than usual, rough surface", "storage": "Sealed container with fresh silica gel.", "method": "Oven at 75-80C with door slightly open. Food dehydrator on highest setting."},
    {"filament": "ASA", "color": "#7F77DD", "temp": "75-80°C", "time": "4-6 hrs", "signs": "Same as ABS — popping sounds, rough surface, increased warping", "storage": "Sealed container. Similar moisture sensitivity to ABS.", "method": "Same as ABS — oven at 75-80C."},
    {"filament": "TPU", "color": "#D4537E", "temp": "45-50°C", "time": "4-6 hrs", "signs": "Bubbling in prints, rough surface, popping sounds", "storage": "Sealed bag. TPU absorbs moisture at moderate rate.", "method": "Food dehydrator at 45C. Keep temp low to avoid deforming the flexible filament."},
    {"filament": "Nylon", "color": "#E8A030", "temp": "85-90°C", "time": "12-24 hrs", "signs": "Very aggressive stringing, extremely weak prints, bubbling, popping.", "storage": "Print directly from a dry box. Nylon must stay sealed with fresh silica gel at ALL times.", "method": "Oven at 85-90C for 12-24 hours. Print immediately after drying."},
    {"filament": "Wood PLA", "color": "#A0714F", "temp": "45-50°C", "time": "4-6 hrs", "signs": "Same as PLA — popping, rough surface", "storage": "Same as PLA. Zip-lock with silica gel.", "method": "Food dehydrator at 45C. Same as regular PLA."},
    {"filament": "Carbon Fibre PLA", "color": "#444455", "temp": "45-50°C", "time": "4-6 hrs", "signs": "Popping, rough surface, weak layer adhesion", "storage": "Sealed bag with silica gel. Similar to regular PLA.", "method": "Food dehydrator at 45C. Same process as regular PLA."},
]

FIRST_LAYER_WIZARD = [
    {"id": "q1", "question": "What does your first layer look like?", "options": [
        {"text": "Not sticking at all — peeling right off", "next": "q2"},
        {"text": "Sticking but looks rough and bubbly", "next": "q4"},
        {"text": "Looks squished and too flat", "next": "q5"},
        {"text": "Looks fine but warping at corners", "next": "q6"},
        {"text": "First few layers fine then print detaches", "next": "q7"}
    ]},
    {"id": "q2", "question": "Is the filament sticking to the nozzle instead of the bed?", "options": [
        {"text": "Yes — curling around the nozzle", "next": "q3"},
        {"text": "No — just not bonding to the bed at all", "fix": "Your nozzle is too far from the bed. Lower Z offset by 0.05mm increments until the first layer squishes slightly. Also clean bed with isopropyl alcohol before every print."}
    ]},
    {"id": "q3", "question": "What is your bed temperature set to?", "options": [
        {"text": "Below 50C for PLA / Below 70C for PETG", "fix": "Bed temperature is too low. Set PLA bed to 60C, PETG to 80C, ABS/ASA to 100C. Wait for full heat soak (5 minutes) before printing."},
        {"text": "Temperature looks correct", "fix": "Nozzle is too far from bed AND bed is not clean enough. Re-level carefully, clean with IPA, and lower Z offset slightly."}
    ]},
    {"id": "q4", "question": "Did you dry your filament recently?", "options": [
        {"text": "No — it has been sitting out", "fix": "Wet filament causes bubbling, rough texture and popping sounds. Dry your filament: PLA at 50C for 4h, PETG at 65C for 6h, ABS at 80C for 4h in a food dehydrator or oven."},
        {"text": "Yes it is freshly dried", "fix": "Rough first layer with dry filament means print speed is too fast. Reduce first layer speed to 15-20mm/s. Also check nozzle is not too close to bed."}
    ]},
    {"id": "q5", "question": "Are the lines merging together and losing detail?", "options": [
        {"text": "Yes — completely flat and merged", "fix": "Z offset is too low — nozzle is too close to the bed. Raise Z offset by 0.05mm steps until lines are distinct but still slightly squished."},
        {"text": "Slightly flat but looks okay", "fix": "This is actually correct! A slight squish on the first layer is good for adhesion. If the bottom surface looks rough when removed, raise Z offset very slightly."}
    ]},
    {"id": "q6", "question": "What filament are you using?", "options": [
        {"text": "ABS or ASA", "fix": "ABS and ASA warp heavily without an enclosure. Add a large brim (10mm+), turn off all cooling for the first 5 layers, and use ABS juice or glue stick on the bed."},
        {"text": "PLA or PETG", "fix": "PLA and PETG should not warp much. Check: 1) First layer speed under 20mm/s, 2) Cooling fan off for first 3 layers, 3) Bed clean with IPA, 4) Add a 5mm brim in slicer."}
    ]},
    {"id": "q7", "question": "At what layer does it detach?", "options": [
        {"text": "Around layer 3-10", "fix": "Temperature shift is causing delamination. Slow down overall speed, increase bed temp by 5C, add a brim, and make sure there are no drafts near the printer."},
        {"text": "Much later in the print", "fix": "This is almost always warping from a tall print cooling unevenly. Use an enclosure, reduce cooling fan, add a brim, and for ABS/ASA use ABS juice on the bed."}
    ]}
]

MATERIAL_QUIZ = [
    {"id": "mq1", "question": "What are you mainly printing?", "options": [
        {"text": "Functional parts that need to be strong", "next": "mq2"},
        {"text": "Display models or decorative items", "next": "mq5"},
        {"text": "Flexible parts like phone cases or gaskets", "result": "TPU"},
        {"text": "Outdoor parts exposed to sun and rain", "result": "ASA"},
    ]},
    {"id": "mq2", "question": "Does it need to handle high temperatures?", "options": [
        {"text": "Yes — near engines, electronics or hot environments", "next": "mq3"},
        {"text": "No — just needs to be mechanically strong", "next": "mq4"},
    ]},
    {"id": "mq3", "question": "Do you have a printer enclosure?", "options": [
        {"text": "Yes I have an enclosure", "result": "ABS"},
        {"text": "No — open frame printer", "result": "PETG"},
    ]},
    {"id": "mq4", "question": "Are you a beginner or experienced?", "options": [
        {"text": "Beginner — I want easy to print", "result": "PLA+"},
        {"text": "Experienced — I want maximum strength", "result": "Nylon"},
        {"text": "Somewhere in between", "result": "PETG"},
    ]},
    {"id": "mq5", "question": "What kind of visual model?", "options": [
        {"text": "Figurines or art with fine detail", "result": "PLA"},
        {"text": "Something with a natural wood look", "result": "Wood PLA"},
        {"text": "Lightweight structural model", "result": "Carbon Fibre PLA"},
        {"text": "Just a quick prototype", "result": "PLA"},
    ]},
]

FAILURE_GALLERY = [
    {"name": "Spaghetti print", "emoji": "🍝", "description": "Print detached and extruder kept printing in mid-air creating a mess of spaghetti-like filament everywhere.", "causes": ["First layer adhesion failure", "Bed not level", "Print knocked off by nozzle"], "fixes": ["Re-level bed carefully", "Increase first layer temperature by 5C", "Add brim for better adhesion", "Clean bed with IPA before printing"], "prevention": "Always watch the first 3-5 layers. If anything looks wrong, cancel and fix it."},
    {"name": "Layer shifting", "emoji": "↔️", "description": "Layers suddenly shift to one side mid-print making the object look like it's been pushed sideways.", "causes": ["Print speed too fast", "Loose belts or pulleys", "Extruder hitting print or brim", "Electrical interference"], "fixes": ["Reduce print speed by 30%", "Check and tension all belts", "Check for obstructions on bed", "Check stepper motor connections"], "prevention": "Regularly check belt tension and print at appropriate speeds for your printer."},
    {"name": "Stringing / spider web", "emoji": "🕸️", "description": "Thin strings of plastic connecting different parts of the print like a spider web.", "causes": ["Retraction too low", "Temperature too high", "Travel speed too slow", "Wet filament"], "fixes": ["Increase retraction by 0.5mm steps", "Lower temperature by 5C", "Increase travel speed", "Enable combing mode in slicer"], "prevention": "Store filament sealed with silica gel and tune retraction for each filament brand."},
    {"name": "Warping / lifting corners", "emoji": "⬆️", "description": "Corners of the print lift off the bed during printing, sometimes causing the whole print to detach.", "causes": ["Bed too cold", "No brim used", "Filament shrinks too much on cooling", "Drafts near printer"], "fixes": ["Increase bed temperature", "Add 8mm+ brim", "Use enclosure for ABS/ASA", "Move printer away from fans/windows"], "prevention": "Use PEI sheet, correct bed temperatures, and always add brim for large or ABS prints."},
    {"name": "Under-extrusion", "emoji": "📉", "description": "Gaps and holes in the print walls, layers look weak and incomplete.", "causes": ["Print speed too fast", "Temperature too low", "Partial clog", "Bowden tube gap"], "fixes": ["Reduce speed by 20%", "Increase temperature by 5C", "Do a cold pull to clean nozzle", "Check Bowden tube connection"], "prevention": "Dry your filament, keep nozzle clean, and don't print faster than your hotend can melt."},
    {"name": "Elephant foot", "emoji": "🐘", "description": "The bottom layers are wider than the rest of the print, making it look like it has elephant feet.", "causes": ["Nozzle too close to bed", "First layer squish too high", "Bed temperature too high"], "fixes": ["Raise Z offset by 0.05mm", "Reduce first layer squish in slicer", "Enable elephant foot compensation", "Lower bed temperature slightly"], "prevention": "Calibrate Z offset carefully — the first layer should be squished slightly but not smeared."},
    {"name": "Ghosting / ringing", "emoji": "👻", "description": "Wavy ripple patterns appear on print surface near sharp corners or features.", "causes": ["Print speed too fast", "Loose belts", "Heavy printhead vibrating", "Resonance in frame"], "fixes": ["Reduce print speed", "Tension all belts", "Enable input shaping if available", "Add rubber feet to printer"], "prevention": "Print at appropriate speed for your printer type. CoreXY handles high speeds better than bed slingers."},
    {"name": "Blobs and zits", "emoji": "🫧", "description": "Small blobs or bumps appear on the surface, especially at seam locations.", "causes": ["Too much pressure in nozzle", "Seam placement", "Retraction not tuned", "Over-extrusion"], "fixes": ["Enable pressure advance/linear advance", "Set seam to back of print", "Tune retraction distance", "Calibrate flow rate"], "prevention": "Use pressure advance firmware settings and place seam in least visible location."},
]

PRINTER_CHECKLIST = [
    {"step": 1, "title": "Unbox and inspect", "emoji": "📦", "tasks": ["Check all parts are present against the manual", "Inspect frame for any damage from shipping", "Read the full quickstart guide before touching anything", "Identify all the cables and where they connect"]},
    {"step": 2, "title": "Assemble the printer", "emoji": "🔧", "tasks": ["Follow the official assembly guide step by step", "Do not overtighten screws — snug is enough", "Check all GT2 belts are evenly tensioned (should twang like a guitar string)", "Make sure all eccentric nuts are adjusted so wheels have slight resistance"]},
    {"step": 3, "title": "Level the bed", "emoji": "📐", "tasks": ["Home all axes first", "Manually move nozzle to each corner", "Adjust each corner so nozzle grips a paper sheet with slight resistance", "Check centre of bed too", "Run mesh bed levelling if your printer supports it"]},
    {"step": 4, "title": "Load filament", "emoji": "🧵", "tasks": ["Heat nozzle to filament temperature (PLA = 210C)", "Cut filament at 45 degree angle", "Insert filament until you feel resistance then push until it extrudes", "Purge 50-100mm of filament until colour is consistent", "Check extruder is gripping filament properly"]},
    {"step": 5, "title": "Calibrate Z offset", "emoji": "⬆️", "tasks": ["Start a first layer calibration print", "Watch first layer carefully — should be slightly squished", "Too far: filament not bonding, gaps between lines", "Too close: filament smearing, nozzle scraping", "Adjust in 0.05mm steps until first layer looks perfect"]},
    {"step": 6, "title": "First print", "emoji": "🖨️", "tasks": ["Download a simple calibration cube from Thingiverse", "Use recommended settings for your filament (use OptimalPrint!)", "Watch the entire first layer before walking away", "Check for any unusual sounds or smells", "Measure the printed cube — should be within 0.2mm of 20mm"]},
    {"step": 7, "title": "Fine tune", "emoji": "🎯", "tasks": ["Calibrate extruder E-steps if dimensions are off", "Run temperature tower to find optimal temp for your filament brand", "Run retraction test to minimise stringing", "Print a benchy to test overall quality", "Celebrate your first successful print!"]},
]

BLOG_POSTS = [
    {"title": "5 mistakes every beginner makes (and how to avoid them)", "emoji": "🚫", "category": "Beginner", "read_time": "4 min", "content": "Starting 3D printing is exciting but the first few weeks are full of avoidable mistakes. Here are the five biggest ones and exactly how to avoid them.", "tips": ["Not levelling the bed properly — this causes 80% of beginner failures. Spend 15 minutes getting it right.", "Printing too fast — slow down to 40mm/s for your first prints and work up from there.", "Ignoring filament storage — wet filament causes stringing, blobs and weak parts. Store in sealed bags.", "Giving up after one failed print — every print teaches you something. Check what went wrong and try again.", "Not watching the first layer — stay and watch the first 5 minutes of every print until you trust your printer."]},
    {"title": "PLA vs PETG vs ABS — the ultimate comparison", "emoji": "⚖️", "category": "Materials", "read_time": "6 min", "content": "Choosing the right filament is one of the most important decisions in 3D printing. Here is everything you need to know about the three most popular options.", "tips": ["PLA: easiest to print, great detail, biodegradable. Softens at 60C so avoid hot environments.", "PETG: the best all-rounder. Strong, food-safe, low warp. Slightly harder to dial in than PLA.", "ABS: heat resistant up to 100C and sandable but needs an enclosure and has toxic fumes.", "For beginners, always start with PLA. Move to PETG for functional parts, ABS only if you need heat resistance.", "PLA+ bridges the gap between PLA and PETG — tough enough for most functional parts with PLA ease."]},
    {"title": "How to get perfect first layers every time", "emoji": "📐", "category": "Tips", "read_time": "5 min", "content": "The first layer is the foundation of every print. Get it right and everything else follows. Here is the complete guide to perfect first layers.", "tips": ["Level your bed with a piece of paper — nozzle should grip it with slight resistance at all four corners.", "Clean your bed with isopropyl alcohol before every print — oils from your fingers ruin adhesion.", "Print first layer at 20mm/s maximum — slow and steady wins here.", "First layer temperature should be 5C higher than the rest of the print for better bonding.", "If the first layer looks good, your print will almost certainly succeed — watch it carefully."]},
    {"title": "The complete guide to 3D printing supports", "emoji": "🌳", "category": "Advanced", "read_time": "7 min", "content": "Supports are necessary evil in 3D printing but with the right settings they are easy to remove and leave minimal marks.", "tips": ["Use tree supports for organic shapes and figurines — they touch minimally and remove easily.", "Set support Z distance to 0.2mm — too close and they fuse, too far and overhangs look bad.", "Interface layers make supports much easier to remove — use 2 layers at 0.1mm height.", "Angle your model to reduce supports needed — rotate 45 degrees to eliminate most overhangs.", "Paint-on supports in PrusaSlicer let you add supports exactly where needed and nowhere else."]},
    {"title": "Why your prints are failing and how to fix them", "emoji": "🔧", "category": "Troubleshooting", "read_time": "8 min", "content": "Failed prints are frustrating but every failure has a cause and a fix. Here are the most common failures and exactly how to diagnose and fix them.", "tips": ["Print detaching from bed: level more carefully, increase bed temp, add brim, clean with IPA.", "Stringing: increase retraction, lower temp 5C, enable combing, dry your filament.", "Layer separation: increase temp 5C, reduce speed, check filament for moisture.", "Under-extrusion: partial clog, temperature too low, speed too fast, or grinding extruder.", "Warping: enclosure for ABS/ASA, brim, higher bed temp, no drafts near printer."]},
    {"title": "Smart manufacturing and 3D printing — the future of factories", "emoji": "🏭", "category": "Industry", "read_time": "5 min", "content": "3D printing is transforming manufacturing from mass production to mass customisation. Here is how additive manufacturing is changing industry.", "tips": ["Additive manufacturing reduces material waste by up to 90% compared to subtractive methods.", "Custom tooling and jigs can be 3D printed in hours instead of weeks from a machine shop.", "Small batch production of 1-100 parts is often cheaper with 3D printing than injection moulding.", "Parameter optimisation — exactly what OptimalPrint does — is a key research area in smart manufacturing.", "Carbon fibre, metal, and ceramic 3D printing are bringing additive manufacturing to aerospace and medical."]},
]

def calculate_settings(filament, printer, purpose, nozzle, size, priority, quality_level=5):
    f = FILAMENT_SETTINGS[filament]
    p = PRINTER_PROFILES[printer]
    nl = NOZZLE_LAYER[nozzle]
    quality_ratio = quality_level / 10.0

    if priority == "fastest":
        layer = nl["max"]
    elif priority == "smoothest":
        layer = nl["min"]
    elif priority == "balanced":
        layer = round(nl["max"] - (nl["max"] - nl["min"]) * quality_ratio, 2)
    else:
        layer = nl["default"]

    base_speed = min(f["max_speed"] * p["speed_multiplier"], p["max_speed"])
    if priority == "fastest":
        speed = int(base_speed)
    elif priority == "strongest":
        speed = int(base_speed * 0.55)
    elif priority == "balanced":
        speed = int(base_speed * (1.0 - quality_ratio * 0.4))
    else:
        speed = int(base_speed * 0.65)

    if purpose == "functional":
        infill, walls, infill_pattern = 40, 4, "grid"
    elif purpose == "visual":
        infill, walls, infill_pattern = 15, 3, "gyroid"
    elif purpose == "flexible":
        infill, walls, infill_pattern = 20, 2, "gyroid"
    else:
        infill, walls, infill_pattern = 10, 2, "lines"

    if priority == "strongest":
        infill = min(infill + 20, 80)
        walls += 1
    elif priority == "fastest":
        infill = max(infill - 10, 10)

    size_volumes = {"small": 8, "medium": 40, "large": 150}
    volume_cm3 = size_volumes[size] * (infill / 100 * 0.6 + 0.4)
    flow_rate_cm3_per_min = (speed * float(nozzle) * layer * 60) / 1000
    time_mins = int((volume_cm3 / max(flow_rate_cm3_per_min, 0.5)) * 1.35)
    time_mins = max(time_mins, 8)
    hours = time_mins // 60
    mins = time_mins % 60

    weight_grams = round(volume_cm3 * f["density"], 1)
    filament_length_m = round((weight_grams / f["density"]) / (3.14159 * (1.75/2)**2) / 10, 1)

    warp_risk = f["warp_risk"]
    if size == "large" and warp_risk != "high":
        warp_risk = "medium"
    string_risk = "low"
    if filament == "PETG":
        string_risk = "medium"
    elif filament in ["TPU", "Nylon"]:
        string_risk = "high"
    adhesion_risk = "low"
    if filament in ["ABS", "ASA", "Nylon"]:
        adhesion_risk = "high"
    elif filament == "PETG":
        adhesion_risk = "medium"

    brim_needed = warp_risk == "high" or (warp_risk == "medium" and size == "large")

    tips = []
    if filament in ["PETG", "ABS", "ASA", "TPU", "Nylon"]:
        tips.append("Dry your filament before printing — moisture causes blobs, weak layers and stringing.")
    if warp_risk == "high":
        tips.append(f"Use a brim of at least 8mm — {filament} warps easily without strong bed adhesion.")
    if purpose == "functional":
        tips.append(f"{infill_pattern.capitalize()} infill gives the best strength-to-time ratio for functional parts.")
    if printer == "corexY":
        tips.append("CoreXY handles high speeds well — push speed up 20% if your first layer looks good.")
    if string_risk == "high":
        tips.append("Reduce retraction and increase travel speed to minimise stringing with this filament.")
    if filament == "Carbon Fibre PLA":
        tips.append("CF filament is abrasive — use a hardened steel nozzle or it will wear out fast.")
    if filament == "Wood PLA":
        tips.append("Use a 0.6mm or larger nozzle with Wood PLA to avoid clogging from wood particles.")
    if not tips:
        tips.append("Great combination — no special warnings. You are good to go!")

    compat_warning = PRINTER_WARNINGS.get((printer, filament), None)

    return {
        "layer_height": layer, "speed": speed, "infill": infill, "walls": walls,
        "infill_pattern": infill_pattern, "nozzle_temp": f["nozzle_temp"],
        "bed_temp": f["bed_temp"], "cooling": f["cooling"],
        "retraction": f["retraction"], "retraction_speed": f["retraction_speed"],
        "print_time": f"{hours}h {mins}m", "time_mins": time_mins,
        "warp_risk": warp_risk, "string_risk": string_risk, "adhesion_risk": adhesion_risk,
        "brim_needed": brim_needed, "tips": tips, "weight_grams": weight_grams,
        "filament_length_m": filament_length_m, "filament_density": f["density"],
        "compat_warning": compat_warning, "printer_note": p["notes"],
        "beginner_friendly": f["beginner_friendly"], "needs_enclosure": f["needs_enclosure"],
        "community_tips": f["community_tips"]
    }

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/app")
def main_app():
    return render_template("index.html",
        common_prints=COMMON_PRINTS, filaments=FILAMENT_SETTINGS,
        troubleshooting=TROUBLESHOOTING, slicer_guide=SLICER_GUIDE,
        currencies=CURRENCIES, printer_profiles=PRINTER_PROFILES,
        printer_compat=PRINTER_FILAMENT_COMPATIBILITY, glossary=GLOSSARY,
        bed_adhesion=BED_ADHESION, supports_guide=SUPPORTS_GUIDE,
        drying_guide=DRYING_GUIDE, first_layer_wizard=FIRST_LAYER_WIZARD,
        material_quiz=MATERIAL_QUIZ, failure_gallery=FAILURE_GALLERY,
        printer_checklist=PRINTER_CHECKLIST, blog_posts=BLOG_POSTS)

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    result = calculate_settings(
        filament=data["filament"], printer=data["printer"],
        purpose=data["purpose"], nozzle=data["nozzle"],
        size=data["size"], priority=data["priority"],
        quality_level=int(data.get("quality_level", 5))
    )
    if current_user.is_authenticated:
        h = PrintHistory(
            user_id=current_user.id,
            filament=data["filament"], printer=data["printer"],
            purpose=data["purpose"], nozzle=data["nozzle"],
            size=data["size"], priority=data["priority"],
            quality_level=int(data.get("quality_level", 5)),
            layer_height=result["layer_height"], speed=result["speed"],
            infill=result["infill"], print_time=result["print_time"],
            weight_grams=result["weight_grams"]
        )
        db.session.add(h)
        db.session.commit()
    return jsonify(result)

@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm

    data = request.json
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    story = []

    title_style = ParagraphStyle('title', fontSize=24, fontName='Helvetica-Bold', textColor=colors.HexColor('#6c63ff'), spaceAfter=6)
    sub_style = ParagraphStyle('sub', fontSize=12, textColor=colors.HexColor('#8888aa'), spaceAfter=20)
    body_style = ParagraphStyle('body', fontSize=11, textColor=colors.HexColor('#333344'), spaceAfter=6, leading=16)
    heading_style = ParagraphStyle('heading', fontSize=13, fontName='Helvetica-Bold', textColor=colors.HexColor('#111118'), spaceAfter=8, spaceBefore=16)

    story.append(Paragraph('OptimalPrint', title_style))
    story.append(Paragraph('3D Print Settings Report', sub_style))
    story.append(Paragraph(f'Filament: {data.get("filament_name","—")} | Printer: {data.get("printer_name","—")}', body_style))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph('Recommended Settings', heading_style))

    settings_data = [
        ['Setting', 'Value'],
        ['Layer Height', data.get('layer','—')],
        ['Print Speed', data.get('speed','—')],
        ['Infill', data.get('infill','—')],
        ['Estimated Time', data.get('time','—')],
        ['Nozzle Temperature', data.get('nozzle','—')],
        ['Bed Temperature', data.get('bed','—')],
        ['Cooling Fan', data.get('cooling','—')],
        ['Wall Count', data.get('walls','—')],
        ['Infill Pattern', data.get('pattern','—')],
        ['Retraction', data.get('retraction','—')],
        ['Estimated Weight', data.get('weight','—')],
    ]
    t = Table(settings_data, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c63ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8f8ff'), colors.white]),
        ('FONTSIZE', (0,1), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ddddee')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('Generated by OptimalPrint — optimalprint.up.railway.app', ParagraphStyle('footer', fontSize=9, textColor=colors.HexColor('#aaaacc'), alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='OptimalPrint-settings.pdf')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return redirect(url_for("register"))
        user = User(email=email, username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("main_app"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("main_app"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))

@app.route("/history")
@login_required
def history():
    records = PrintHistory.query.filter_by(user_id=current_user.id).order_by(PrintHistory.created_at.desc()).limit(50).all()
    return jsonify([{
        "filament": r.filament, "printer": r.printer, "purpose": r.purpose,
        "print_time": r.print_time, "weight_grams": r.weight_grams,
        "layer_height": r.layer_height, "speed": r.speed, "infill": r.infill,
        "created_at": r.created_at.strftime("%d %b %Y %H:%M")
    } for r in records])

@app.route("/save-setting", methods=["POST"])
@login_required
def save_setting():
    data = request.json
    s = SavedSetting(
        user_id=current_user.id,
        name=data.get("name", f"{data['filament']} · {data['purpose']}"),
        filament=data["filament"], printer=data["printer"],
        purpose=data["purpose"], nozzle=data["nozzle"],
        size=data["size"], priority=data["priority"],
        quality_level=int(data.get("quality_level", 5))
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/saved-settings")
@login_required
def saved_settings():
    settings = SavedSetting.query.filter_by(user_id=current_user.id).order_by(SavedSetting.created_at.desc()).all()
    return jsonify([{
        "id": s.id, "name": s.name, "filament": s.filament,
        "printer": s.printer, "purpose": s.purpose, "nozzle": s.nozzle,
        "size": s.size, "priority": s.priority, "quality_level": s.quality_level,
        "created_at": s.created_at.strftime("%d %b %Y")
    } for s in settings])

@app.route("/delete-setting/<int:sid>", methods=["DELETE"])
@login_required
def delete_setting(sid):
    s = SavedSetting.query.filter_by(id=sid, user_id=current_user.id).first()
    if s:
        db.session.delete(s)
        db.session.commit()
    return jsonify({"ok": True})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)