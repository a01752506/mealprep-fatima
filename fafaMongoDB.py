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
st.markdown(
    """
    <style>
    :root {
        --bg: #FFF8FB;
        --card: #FFFFFF;
        --border: #F0D9E2;
        --text: #2E2430;
        --muted: #7D6872;
        --accent: #EBC7D4;
        --accent-strong: #DFA8BC;
        --accent-soft: #FAEEF3;
    }

    .stApp {
        background: linear-gradient(180deg, #FFF8FB 0%, #FFFDFD 100%);
        color: var(--text);
    }

    section[data-testid="stSidebar"] {
        background: #FFFDFE;
        border-right: 1px solid var(--border);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }

    .hero-title {
        font-size: 2.85rem;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.04em;
        margin-bottom: 0.25rem;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: 1.05rem;
        margin-bottom: 1.6rem;
    }

    .soft-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 1.25rem;
        box-shadow: 0 10px 30px rgba(223, 168, 188, 0.10);
        margin-bottom: 1rem;
    }

    .mini-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid var(--border);
        border-radius: 22px;
        padding: 1.05rem 1.15rem;
        box-shadow: 0 6px 22px rgba(223, 168, 188, 0.08);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.92rem;
        margin-bottom: 0.2rem;
    }

    .metric-value {
        color: var(--text);
        font-size: 1.8rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: var(--text);
        margin: 1rem 0 0.65rem 0;
    }

    .section-subtitle {
        color: var(--muted);
        margin-bottom: 1rem;
    }

    .menu-preview {
        background: #FFFDFE;
        border: 1px solid #F3E3EA;
        border-radius: 18px;
        padding: 1rem;
        margin-top: 0.7rem;
    }

    .meal-title {
        font-size: 0.98rem;
        font-weight: 700;
        color: var(--text);
        margin-top: 0.7rem;
        margin-bottom: 0.2rem;
    }

    .small-muted {
        color: var(--muted);
        font-size: 0.93rem;
        line-height: 1.55;
    }

    .question-wrap {
        text-align: center;
        padding: 1.2rem 0.6rem 0.8rem 0.6rem;
    }

    .question-title {
        font-size: 2rem;
        font-weight: 800;
        color: var(--text);
        margin-bottom: 0.35rem;
        letter-spacing: -0.03em;
    }

    .question-subtitle {
        color: var(--muted);
        font-size: 1rem;
        max-width: 720px;
        margin: 0 auto;
        line-height: 1.55;
    }

    .menu-card-selected {
        background: linear-gradient(180deg, #FFF8FB 0%, #FFF1F6 100%);
        border: 2px solid var(--accent-strong);
        border-radius: 24px;
        padding: 1.1rem;
        box-shadow: 0 12px 30px rgba(223, 168, 188, 0.18);
        margin-bottom: 1rem;
    }

    .menu-card-default {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 1.1rem;
        box-shadow: 0 8px 24px rgba(223, 168, 188, 0.08);
        margin-bottom: 1rem;
    }

    .tag {
        display: inline-block;
        background: var(--accent-soft);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 999px;
        padding: 0.28rem 0.68rem;
        font-size: 0.84rem;
        margin-right: 0.35rem;
        margin-bottom: 0.4rem;
    }

    .selection-banner {
        background: linear-gradient(90deg, #FBEAF1 0%, #FFF7FA 100%);
        border: 1px solid var(--accent-strong);
        border-radius: 18px;
        padding: 0.95rem 1rem;
        margin: 1rem 0 1.2rem 0;
        color: var(--text);
        font-weight: 700;
    }

    .day-card {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1rem;
        min-height: 112px;
        box-shadow: 0 6px 18px rgba(223, 168, 188, 0.08);
        margin-bottom: 0.9rem;
    }

    .day-label {
        color: var(--muted);
        font-size: 0.86rem;
        margin-bottom: 0.2rem;
    }

    .day-menu {
        font-size: 1rem;
        font-weight: 800;
        color: var(--text);
        margin-bottom: 0.3rem;
    }

    .check-category {
        font-size: 1.12rem;
        font-weight: 800;
        color: var(--text);
        margin: 1.1rem 0 0.65rem 0;
        padding-top: 0.25rem;
    }

    .check-item {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.55rem;
        box-shadow: 0 4px 14px rgba(223, 168, 188, 0.06);
    }

    .check-item-done {
        background: #FBF6F8;
        border: 1px solid #E9D7DE;
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.55rem;
        opacity: 0.75;
    }

    .check-name {
        font-weight: 700;
        color: var(--text);
        margin-bottom: 0.1rem;
    }

    .check-qty {
        color: var(--muted);
        font-size: 0.9rem;
    }

    .note-box {
        background: #FFF7FA;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 0.85rem 1rem;
        color: var(--muted);
        font-size: 0.92rem;
        margin-bottom: 1rem;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        background: #FFFFFF !important;
        color: var(--text) !important;
        font-weight: 700 !important;
        box-shadow: 0 6px 18px rgba(223, 168, 188, 0.08) !important;
        min-height: 2.9rem !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--accent-soft) !important;
        border-color: var(--accent-strong) !important;
    }

    .stRadio > div {
        gap: 0.7rem;
    }

    div[data-baseweb="select"] > div,
    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        border-radius: 14px !important;
        border: 1px solid var(--border) !important;
        background: #FFFFFF !important;
    }

    .stProgress > div > div > div > div {
        background-color: #E5AFC3 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# ==================== SESION ====================
def init_session_state():
    defaults = {
    "authenticated": False,
    "show_dev": False,
    "selected_favorite_by_plan": {},
    "shopping_checks": {},
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
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        maxPoolSize=10
    )
    client.admin.command("ping")
    return client[MONGO_DB_NAME]

db = get_mongo_db()

menu_sets_collection = db["menu_sets"]
usage_logs_collection = db["usage_logs"]
generated_plans_collection = db["generated_plans"]


def registrar_evento(tipo: str, detalle: str):
    usage_logs_collection.insert_one({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tipo": tipo,
        "detalle": detalle,
        "accedido_desde": "streamlit_cloud",
    })


def guardar_plan(nombre_plan, pdf_path, menus_json):
    menu_sets_collection.insert_one({
        "nombre_plan": nombre_plan,
        "pdf_path": pdf_path,
        "menus_json": menus_json,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()


@st.cache_data(ttl=30)
def cargar_planes():
    docs = list(menu_sets_collection.find().sort("fecha", -1))
    if not docs:
        return pd.DataFrame(columns=["id", "nombre_plan", "pdf_path", "menus_json", "fecha"])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)


def eliminar_plan(plan_id):
    menu_sets_collection.delete_one({"_id": ObjectId(plan_id)})
    generated_plans_collection.delete_many({"menu_set_id": plan_id})
    st.cache_data.clear()


@st.cache_data(ttl=30)
def cargar_logs():
    docs = list(usage_logs_collection.find().sort("timestamp", -1))
    if not docs:
        return pd.DataFrame(columns=["timestamp", "tipo", "detalle", "accedido_desde"])

    for doc in docs:
        doc["id"] = str(doc["_id"])

    return pd.DataFrame(docs)


def guardar_plan_15_dias(menu_set_id, favorite_menu, plan_data):
    generated_plans_collection.delete_many({"menu_set_id": menu_set_id})

    generated_plans_collection.insert_one({
        "menu_set_id": menu_set_id,
        "favorite_menu": favorite_menu,
        "plan_json": json.dumps(plan_data, ensure_ascii=False),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    st.cache_data.clear()


@st.cache_data(ttl=30)
def cargar_plan_15_dias(menu_set_id):
    docs = list(
        generated_plans_collection.find({"menu_set_id": menu_set_id}).sort("created_at", -1).limit(1)
    )

    if not docs:
        return pd.DataFrame(columns=["menu_set_id", "favorite_menu", "plan_json", "created_at"])

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

    counts = {num: 3 for num in menu_numbers}
    counts[favorite_menu_number] += 3

    total = sum(counts.values())

    while total < 15:
        for num in menu_numbers:
            if total < 15:
                counts[num] += 1
                total += 1

    while total > 15:
        for num in menu_numbers:
            if num != favorite_menu_number and counts[num] > 1 and total > 15:
                counts[num] -= 1
                total -= 1

    sequence = []
    for num, qty in counts.items():
        sequence.extend([num] * qty)

    rng = random.Random(seed)
    rng.shuffle(sequence)

    return [{"dia": i + 1, "menu_numero": menu_number} for i, menu_number in enumerate(sequence[:15])]

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
            "Historial",
            "Dashboard",
        ],
    )

    st.session_state.show_dev = st.checkbox(
        "Mostrar modo desarrolladora",
        value=st.session_state.show_dev
    )

# ==================== HEADER ====================
st.markdown('<div class="hero-title">Meal Prep Planner</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Sube la dieta, pregúntale a Fátima cuál es su menú favorito y convierte la planeación en una lista del súper mucho más útil.</div>',
    unsafe_allow_html=True,
)

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

        if not menus_extraidos:
            st.error("No se detectaron menús en el PDF.")
        else:
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
    st.markdown('<div class="section-subtitle">Aquí solo ves la planeación ya armada, sin saturar la pantalla de selección.</div>', unsafe_allow_html=True)

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

            cols = st.columns(3)
            for idx, day in enumerate(plan_data):
                with cols[idx % 3]:
                    st.markdown(
                        f'<div class="day-card"><div class="day-label">Día {day["dia"]}</div><div class="day-menu">Menú {day["menu_numero"]}</div><div class="small-muted">Distribución sugerida para que la planeación se sienta balanceada y práctica.</div></div>',
                        unsafe_allow_html=True,
                    )

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

elif opcion == "Historial":
    st.markdown('<div class="section-title">Historial de planes</div>', unsafe_allow_html=True)
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

        if not planes_por_fecha.empty:
            st.markdown("### 📈 Planes guardados por fecha")

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
