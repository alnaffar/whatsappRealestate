import streamlit as st
import pandas as pd
import re
from dateutil import parser
from io import BytesIO
import chardet

# === Classifier Functions ===
def classify_message(msg):
    categories = {
        "rent": ["for rent", "looking for rent", "available for rent", "rent price", "للإيجار"],
        "sell": ["for sale", "available for sale", "sale price", "selling price", "للبيع"],
        "buyer": ["looking for", "need", "want to buy", "client ready", "cash buyer", "ready to sign", "looking for hot deal", "looking hot deal", "مشتري"],
        "request": ["anyone have", "does anyone", "please pm", "dm me", "kindly dm", "share with me", "حد عنده"]
    }
    tags = []
    lower_msg = msg.lower()
    for category, keywords in categories.items():
        if any(keyword in lower_msg for keyword in keywords):
            tags.append(category)
    return ", ".join(tags) if tags else "uncategorized"

def extract_unit_type(message):
    msg = message.lower()
    if "hospital" in msg or "مستشفى" in msg: return "hospital"
    if "clinic" in msg or "عيادة" in msg: return "clinic"
    if "school" in msg or "مدرسة" in msg: return "school"
    if "studio" in msg or "استوديو" in msg: return "studio"
    if "villa" in msg or "فيلا" in msg: return "villa"
    for n in range(1, 6):
        if re.search(rf"\b{n}\s*(br|bhk|bed(room)?|bedrooms?)\b", msg): return f"{n} bedrooms"
    return "unknown"

def extract_date(msg):
    try:
        return str(parser.parse(msg, fuzzy=True).date())
    except:
        return "no date"

# === Message Parsing with Multiple Format Support ===
def parse_chat_lines(text):
    pattern_dash = re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{4})[, ]\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*[\u202f\s]?(am|pm)?\s*[-–—]\s*(.*?):\s(.+)$",
        re.IGNORECASE
    )
    pattern_bracket = re.compile(
        r"^\[(\d{1,2}/\d{1,2}/\d{4})[ ,]*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*?):\s(.+)$",
        re.IGNORECASE
    )

    messages = []
    for line in text.splitlines():
        line = line.strip()
        match1 = pattern_dash.match(line)
        match2 = pattern_bracket.match(line)

        if match1:
            date, time, ampm, sender, msg = match1.groups()
            timestamp_str = f"{date} {time} {ampm or ''}"
        elif match2:
            date, time, sender, msg = match2.groups()
            timestamp_str = f"{date} {time}"
        else:
            continue

        try:
            timestamp = parser.parse(timestamp_str, fuzzy=True, dayfirst=True)
            messages.append((str(timestamp), sender.strip(), msg.strip()))
        except Exception:
            continue
    return messages

# === Streamlit App UI ===
st.set_page_config(page_title="WhatsApp Real Estate Classifier", layout="wide")
st.title("🏘️ WhatsApp Real Estate Classifier - Multi Format Support")

uploaded_file = st.file_uploader("📄 Upload WhatsApp Chat (.txt)", type="txt")

if uploaded_file:
    raw = uploaded_file.read()
    enc = chardet.detect(raw)['encoding']
    text = raw.decode(enc, errors='ignore').replace("â€¯", " ").replace("  ", " ")

    messages = parse_chat_lines(text)

    if not messages:
        st.warning("⚠️ No messages matched supported formats.")
    else:
        df = pd.DataFrame(messages, columns=["timestamp", "sender", "message"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["date_only"] = df["timestamp"].dt.date
        df["category"] = df["message"].apply(classify_message)
        df["unit_type"] = df["message"].apply(extract_unit_type)
        df["date_mentioned"] = df["message"].apply(extract_date)

        st.success(f"✅ {len(df)} messages parsed successfully!")
        st.dataframe(df.head(30), use_container_width=True)

        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        st.download_button(
            label="📥 Download Classified Excel",
            data=output.getvalue(),
            file_name="classified_messages.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
