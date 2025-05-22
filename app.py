import streamlit as st
import pandas as pd
import re
from io import BytesIO
from dateutil import parser
import chardet

# === Classifier functions ===
def classify_message(msg):
    categories = {
        "rent": ["for rent", "available for rent", "looking for rent", "rent price", "للإيجار"],
        "sell": ["for sale", "available for sale", "selling price", "sale price", "للبيع"],
        "buyer": ["looking for", "need", "want to buy", "client ready", "cash buyer", "ready to sign", "hot deal", "مشتري"],
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

    for i in range(1, 6):
        if re.search(rf"\b{i}\s*(br|bhk|bed(room)?|bedrooms?)\b", msg): return f"{i} bedrooms"
    return "unknown"

def extract_date(message):
    match = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", message)
    if match:
        try:
            return str(parser.parse(match.group(0), dayfirst=True).date())
        except:
            return "no date"
    return "no date"

# === Streamlit UI ===
st.title("🏘️ WhatsApp Real Estate Classifier")

uploaded_file = st.file_uploader("📄 Upload WhatsApp Chat (.txt)", type="txt")

if uploaded_file:
    raw_bytes = uploaded_file.read()
    encoding = chardet.detect(raw_bytes)['encoding']
    chat_text = raw_bytes.decode(encoding, errors="ignore")

    messages = []

    pattern1 = re.compile(r"\[(\d{1,2}/\d{1,2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (.*?): (.+)")
    pattern2 = re.compile(r"(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2})[\u202f\s]?(am|pm)? - (.*?): (.+)", re.IGNORECASE)

    for line in chat_text.splitlines():
        m1 = pattern1.match(line)
        m2 = pattern2.match(line)
        if m1:
            date, time, sender, message = m1.groups()
            timestamp = f"{date} {time}"
            messages.append((timestamp, sender, message))
        elif m2:
            date, time, am_pm, sender, message = m2.groups()
            timestamp = f"{date} {time} {am_pm or ''}"
            messages.append((timestamp, sender, message))

    if not messages:
        st.warning("⚠️ No messages matched the expected formats.")
    else:
        df = pd.DataFrame(messages, columns=["timestamp", "sender", "message"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%m/%Y %I:%M %p", errors="coerce")
        df["date_only"] = df["timestamp"].dt.date
        df["category"] = df["message"].apply(classify_message)
        df["unit_type"] = df["message"].apply(extract_unit_type)
        df["date_mentioned"] = df["message"].apply(extract_date)

        st.success("✅ Chat processed successfully!")
        st.dataframe(df.head(10))

        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        st.download_button("📥 Download Excel", data=output.getvalue(), file_name="classified_messages.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
