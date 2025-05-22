import streamlit as st
import pandas as pd
import re
from io import BytesIO
from dateutil import parser
import chardet

# === Classifier Functions ===
def classify_message(msg):
    categories = {
        "rent": ["for rent", "للإيجار", "looking for rent", "available for rent", "rent price"],
        "sell": ["for sale", "للبيع", "selling price", "available for sale"],
        "buyer": ["want to buy", "cash buyer", "ready client", "hot deal", "مشتري", "looking hot deal"],
        "request": ["please pm", "dm me", "anyone have", "kindly dm", "share with me", "حد عنده", "راسلني"]
    }
    msg = msg.lower()
    tags = [cat for cat, keywords in categories.items() if any(k in msg for k in keywords)]
    return ", ".join(tags) if tags else "uncategorized"

def extract_unit_type(msg):
    msg = msg.lower()
    keywords = {
        "hospital": "hospital", "clinic": "clinic", "school": "school", "studio": "studio", "فيلا": "villa", "villa": "villa"
    }
    for k, v in keywords.items():
        if k in msg: return v
    for n in range(1, 6):
        if re.search(rf"\b{n}\s*(br|bhk|bed(room)?|bedrooms?)\b", msg): return f"{n} bedrooms"
    return "unknown"

def extract_date(message):
    match = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", message)
    if match:
        try:
            return str(parser.parse(match.group(0), dayfirst=True).date())
        except:
            pass
    return "no date"

# === Streamlit App ===
st.title("🏘️ WhatsApp Real Estate Classifier (Multi Format)")

uploaded_file = st.file_uploader("📄 Upload WhatsApp Chat (.txt)", type="txt")

if uploaded_file:
    raw = uploaded_file.read()
    enc = chardet.detect(raw)['encoding']
    text = raw.decode(enc, errors='ignore')

    pattern1 = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2})[\u202f\s]?(am|pm)? - (.*?): (.+)", re.IGNORECASE)
    pattern2 = re.compile(r"\[(\d{1,2}/\d{1,2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (.*?): (.+)")

    messages = []
    for line in text.splitlines():
        if m := pattern1.match(line):
            date, time, ampm, sender, msg = m.groups()
            ts = f"{date} {time} {ampm or ''}"
            messages.append((ts, sender, msg))
        elif m := pattern2.match(line):
            date, time, sender, msg = m.groups()
            ts = f"{date} {time}"
            messages.append((ts, sender, msg))

    if not messages:
        st.warning("⚠️ No messages matched the expected formats.")
    else:
        df = pd.DataFrame(messages, columns=["timestamp", "sender", "message"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
        df["date_only"] = df["timestamp"].dt.date
        df["category"] = df["message"].apply(classify_message)
        df["unit_type"] = df["message"].apply(extract_unit_type)
        df["date_mentioned"] = df["message"].apply(extract_date)

        st.success("✅ Chat processed successfully!")
        st.dataframe(df.head(10))

        out = BytesIO()
        df.to_excel(out, index=False, engine='openpyxl')
        st.download_button("📥 Download Excel", out.getvalue(), "classified_messages.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
