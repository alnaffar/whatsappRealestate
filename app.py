import streamlit as st
import pandas as pd
import re
from io import BytesIO
from dateutil import parser
import chardet

# === Classifier functions ===
def classify_message(msg):
    categories = {
        "rent": [
            "for rent", "available for rent", "looking for rent", "rent price",
            "للإيجار", "متاح للإيجار", "ابحث عن إيجار", "سعر الإيجار"
        ],
        "sell": [
            "for sale", "available for sale", "selling price", "sale price",
            "للبيع", "متاح للبيع", "سعر البيع"
        ],
        "buyer": [
            "looking for", "need", "want to buy", "client ready", "cash buyer", "ready to sign", "hot deal",
            "أبحث عن", "محتاج", "عميل جاهز", "مشتري جاد", "صفقة ساخنة", "مستعد للتوقيع"
        ],
        "request": [
            "anyone have", "does anyone", "please pm", "dm me", "kindly dm", "share with me",
            "حد عنده", "حد يعرف", "الرجاء التواصل", "راسلني", "من فضلك أرسل"
        ]
    }
    tags = []
    lower_msg = msg.lower()
    for category, keywords in categories.items():
        if any(keyword in lower_msg for keyword in keywords):
            tags.append(category)
    return ", ".join(tags) if tags else "uncategorized"

def extract_unit_type(message):
    msg = message.lower()
    if any(w in msg for w in ["hospital", "مستشفى"]): return "hospital"
    if any(w in msg for w in ["clinic", "عيادة"]): return "clinic"
    if any(w in msg for w in ["school", "مدرسة"]): return "school"
    if any(w in msg for w in ["studio", "استوديو"]): return "studio"
    if any(w in msg for w in ["villa", "فيلا"]): return "villa"

    word_to_num = {
        "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
        "واحد": "1", "اثنين": "2", "ثلاث": "3", "أربع": "4", "خمس": "5"
    }
    for number in range(1, 6):
        if re.search(rf"\\b{number}\\s*(br|bhk|bed(room)?|bedrooms?)\\b", msg):
            return f"{number} bedrooms"
    for word, digit in word_to_num.items():
        if re.search(rf"\\b{word}\\s*(br|bhk|bed(room)?|bedrooms?)\\b", msg):
            return f"{digit} bedrooms"
        if re.search(rf"{digit}\\s*(غرفة|غرف)", msg):
            return f"{digit} bedrooms"

    return "unknown"

def extract_date(message):
    match = re.search(r"\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}", message)
    if match:
        try:
            return str(parser.parse(match.group(0), dayfirst=True).date())
        except:
            return "no date"
    return "no date"

# === Streamlit UI ===
st.title("🏘️ WhatsApp Real Estate Classifier (Android + iPhone Support)")

uploaded_file = st.file_uploader("📄 Upload WhatsApp Chat (.txt)", type="txt")

if uploaded_file:
    raw_bytes = uploaded_file.read()
    encoding_guess = chardet.detect(raw_bytes)
    chat_text = raw_bytes.decode(encoding_guess["encoding"], errors="ignore")

    pattern = re.compile(
        r"^(\\d{1,2}/\\d{1,2}/\\d{4}),\\s*(\\d{1,2}:\\d{2})[\\u202f\\s]?(am|pm)?\\s*-\\s*(.*?):\\s(.+)",
        re.IGNORECASE
    )

    messages = []
    for line in chat_text.splitlines():
        match = pattern.match(line.strip())
        if match:
            date, time, ampm, sender, msg = match.groups()
            timestamp = f"{date} {time} {ampm or ''}"
            messages.append((timestamp.strip(), sender.strip(), msg.strip()))

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

        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        st.download_button(
            "📥 Download Excel",
            data=output.getvalue(),
            file_name="classified_messages.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
