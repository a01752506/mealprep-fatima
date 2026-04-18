import streamlit as st
import pandas as pd
import os
import re
import json
import unicodedata
import random
import math
from datetime import datetime
from fractions import Fraction
from collections import defaultdict
import fitz
from pymongo import MongoClient
from bson import ObjectId

# ==================== VARIABLES ====================
PUBLIC_ACCESS_PASSWORD = st.secrets["PUBLIC_ACCESS_PASSWORD"]
DEVELOPER_PASSWORD = st.secrets["DEVELOPER_PASSWORD"]
MONGO_URI = st.secrets["MONGO_URI"]
MONGO_DB_NAME = st.secrets["MONGO_DB_NAME"]

# ==================== CONFIG ====================
PDF_FOLDER = "pdfs"

st.set_page_config(
    page_title="Meal Prep Planner - Fátima",
    page_icon="🥗",
    layout="wide"
)

# ==================== ESTILO ====================
st.markdown("""
<style>

:root {
    --bg: #FFF9E6;
    --card: #FFFFFF;
    --border: #EEDB8A;
    --text: #4A4032;
    --muted: #6B5E4A;

    --accent: #FFE08A;
    --accent-strong: #E6B800;
    --accent-soft: #FFF4CC;
}

/* Fondo general */
.stApp {
    background-color: var(--bg);
    color: var(--text);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--accent-soft);
    border-right: 1px solid var(--border);
}

/* Tarjetas principales */
.soft-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}

/* Tarjetas pequeñas */
.mini-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
}

/* Títulos */
.section-title {
    font-size: 30px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
}

.section-subtitle {
    color: var(--muted);
    margin-bottom: 20px;
}

/* Botones */
button[kind="primary"] {
    background-color: var(--accent);
    border: none;
    color: #4A4032;
    border-radius: 10px;
    font-weight: 600;
}

button[kind="primary"]:hover {
    background-color: var(--accent-strong);
}

/* Selectbox */
div[data-baseweb="select"] {
    border-radius: 10px;
}

/* Pills (Desayuno, Comida, etc) */
.small-pill {
    background-color: var(--accent-soft);
    color: var(--text);
    border-radius: 20px;
    padding: 6px 12px;
    font-size: 12px;
    margin-right: 6px;
}

/* Banner */
.selection-banner {
    background-color: var(--accent-soft);
    border: 1px solid var(--border);
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 16px;
}

/* Day cards (plan 15 días) */
.day-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
}

.day-label {
    font-weight: 600;
    color: var(--muted);
    margin-bottom: 4px;
}

.day-menu {
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
}

.small-muted {
    font-size: 12px;
    color: var(--muted);
}

/* Inputs */
input, textarea {
    border-radius: 10px !important;
}

/* Tabs */
button[role="tab"] {
    font-weight: 600;
    color: var(--muted);
}

button[role="tab"][aria-selected="true"] {
    color: var(--text);
    border-bottom: 2px solid var(--accent-strong);
}

</style>
""", unsafe_allow_html=True)

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# ==================== SESION ====================
def init_session_state():
    defaults = {
        "authenticated": False,
        "show_dev": False,
        "selected_favorite_by_plan": {},
        "shopping_checks": {},
        "uploaded_pdf_name": None,
        "uploaded_pdf_path": None,
        "uploaded_menus": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

if not st.session_state.authenticated:
    st.markdown('<div class="hero-title">🔒 Acceso privado</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Esta app es solo para uso autorizado.</div>', unsafe_allow_html=True)

    password_input = st.text_input("Ingresa la contraseña", type="password")

    if st.button("Entrar", use_container_width=True):
        if password_input == PUBLIC_ACCESS_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

    st.stop()

# ==================== DB ====================
@st.cache_resource
def get_mongo_db():
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
            maxPoolSize=10
        )
        client.admin.command("ping")
        return client[MONGO_DB_NAME]
    except Exception:
        return None


db = get_mongo_db()
mongo_available = db is not None

if mongo_available:
    menu_sets_collection = db["menu_sets"]
    usage_logs_collection = db["usage_logs"]
    generated_plans_collection = db["generated_plans"]
    ejercicios_collection = db["ejercicios"]
else:
    menu_sets_collection = None
    usage_logs_collection = None
    generated_plans_collection = None
    ejercicios_collection = None


def registrar_evento(tipo: str, detalle: str):
    if not mongo_available:
        return

    usage_logs_collection.insert_one({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo,
        "detalle": detalle,
        "accedido_desde": "streamlit_cloud",
    })


def guardar_plan(nombre_plan, pdf_path, menus_json):
    if not mongo_available:
        st.error("No se pudo conectar a MongoDB. Revisa tus secrets y Mongo Atlas.")
        return

    menu_sets_collection.insert_one({
        "nombre_plan": nombre_plan,
        "pdf_path": pdf_path,
        "menus_json": menus_json,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()


@st.cache_data(ttl=30)
def cargar_planes():
    if not mongo_available:
        return pd.DataFrame(columns=["id", "nombre_plan", "pdf_path", "menus_json", "fecha"])

    docs = list(
        menu_sets_collection.find(
            {},
            {"nombre_plan": 1, "pdf_path": 1, "menus_json": 1, "fecha": 1}
        ).sort("fecha", -1)
    )

    if not docs:
        return pd.DataFrame(columns=["id", "nombre_plan", "pdf_path", "menus_json", "fecha"])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)


def eliminar_plan(plan_id):
    if not mongo_available:
        st.error("No se pudo conectar a MongoDB.")
        return

    try:
        menu_sets_collection.delete_one({"_id": ObjectId(plan_id)})
        generated_plans_collection.delete_many({"menu_set_id": plan_id})
        st.cache_data.clear()
    except Exception:
        st.error("No se pudo eliminar el plan.")


@st.cache_data(ttl=30)
def cargar_logs():
    if not mongo_available:
        return pd.DataFrame(columns=["timestamp", "tipo", "detalle", "accedido_desde"])

    docs = list(
        usage_logs_collection.find(
            {},
            {"timestamp": 1, "tipo": 1, "detalle": 1, "accedido_desde": 1}
        ).sort("timestamp", -1)
    )

    if not docs:
        return pd.DataFrame(columns=["timestamp", "tipo", "detalle", "accedido_desde"])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)


def guardar_plan_15_dias(menu_set_id, favorite_menu, plan_data):
    if not mongo_available:
        st.error("No se pudo conectar a MongoDB.")
        return

    generated_plans_collection.delete_many({"menu_set_id": menu_set_id})

    generated_plans_collection.insert_one({
        "menu_set_id": menu_set_id,
        "favorite_menu": favorite_menu,
        "plan_json": json.dumps(plan_data, ensure_ascii=False),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()

def guardar_ejercicio(nombre_ejercicio, peso, unidad, fecha_ejercicio, notas=""):
    if not mongo_available:
        st.error("No se pudo conectar a MongoDB.")
        return

    peso_kg = convertir_a_kg(peso, unidad)

    ejercicios_collection.insert_one({
        "nombre_ejercicio": nombre_ejercicio,
        "peso_original": peso,
        "unidad_original": unidad,
        "peso_kg": peso_kg,
        "fecha": str(fecha_ejercicio),
        "notas": notas,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()

@st.cache_data(ttl=30)
def cargar_plan_15_dias(menu_set_id):
    if not mongo_available:
        return pd.DataFrame(columns=["menu_set_id", "favorite_menu", "plan_json", "created_at"])

    docs = list(
        generated_plans_collection.find(
            {"menu_set_id": menu_set_id},
            {"menu_set_id": 1, "favorite_menu": 1, "plan_json": 1, "created_at": 1}
        ).sort("created_at", -1).limit(1)
    )

    if not docs:
        return pd.DataFrame(columns=["menu_set_id", "favorite_menu", "plan_json", "created_at"])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)

@st.cache_data(ttl=30)
def cargar_ejercicios():
    if not mongo_available:
        return pd.DataFrame(columns=[
            "nombre_ejercicio", "peso_original", "unidad_original",
            "peso_kg", "fecha", "notas", "created_at"
        ])

    docs = list(
        ejercicios_collection.find(
            {},
            {
                "nombre_ejercicio": 1,
                "peso_original": 1,
                "unidad_original": 1,
                "peso_kg": 1,
                "fecha": 1,
                "notas": 1,
                "created_at": 1
            }
        ).sort("fecha", -1)
    )

    if not docs:
        return pd.DataFrame(columns=[
            "nombre_ejercicio", "peso_original", "unidad_original",
            "peso_kg", "fecha", "notas", "created_at"
        ])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)


# ==================== HELPERS DE TEXTO ====================
def strip_accents(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def normalize_for_search(text: str) -> str:
    if not text:
        return ""
    text = strip_accents(text).lower()
    return re.sub(r"\s+", " ", text).strip()


def normalize_token(text: str) -> str:
    if not text:
        return ""
    text = strip_accents(text).lower().strip()
    text = re.sub(r"[^\w\s/]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def limpiar_linea(line: str) -> str:
    if not line:
        return ""
    line = line.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", line).strip()


def should_skip_line(line: str) -> bool:
    raw = line.strip()
    low = normalize_token(raw)

    if not low:
        return True

    basura = [
        "ln oscar marquez",
        "eat to fit",
        "nutrifit oscar",
        "nutrifitoscar",
        "instagram",
        "lista de super",
        "lista de equivalencias",
        "control de porciones",
        "para el antojo",
        "menu",
        "---",
    ]

    if "@" in raw:
        return True

    return any(b in low for b in basura)

def convertir_a_kg(peso, unidad):
    if unidad == "lbs":
        return round(peso * 0.453592, 2)
    return round(peso, 2)


# ==================== PDF ====================
def guardar_pdf(uploaded_file):
    if uploaded_file is None:
        return None

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    filepath = os.path.join(PDF_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filepath


def extract_text_with_fitz(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        pages.append({
            "page_number": i + 1,
            "text": text
        })

    doc.close()
    return pages


def page_looks_like_menu(text: str) -> bool:
    clean = normalize_for_search(text)
    compact = re.sub(r"\s+", "", clean)

    excluded = [
        "listadesuper",
        "listadeequivalencias",
        "controldeporciones",
        "paraelantojo",
        "alimentoeq",
    ]
    if any(x in compact for x in excluded):
        return False

    has_menu = "menu" in compact
    has_desayuno = "desayuno" in compact
    has_colacion = "colacion" in compact
    has_comida = "comida" in compact
    has_cena = "cena" in compact

    section_count = sum([has_desayuno, has_colacion, has_comida, has_cena])
    return has_menu and section_count >= 2


def extract_menu_pages(pdf_path):
    pages = extract_text_with_fitz(pdf_path)
    return [page for page in pages if page_looks_like_menu(page["text"])]


def cleanup_section_text(text: str) -> str:
    if not text:
        return ""

    lines = [limpiar_linea(x) for x in text.split("\n")]
    cleaned = []

    for line in lines:
        if not line:
            continue
        if should_skip_line(line):
            continue
        cleaned.append(line)

    seen = set()
    unique = []
    for item in cleaned:
        marker = item.lower()
        if marker not in seen:
            unique.append(item)
            seen.add(marker)

    return "\n".join(unique).strip()


def parse_menu_page(page_text: str):
    raw = page_text.replace("\r", "\n")
    raw = re.sub(r"\n{2,}", "\n", raw)

    filtered_lines = []
    for line in raw.split("\n"):
        line = limpiar_linea(line)
        if not line:
            continue
        if should_skip_line(line):
            continue
        filtered_lines.append(line)

    filtered_text = "\n".join(filtered_lines)
    pattern = re.compile(r"(Desayuno|Colaci[oó]n|Comida|Cena)\.?\s*", re.IGNORECASE)
    matches = list(pattern.finditer(filtered_text))

    sections = {
        "desayuno": "",
        "colacion_1": "",
        "comida": "",
        "colacion_2": "",
        "cena": "",
    }

    colacion_count = 0

    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(filtered_text)

        header = normalize_token(match.group(1))
        content = cleanup_section_text(filtered_text[start:end].strip())

        if header == "desayuno":
            sections["desayuno"] = content
        elif header == "comida":
            sections["comida"] = content
        elif header == "cena":
            sections["cena"] = content
        elif header == "colacion":
            colacion_count += 1
            if colacion_count == 1:
                sections["colacion_1"] = content
            elif colacion_count == 2:
                sections["colacion_2"] = content

    return sections


def extract_menus_from_pdf(pdf_path):
    menu_pages = extract_menu_pages(pdf_path)
    menus = []

    for idx, page in enumerate(menu_pages, start=1):
        sections = parse_menu_page(page["text"])
        sections["menu_numero"] = idx
        sections["page_number"] = page["page_number"]
        menus.append(sections)

    return menus


def render_menu(menu):
    st.markdown('<div class="menu-preview">', unsafe_allow_html=True)

    def meal_block(title, content):
        if content:
            st.markdown(f'<div class="meal-title">{title}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="small-muted">{content.replace(chr(10), "<br>")}</div>',
                unsafe_allow_html=True,
            )

    meal_block("Desayuno", menu.get("desayuno"))
    meal_block("Colación 1", menu.get("colacion_1"))
    meal_block("Comida", menu.get("comida"))
    meal_block("Colación 2", menu.get("colacion_2"))
    meal_block("Cena", menu.get("cena"))

    if not any(menu.get(k) for k in ["desayuno", "colacion_1", "comida", "colacion_2", "cena"]):
        st.warning("Este menú quedó vacío al parsearse.")

    st.markdown('</div>', unsafe_allow_html=True)

# ==================== INGREDIENTES ====================
def parse_number(value: str):
    if not value:
        return None

    value = value.strip()
    value = value.replace("½", "1/2")
    value = value.replace("¼", "1/4")
    value = value.replace("¾", "3/4")

    try:
        if "/" in value:
            return float(Fraction(value))
        return float(value)
    except Exception:
        return None


def normalize_ingredient_name(name: str) -> str:
    name = normalize_token(name)

    aliases = {
        "pechuga de pollo": "pollo",
        "pollo asada": "pollo",
        "pollo": "pollo",
        "tinga de pollo": "pollo",
        "bistec de res": "bistec",
        "bistec": "bistec",
        "pescado": "pescado",
        "filete de pescado": "pescado",
        "salmon": "salmon",
        "leche light": "leche",
        "leche": "leche",
        "fresas": "fresas",
        "blueberries": "blueberries",
        "pina": "piña",
        "melon": "melón",
        "platano": "plátano",
        "manzana": "manzana",
        "naranja": "naranja",
        "toronja": "toronja",
        "aguacate": "aguacate",
        "espinaca cocida": "espinaca",
        "espinaca": "espinaca",
        "champinones": "champiñones",
        "pimientos": "pimientos",
        "zanahoria": "zanahoria",
        "calabaza": "calabaza",
        "verduras": "verduras",
        "pico": "pico de gallo",
        "pico de gallo": "pico de gallo",
        "arroz": "arroz",
        "queso panela": "queso panela",
        "queso oaxaca": "queso oaxaca",
        "jamon de pavo": "jamón de pavo",
        "aceite oleico": "aceite oleico",
        "proteina sin carbohidratos": "proteína",
        "proteina": "proteína",
        "nopales": "nopales",
        "lechuga": "lechuga",
        "cebolla": "cebolla",
        "cebollita cambray": "cebolla",
        "galletas salmas": "galletas salmas",
        "salmas": "galletas salmas",
        "yogurt bebible chobani": "yogurt bebible chobani",
        "yogurt flip chobani": "yogurt flip chobani",
        "yogurt chobani split": "yogurt chobani split",
        "yogurt chobani": "yogurt chobani",
        "yogurt bajo en grasa estilo griego de yoplait": "yogurt griego yoplait",
        "yogurt": "yogurt",
        "pan integral": "pan integral",
        "tortilla de maiz": "tortilla de maíz",
        "tortillas de maiz": "tortilla de maíz",
        "tortilla de harina integral": "tortilla de harina integral",
        "tortillas de harina integral": "tortilla de harina integral",
        "tortilla de nopal": "tortilla de nopal",
        "tortillas de nopal": "tortilla de nopal",
        "tostadas susalia": "tostadas susalia",
        "totopos susalia": "totopos susalia",
        "platano con canela": "plátano",
        "salsa verde o roja": "salsa",
        "guacamole": "guacamole",
        "mayonesa light": "mayonesa light",
        "queso cottage": "queso cottage",
    }

    for key, value in aliases.items():
        if key in name:
            return value

    return name


def normalize_unit(unit: str) -> str:
    unit = unit.lower().strip()

    mapping = {
        "tazas": "taza",
        "paquetes": "paquete",
        "piezas": "pieza",
        "pz": "pieza",
        "pzas": "pieza",
        "rebanadas": "rebanada",
        "cucharaditas": "cucharadita",
        "cucharadas": "cucharada",
        "tortillas": "pieza",
        "tortilla": "pieza",
        "manzanas": "pieza",
        "manzana": "pieza",
        "naranjas": "pieza",
        "naranja": "pieza",
        "yogurt": "pieza",
        "uvas": "pieza",
        "tostadas": "pieza",
        "tostada": "pieza",
        "salmas": "pieza",
    }

    return mapping.get(unit, unit)


def extract_ingredients_from_text(text: str):
    if not text:
        return []

    working = text.lower()
    working = working.replace("½", "1/2").replace("¼", "1/4").replace("¾", "3/4")
    working = working.replace("\n", " | ")

    items = []

    pattern_1 = re.compile(
        r"(\d+(?:/\d+)?)\s*"
        r"(g|ml|taza|tazas|cucharadita|cucharaditas|cucharada|cucharadas|scoop|paquete|paquetes|rebanada|rebanadas)\s*"
        r"de\s+([a-záéíóúñ\s]+?)(?= con | y | en | \||,|$)",
        re.IGNORECASE
    )

    pattern_2 = re.compile(
        r"(\d+(?:/\d+)?)\s*"
        r"(tortilla|tortillas|manzana|manzanas|naranja|naranjas|toronja|yogurt|uvas|tostadas|salmas|tostada|paquete|paquetes)\b"
        r"(?:\s+de\s+([a-záéíóúñ\s]+?))?(?= con | y | en | \||,|$)",
        re.IGNORECASE
    )

    pattern_3 = re.compile(
        r"(\d+(?:/\d+)?)\s*(yogurt(?:\s+[a-záéíóúñ]+){0,6})",
        re.IGNORECASE
    )

    for match in pattern_1.finditer(working):
        qty = parse_number(match.group(1))
        unit = normalize_unit(match.group(2).strip().lower())
        ingredient = normalize_ingredient_name(match.group(3).strip())

        if qty is not None and ingredient:
            items.append((ingredient, unit, qty))

    for match in pattern_2.finditer(working):
        qty = parse_number(match.group(1))
        unit = match.group(2).strip().lower()
        extra = (match.group(3) or "").strip()

        ingredient = ""
        final_unit = "pieza"

        if unit in ["manzana", "manzanas"]:
            ingredient = "manzana"
        elif unit in ["naranja", "naranjas"]:
            ingredient = "naranja"
        elif unit == "toronja":
            ingredient = "toronja"
        elif unit == "yogurt":
            ingredient = extra if extra else "yogurt"
        elif unit in ["tortilla", "tortillas"]:
            ingredient = f"tortilla de {extra}" if extra else "tortilla"
        elif unit == "uvas":
            ingredient = "uvas"
        elif unit in ["tostadas", "tostada"]:
            ingredient = "tostadas" if not extra else f"tostadas {extra}"
        elif unit == "salmas":
            ingredient = "galletas salmas"
        elif unit in ["paquete", "paquetes"]:
            ingredient = extra if extra else "paquete"
            final_unit = "paquete"
        else:
            ingredient = unit

        ingredient = normalize_ingredient_name(ingredient)

        if qty is not None and ingredient:
            items.append((ingredient, final_unit, qty))

    for match in pattern_3.finditer(working):
        qty = parse_number(match.group(1))
        ingredient = normalize_ingredient_name(match.group(2).strip())

        if qty is not None and ingredient:
            items.append((ingredient, "pieza", qty))

    dedup = []
    seen = set()
    for item in items:
        if item not in seen:
            dedup.append(item)
            seen.add(item)

    return dedup


def convert_to_supermarket_unit(ingredient: str, unit: str, qty: float):
    ingredient = normalize_ingredient_name(ingredient)
    unit = normalize_unit(unit)

    conversions = {
        "espinaca": {"taza": ("bolsa", 2)},
        "lechuga": {"taza": ("pieza", 4)},
        "fresas": {"taza": ("paquete", 1)},
        "blueberries": {"taza": ("paquete", 1)},
        "verduras": {"taza": ("bolsa", 2)},
        "arroz": {"taza": ("paquete", 2)},
        "leche": {"ml": ("litro", 1000)},
        "pollo": {"g": ("kg", 1000)},
        "bistec": {"g": ("kg", 1000)},
        "pescado": {"g": ("kg", 1000)},
        "salmon": {"g": ("kg", 1000)},
        "zanahoria": {"taza": ("paquete", 1)},
        "calabaza": {"taza": ("paquete", 1)},
        "pimientos": {"taza": ("paquete", 1)},
    }

    if ingredient in conversions and unit in conversions[ingredient]:
        new_unit, factor = conversions[ingredient][unit]
        new_qty = qty / factor

        if new_unit in ["bolsa", "paquete", "pieza", "litro"]:
            new_qty = math.ceil(new_qty)
        else:
            new_qty = round(new_qty, 2)

        return new_unit, new_qty

    if ingredient in ["pollo", "bistec", "pescado", "salmon"] and unit == "g":
        return "kg", round(qty / 1000, 2)
    
    preparaciones = ["pico de gallo", "salsa", "guacamole"]

    if ingredient not in preparaciones and unit == "taza":
        return "bolsa", math.ceil(qty / 2)

    return unit, qty


def build_shopping_list_from_plan(day_plan, menus_by_number):
    shopping = defaultdict(lambda: defaultdict(float))

    for day in day_plan:
        menu_number = day["menu_numero"]
        menu = menus_by_number.get(menu_number)
        if not menu:
            continue

        for section in ["desayuno", "colacion_1", "comida", "colacion_2", "cena"]:
            text = menu.get(section, "")
            ingredients = extract_ingredients_from_text(text)

            for ingredient, unit, qty in ingredients:
                unit = normalize_unit(unit)
                unit, qty = convert_to_supermarket_unit(ingredient, unit, qty)

                if ingredient == "proteína" and unit == "g":
                    continue

                shopping[ingredient][unit] += qty

    rows = []
    for ingredient, units in shopping.items():
        for unit, total in units.items():
            if unit in ["bolsa", "paquete", "pieza", "litro"]:
                total = math.ceil(total)
            else:
                total = round(total, 2)

            rows.append({
                "Ingrediente": ingredient,
                "Unidad": unit,
                "Cantidad total": total,
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(by=["Ingrediente", "Unidad"]).reset_index(drop=True)

    return df


def categorize_ingredient(name: str) -> str:
    n = normalize_token(name)

    if any(x in n for x in ["pollo", "bistec", "pescado", "salmon", "jamon", "proteina", "yogurt", "leche"]):
        return "Proteínas y lácteos"

    if "queso" in n:
        return "Quesos"

    if any(x in n for x in ["fresas", "blueberries", "pina", "melon", "platano", "manzana", "naranja", "toronja", "uvas"]):
        return "Frutas"

    if any(x in n for x in ["lechuga", "espinaca", "zanahoria", "calabaza", "pimientos", "nopales", "cebolla", "verduras", "pico de gallo", "aguacate", "salsa"]):
        return "Verduras y extras"

    if any(x in n for x in ["tortilla", "pan integral", "galletas salmas", "arroz", "tostadas", "totopos", "bolillo"]):
        return "Cereales y panes"

    if any(x in n for x in ["aceite", "mayonesa", "guacamole", "queso cottage"]):
        return "Condimentos y complementos"

    return "Otros"


# ==================== PLANIFICADOR ====================
def generate_weighted_15_day_plan(menus, favorite_menu_number, seed=None):
    menu_numbers = [menu["menu_numero"] for menu in menus]

    if not menu_numbers:
        return []

    if favorite_menu_number not in menu_numbers:
        favorite_menu_number = menu_numbers[0]

    total_days = 15
    num_menus = len(menu_numbers)

    # Caso simple: si solo hay un menú, se repite
    if num_menus == 1:
        return [{"dia": i + 1, "menu_numero": menu_numbers[0]} for i in range(total_days)]

    # Queremos que el favorito tenga prioridad, pero sin exagerar
    # Regla:
    # - si hay 4 menús, favorito ≈ 6 días
    # - si hay 3 menús, favorito ≈ 6 días
    # - si hay 2 menús, favorito ≈ 8 días
    if num_menus >= 3:
        favorite_count = 6
    else:
        favorite_count = 8

    remaining_days = total_days - favorite_count
    other_menus = [num for num in menu_numbers if num != favorite_menu_number]

    counts = {num: 0 for num in menu_numbers}
    counts[favorite_menu_number] = favorite_count

    # Repartir los días restantes entre los otros menús de forma equilibrada
    base_count = remaining_days // len(other_menus)
    extra = remaining_days % len(other_menus)

    for i, num in enumerate(other_menus):
        counts[num] = base_count + (1 if i < extra else 0)

    # Construir secuencia
    sequence = []
    for num, qty in counts.items():
        sequence.extend([num] * qty)

    rng = random.Random(seed)

    # Mezclar varias veces hasta evitar demasiadas repeticiones seguidas
    for _ in range(100):
        rng.shuffle(sequence)
        max_consecutive = 1
        current_streak = 1

        for i in range(1, len(sequence)):
            if sequence[i] == sequence[i - 1]:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 1

        # Aceptamos la secuencia si no hay más de 2 iguales seguidos
        if max_consecutive <= 2:
            break

    return [{"dia": i + 1, "menu_numero": menu_number} for i, menu_number in enumerate(sequence)]

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🥗 Meal Prep Planner")
    st.caption("Organiza tu alimentación de forma simple")

    opcion = st.radio(
        "Navegación",
        [
            "Inicio",
            "Subir plan",
            "Elegir menú favorito",
            "Mi plan de 15 días",
            "Lista del súper",
            "Ejercicio",
            "Historial",
            "Dashboard",
        ],
    )

    st.session_state.show_dev = st.checkbox(
        "Mostrar modo desarrolladora",
        value=st.session_state.get("show_dev", False)
    )

# ==================== HEADER ====================
st.markdown('<div class="hero-title">Meal Prep Planner</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Sube tu dieta, selecciona tu menú favorito y convierte la planeación en una lista del súper mucho más útil.</div>',
    unsafe_allow_html=True,
)

if not mongo_available:
    st.warning("⚠️ No hay conexión con MongoDB Atlas. Puedes navegar la app, pero no guardar ni cargar datos hasta arreglar la conexión.")

# ==================== PAGINAS ====================
if opcion == "Inicio":
    planes = cargar_planes()
    total_planes = len(planes)
    total_menus = 0
    ultimo_plan = "Aún no hay planes"

    if not planes.empty:
        ultimo_plan = planes.iloc[0]["nombre_plan"]
        for _, row in planes.iterrows():
            menus = json.loads(row["menus_json"]) if row["menus_json"] else []
            total_menus += len(menus)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="mini-card"><div class="metric-label">Planes guardados</div><div class="metric-value">{total_planes}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="mini-card"><div class="metric-label">Menús detectados</div><div class="metric-value">{total_menus}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="mini-card"><div class="metric-label">Último plan</div><div class="metric-value" style="font-size:1.08rem;">{ultimo_plan}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div class='section-title'>Accesos rápidos</div>", unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.markdown(
            '<div class="soft-card"><strong>➕ Subir plan</strong><div class="small-muted">Carga el PDF y detecta los menús automáticamente.</div></div>',
            unsafe_allow_html=True,
        )
    with q2:
        st.markdown(
            '<div class="soft-card"><strong>💗 Elegir favorito</strong><div class="small-muted">Hazle a Fátima la pregunta importante y guarda su menú favorito.</div></div>',
            unsafe_allow_html=True,
        )
    with q3:
        st.markdown(
            '<div class="soft-card"><strong>📅 Ver 15 días</strong><div class="small-muted">Consulta la planeación ya generada sin saturar la selección.</div></div>',
            unsafe_allow_html=True,
        )
    with q4:
        st.markdown(
            '<div class="soft-card"><strong>🛒 Lista del súper</strong><div class="small-muted">Revisa ingredientes en formato checklist y por categorías.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="soft-card"><div class="section-title" style="margin-top:0;">Flujo</div><div class="small-muted">1. Subes el PDF.<br>2. Guardas el plan.<br>3. Fátima elige su menú favorito.<br>4. La app genera su propuesta de 15 días.<br>5. Se crea una lista del súper pensada para comprar, no para cocinar.</div></div>',
        unsafe_allow_html=True,
    )

elif opcion == "Subir plan":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Subir PDF de la dieta</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Carga el archivo, revisa cómo quedó el parseo y guarda el plan.</div>', unsafe_allow_html=True)

    nombre_plan = st.text_input("Nombre del plan", placeholder="Ej. Plan Fátima abril")
    uploaded_pdf = st.file_uploader("Sube el PDF", type=["pdf"])

    if uploaded_pdf is not None:
        current_file_name = uploaded_pdf.name

        needs_processing = (
            st.session_state.uploaded_pdf_name != current_file_name
            or st.session_state.uploaded_menus is None
            or st.session_state.uploaded_pdf_path is None
        )

        if needs_processing:
            progress = st.progress(0, text="Preparando archivo...")
            status_box = st.empty()

            progress.progress(20, text="Guardando PDF...")
            pdf_path = guardar_pdf(uploaded_pdf)

            progress.progress(55, text="Leyendo contenido...")
            status_box.info("Detectando páginas de menú...")
            menus_extraidos = extract_menus_from_pdf(pdf_path)

            progress.progress(85, text="Organizando comidas...")
            total_menus = len(menus_extraidos)

            progress.progress(100, text="Todo listo")
            status_box.success(f"Se detectaron {total_menus} menús.")

            st.session_state.uploaded_pdf_name = current_file_name
            st.session_state.uploaded_pdf_path = pdf_path
            st.session_state.uploaded_menus = menus_extraidos

        pdf_path = st.session_state.uploaded_pdf_path
        menus_extraidos = st.session_state.uploaded_menus

        if not menus_extraidos:
            st.error("No se detectaron menús en el PDF.")
        else:
            st.success(f"PDF subido correctamente. Se detectaron {len(menus_extraidos)} menús. Ahora puedes elegir tu menú favorito después de guardarlo.")

            for menu in menus_extraidos:
                with st.expander(f"Menú {menu['menu_numero']} · página {menu['page_number']}"):
                    render_menu(menu)

            if st.button("💾 Guardar plan", use_container_width=True, disabled=not nombre_plan.strip()):
                guardar_plan(
                    nombre_plan=nombre_plan.strip(),
                    pdf_path=pdf_path,
                    menus_json=json.dumps(menus_extraidos, ensure_ascii=False),
                )
                registrar_evento("plan_guardado", nombre_plan.strip())
                st.success("Plan guardado correctamente.")
                st.markdown(
                    '<div class="selection-banner">💗 Tu plan ya está listo. Ahora puedes ir a elegir tu menú favorito.</div>',
                    unsafe_allow_html=True,
                )

                st.session_state.uploaded_pdf_name = None
                st.session_state.uploaded_pdf_path = None
                st.session_state.uploaded_menus = None

            if not nombre_plan.strip():
                st.warning("Escribe un nombre para habilitar el botón de guardar.")

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Elegir menú favorito":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Elegir menú favorito</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Aquí va la pregunta importante. Esta pantalla solo sirve para escoger el favorito y generar el plan.</div>', unsafe_allow_html=True)

    df = cargar_planes()
    if df.empty:
        st.info("Primero guarda al menos un plan para poder continuar.")
    else:
        selected_id = st.selectbox(
            "Selecciona un plan",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre_plan"].values[0],
            key="favorite_plan_selector",
        )
        row = df[df["id"] == selected_id].iloc[0]
        menus = json.loads(row["menus_json"]) if row["menus_json"] else []

        st.markdown(
            '<div class="question-wrap"><div class="question-title">¿Cuál es tu menú favorito?</div><div class="question-subtitle">Selecciona el menú que más te guste para que aparezca con mayor frecuencia dentro de la propuesta de 15 días.</div></div>',
            unsafe_allow_html=True,
        )

        selected_map = st.session_state.selected_favorite_by_plan
        selected_favorite = selected_map.get(selected_id)

        cols = st.columns(2)
        for idx, menu in enumerate(menus):
            with cols[idx % 2]:
                is_selected = selected_favorite == menu["menu_numero"]
                class_name = "menu-card-selected" if is_selected else "menu-card-default"
                st.markdown(f'<div class="{class_name}">', unsafe_allow_html=True)
                title = f"### Menú {menu['menu_numero']} {'✓' if is_selected else ''}"
                st.markdown(title)

                tags = []
                for label, key in [
                    ("Desayuno", "desayuno"),
                    ("Colación 1", "colacion_1"),
                    ("Comida", "comida"),
                    ("Colación 2", "colacion_2"),
                    ("Cena", "cena"),
                ]:
                    if menu.get(key):
                        tags.append(f"<span class='tag'>{label}</span>")
                st.markdown("".join(tags), unsafe_allow_html=True)

                render_menu(menu)

                button_label = f"💗 Elegir menú {menu['menu_numero']}"
                if st.button(button_label, key=f"fav_btn_{selected_id}_{menu['menu_numero']}", use_container_width=True):
                    st.session_state.selected_favorite_by_plan[selected_id] = menu["menu_numero"]
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        selected_favorite = st.session_state.selected_favorite_by_plan.get(selected_id)
        if selected_favorite:
            st.markdown(
                f'<div class="selection-banner">✨ Menú favorito seleccionado: Menú {selected_favorite}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Generar plan de 15 días", use_container_width=True):
                day_plan = generate_weighted_15_day_plan(menus, selected_favorite)
                guardar_plan_15_dias(selected_id, selected_favorite, day_plan)
                registrar_evento("plan_15_dias_generado", f"Plan {selected_id} · favorito {selected_favorite}")
                st.success("Plan de 15 días generado correctamente. Ahora revísalo en la pestaña 'Mi plan de 15 días'.")

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Mi plan de 15 días":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Mi plan de 15 días</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Aquí puedes visualizar y ajustar tu planeación según tu rutina real.</div>', unsafe_allow_html=True)

    df = cargar_planes()
    if df.empty:
        st.info("Todavía no hay planes guardados.")
    else:
        selected_id = st.selectbox(
            "Selecciona un plan",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre_plan"].values[0],
            key="view_plan_selector",
        )

        # 🔹 IMPORTANTE: necesitamos menus aquí
        row = df[df["id"] == selected_id].iloc[0]
        menus = json.loads(row["menus_json"]) if row["menus_json"] else []

        generated_df = cargar_plan_15_dias(selected_id)

        if generated_df.empty:
            st.warning("Primero elige el menú favorito y genera el plan de 15 días.")
        else:
            favorite_menu = int(generated_df.iloc[0]["favorite_menu"])
            plan_data = json.loads(generated_df.iloc[0]["plan_json"])

            st.markdown(
                f'<div class="selection-banner">💗 Esta planeación fue creada dando prioridad al Menú {favorite_menu}.</div>',
                unsafe_allow_html=True,
            )

            # 🔥 NUEVO: explicación UX
            st.markdown(
                '<div class="selection-banner">✏️ Puedes personalizar tu plan cambiando el menú de cualquier día según tu rutina.</div>',
                unsafe_allow_html=True,
            )

            menu_options = [menu["menu_numero"] for menu in menus]
            edited_plan = []

            cols = st.columns(3)

            for idx, day in enumerate(plan_data):
                with cols[idx % 3]:

                    current_menu = day["menu_numero"]

                    new_menu = st.selectbox(
                        f"Día {day['dia']}",
                        menu_options,
                        index=menu_options.index(current_menu),
                        key=f"edit_day_{day['dia']}"
                    )

                    edited_plan.append({
                        "dia": day["dia"],
                        "menu_numero": new_menu
                    })

                    st.markdown(
                        f'<div class="small-muted">Menú seleccionado para este día.</div>',
                        unsafe_allow_html=True,
                    )

            # 💾 GUARDAR CAMBIOS
            if st.button("💾 Guardar mi versión personalizada", use_container_width=True):
                guardar_plan_15_dias(selected_id, favorite_menu, edited_plan)
                st.success("Plan actualizado correctamente ✨")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Lista del súper":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Lista del súper</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Checklist bonito, por categorías, y con unidades pensadas para comprar.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="note-box">Las cantidades son aproximadas para facilitar la compra en el súper. La app convierte algunas medidas de cocina como tazas, gramos y mililitros a unidades más prácticas como bolsas, paquetes, litros o kilos.</div>',
        unsafe_allow_html=True,
    )

    df = cargar_planes()
    if df.empty:
        st.info("Todavía no hay planes guardados.")
    else:
        selected_id = st.selectbox(
            "Selecciona un plan",
            df["id"].tolist(),
            format_func=lambda x: df[df["id"] == x]["nombre_plan"].values[0],
            key="shopping_selector",
        )
        row = df[df["id"] == selected_id].iloc[0]
        menus = json.loads(row["menus_json"]) if row["menus_json"] else []
        generated_df = cargar_plan_15_dias(selected_id)

        if generated_df.empty:
            st.warning("Primero genera el plan de 15 días para crear la lista del súper.")
        else:
            plan_data = json.loads(generated_df.iloc[0]["plan_json"])
            menus_by_number = {m["menu_numero"]: m for m in menus}
            shopping_df = build_shopping_list_from_plan(plan_data, menus_by_number)

            if shopping_df.empty:
                st.warning("No se pudieron detectar ingredientes automáticamente todavía.")
            else:
                shopping_df["Categoría"] = shopping_df["Ingrediente"].apply(categorize_ingredient)
                total_items = len(shopping_df)
                done = 0

                for _, item in shopping_df.iterrows():
                    state_key = f"check_{selected_id}_{item['Ingrediente']}_{item['Unidad']}"
                    if st.session_state.shopping_checks.get(state_key, False):
                        done += 1

                st.progress(done / total_items if total_items else 0)
                st.caption(f"{done} de {total_items} ingredientes comprados")

                categorias_orden = [
                    "Proteínas y lácteos",
                    "Quesos",
                    "Frutas",
                    "Verduras y extras",
                    "Cereales y panes",
                    "Condimentos y complementos",
                    "Otros",
                ]

                for categoria in categorias_orden:
                    subset = shopping_df[shopping_df["Categoría"] == categoria].copy()
                    if subset.empty:
                        continue

                    st.markdown(f'<div class="check-category">🧺 {categoria}</div>', unsafe_allow_html=True)

                    for _, item in subset.iterrows():
                        state_key = f"check_{selected_id}_{item['Ingrediente']}_{item['Unidad']}"
                        current_value = st.session_state.shopping_checks.get(state_key, False)
                        display_qty = f"{item['Cantidad total']} {item['Unidad']}"
                        box_class = "check-item-done" if current_value else "check-item"

                        cbox, cinfo = st.columns([0.12, 0.88])
                        with cbox:
                            new_value = st.checkbox("", value=current_value, key=f"ui_{state_key}")
                            st.session_state.shopping_checks[state_key] = new_value

                        with cinfo:
                            applied_class = "check-item-done" if new_value else box_class
                            name = item["Ingrediente"]
                            if new_value:
                                name = f"<s>{name}</s>"

                            st.markdown(
                                f'<div class="{applied_class}"><div class="check-name">{name}</div><div class="check-qty">{display_qty}</div></div>',
                                unsafe_allow_html=True,
                            )

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Ejercicio":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Registro de ejercicio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Aquí puedes registrar los ejercicios que vas haciendo para llevar mejor tu progreso.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="selection-banner">🏋️‍♀️ Registra el nombre del ejercicio, el peso usado y la fecha. No importa si lo capturas después del día en que lo hiciste.</div>',
        unsafe_allow_html=True,
    )

    nombre_ejercicio = st.text_input(
        "Nombre del ejercicio",
        placeholder="Ej. Sentadilla Smith"
    )

    col1, col2 = st.columns(2)

    with col1:
        peso = st.number_input(
            "Peso",
            min_value=0.0,
            value= None,
            placeholder="Ej. 20",
            step=0.5,
        )

    with col2:
        unidad = st.selectbox(
            "Unidad",
            ["kg", "lbs"]
        )

    fecha_ejercicio = st.date_input("Fecha del ejercicio")

    notas = st.text_area(
        "Notas (opcional)",
        placeholder="Ej. Me costó más esta serie, subí peso, etc."
    )
            
    if st.button("💾 Guardar entrenamiento", use_container_width=True):
        if not nombre_ejercicio.strip():
            st.warning("Escribe el nombre del ejercicio.")
        elif peso == 0:
            st.warning("Agrega un peso válido.")
        else:
            guardar_ejercicio(
                nombre_ejercicio=nombre_ejercicio.strip(),
                peso=peso,
                unidad=unidad,
                fecha_ejercicio=fecha_ejercicio,
                notas=notas.strip()
            )
            registrar_evento("ejercicio_guardado", nombre_ejercicio.strip())
            st.success("Ejercicio guardado correctamente ✨")

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Historial":
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title" style="margin-top:0;">Historial de planes</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Consulta tus planes guardados, revisa menús y administra archivos.</div>', unsafe_allow_html=True)

    df = cargar_planes()
    if df.empty:
        st.info("Todavía no hay planes guardados.")
    else:
        for _, row in df.iterrows():
            menus = json.loads(row["menus_json"]) if row["menus_json"] else []

            with st.expander(f"📁 {row['nombre_plan']} · {row['fecha']}", expanded=False):
                st.write(f"**Total de menús:** {len(menus)}")

                tabs = st.tabs([f"Menú {i + 1}" for i in range(len(menus))]) if menus else []
                for i, menu in enumerate(menus):
                    with tabs[i]:
                        render_menu(menu)

                col1, col2 = st.columns(2)

                with col1:
                    if row["pdf_path"]:
                        try:
                            with open(row["pdf_path"], "rb") as f:
                                st.download_button(
                                    label="📄 Descargar PDF",
                                    data=f,
                                    file_name=os.path.basename(row["pdf_path"]),
                                    mime="application/pdf",
                                    key=f"pdf_{row['id']}",
                                    use_container_width=True,
                                )
                        except Exception:
                            st.warning("No se pudo abrir el PDF guardado.")

                with col2:
                    if st.button("🗑️ Eliminar plan", key=f"del_{row['id']}", use_container_width=True):
                        eliminar_plan(row["id"])
                        registrar_evento("plan_eliminado", row["nombre_plan"])
                        st.success("Plan eliminado.")
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

elif opcion == "Dashboard":
    st.markdown('<div class="section-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Visualizaciones separadas del historial para que todo se sienta más claro.</div>', unsafe_allow_html=True)

    df = cargar_planes()
    ej_df = cargar_ejercicios()

    tab1, tab2 = st.tabs(["🍽️ Nutrición", "🏋️‍♀️ Ejercicio"])

    # ==================== TAB NUTRICIÓN ====================
    with tab1:

        if df.empty:
            st.info("Todavía no hay datos suficientes para mostrar visualizaciones.")
        else:
            total_planes = len(df)
            total_menus = 0
            ingredient_counter = defaultdict(int)
            category_counter = defaultdict(int)

            for _, row in df.iterrows():
                menus = json.loads(row["menus_json"]) if row["menus_json"] else []
                total_menus += len(menus)

                for menu in menus:
                    for section in ["desayuno", "colacion_1", "comida", "colacion_2", "cena"]:
                        text = menu.get(section, "")
                        for ingredient, unit, qty in extract_ingredients_from_text(text):
                            ingredient_counter[ingredient] += 1
                            category_counter[categorize_ingredient(ingredient)] += 1

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f'<div class="mini-card"><div class="metric-label">Planes guardados</div><div class="metric-value">{total_planes}</div></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<div class="mini-card"><div class="metric-label">Menús totales</div><div class="metric-value">{total_menus}</div></div>',
                    unsafe_allow_html=True,
                )

            df_chart = df.copy()
            df_chart["fecha_dt"] = pd.to_datetime(df_chart["fecha"])
            planes_por_fecha = df_chart.groupby(df_chart["fecha_dt"].dt.date).size().reset_index(name="Planes")
            planes_por_fecha.columns = ["Fecha", "Planes"]

            st.markdown("### 📅 Planes guardados por fecha")
            st.dataframe(planes_por_fecha, use_container_width=True, hide_index=True)

            if ingredient_counter:
                top_ingredientes = pd.DataFrame(
                    sorted(ingredient_counter.items(), key=lambda x: x[1], reverse=True)[:10],
                    columns=["Ingrediente", "Frecuencia"],
                )
                st.markdown("### 🥑 Top 10 ingredientes más usados")
                st.bar_chart(top_ingredientes.set_index("Ingrediente"))

            if category_counter:
                top_categorias = pd.DataFrame(
                    sorted(category_counter.items(), key=lambda x: x[1], reverse=True),
                    columns=["Categoría", "Frecuencia"],
                )
                st.markdown("### 🧺 Categorías más usadas")
                st.bar_chart(top_categorias.set_index("Categoría"))

            generated_rows = []
            for plan_id in df["id"].tolist():
                generated_df = cargar_plan_15_dias(plan_id)
                if not generated_df.empty:
                    plan_data = json.loads(generated_df.iloc[0]["plan_json"])
                    generated_rows.extend(plan_data)

            if generated_rows:
                freq = pd.DataFrame(generated_rows)["menu_numero"].value_counts().sort_index().rename_axis("Menú").reset_index(name="Frecuencia")
                freq["Menú"] = freq["Menú"].astype(str).apply(lambda x: f"Menú {x}")
                st.markdown("### 🍽️ Frecuencia de menús en las planeaciones de 15 días")
                st.bar_chart(freq.set_index("Menú"))

            favorite_counter = defaultdict(int)

            for plan_id in df["id"].tolist():
                generated_df = cargar_plan_15_dias(plan_id)
                if not generated_df.empty:
                    fav = int(generated_df.iloc[0]["favorite_menu"])
                    favorite_counter[fav] += 1

            if favorite_counter:
                fav_df = pd.DataFrame(
                    sorted(favorite_counter.items(), key=lambda x: x[1], reverse=True),
                    columns=["Menú", "Veces seleccionado"]
                )

                fav_df["Menú"] = fav_df["Menú"].apply(lambda x: f"Menú {x}")

                st.markdown("### 💗 Menús favoritos más seleccionados")
                st.bar_chart(fav_df.set_index("Menú"))

    # ==================== TAB EJERCICIO ====================
    with tab2:

        st.markdown("## 🏋️‍♀️ Progreso de ejercicio")

        if ej_df.empty:
            st.info("Aún no hay ejercicios registrados.")
        else:
            ej_df["fecha"] = pd.to_datetime(ej_df["fecha"])

            ejercicio_sel = st.selectbox(
                "Selecciona un ejercicio",
                sorted(ej_df["nombre_ejercicio"].unique())
            )

            df_filtrado = ej_df[ej_df["nombre_ejercicio"] == ejercicio_sel].copy()
            df_filtrado = df_filtrado.sort_values("fecha")

            # 🔥 selector kg / lbs
            unidad_vista = st.radio("Unidad de visualización:", ["kg", "lbs"], horizontal=True)

            if unidad_vista == "kg":
                valores = df_filtrado["peso_kg"]
            else:
                valores = df_filtrado["peso_kg"] / 0.453592

            st.markdown("### 📈 Progreso de peso")
            st.line_chart(
                df_filtrado.assign(peso=valores).set_index("fecha")["peso"]
            )

            st.markdown("### 📊 Frecuencia de ejercicios")
            freq = ej_df["nombre_ejercicio"].value_counts().sort_values(ascending=False)
            st.bar_chart(freq)

if st.session_state.show_dev:
    st.markdown("---")
    st.markdown('<div class="section-title">Modo desarrolladora</div>', unsafe_allow_html=True)
    password = st.text_input("Contraseña de desarrolladora", type="password")

    if password == DEVELOPER_PASSWORD:
        logs = cargar_logs()
        if logs.empty:
            st.info("Aún no hay eventos registrados desde el dominio público.")
        else:
            st.dataframe(logs, use_container_width=True)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total eventos", len(logs))
            with col2:
                st.metric("Último evento", logs.iloc[0]["timestamp"])

            logs["date"] = pd.to_datetime(logs["timestamp"]).dt.date
            eventos_por_dia = logs.groupby("date").size()
            st.bar_chart(eventos_por_dia, use_container_width=True)

    elif password:
        st.warning("Contraseña incorrecta.")

st.caption("💾 Datos guardados en MongoDB Atlas")
