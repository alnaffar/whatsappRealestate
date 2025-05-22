import streamlit as st
import pandas as pd
import re
from io import BytesIO
from dateutil import parser

# === Classifier functions ===
def classify_message(msg):
    categories = {
        "rent": ["for rent", "looking for rent", "available for rent", "rent price"],
        "sell": ["for sale", "available for sale", "sale price", "selling price"],
        "buyer": ["looking for", "need", "want to buy", "client ready", "cash buyer", "ready to sign", "looking for hot deal", "looking hot deal"],
        "request": ["anyone have", "does anyone", "please pm", "dm me", "kindly dm", "share with me"]
    }
    tags = []
    lower_msg = msg.lower()
    for category, keywords in categories.items():
        if any(keyword in lower_msg for keyword in keywords):
            tags.append(category)
    return ", ".join(tags) if tags else "uncategorized"

def extract_unit_type(message):
    msg = message.lower()
    if "hospital" in msg:
        return "hospital"
    elif "clinic" in msg:
        return "clinic"
    elif "school" in msg:
        return "school"
    elif "studio" in msg:
        return "studio"

    word_to_num = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}
    for number in range(1, 6):
        if re.search(rf"\b{number}\s*(br|bhk|bed(room)?|bedrooms?)\b", msg):
            return f"{number} bedrooms"
    for word, digit in word_to_num.items():
        if re.search(rf"\b{word}\s*(br|bhk|bed(room)?|bedrooms?)\b", msg):
            return f"{digit} bedrooms"
    if "villa" in msg:
        return "villa"
    return "unknown"

def extract_date(message):
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}(st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,]?\s+\d{2,4}\b",
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}\b"
    ]
    for pattern in date_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                return str(parser.parse(match.group(0), fuzzy=True).date())
            except:
                continue
    return "no date"

# === Streamlit UI ===
st.title("🏘️ WhatsApp Real Estate Classifier – Multi Format")

uploaded_file = st.file_uploader("Upload WhatsApp Chat (.txt)", type="txt")

if uploaded_file:
    chat_text = uploaded_file.read().decode("utf-8")

    # Define multiple timestamp regex formats
    patterns = [
        re.compile(r"\[(\d{1,2}/\d{1,2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (.*?): (.+)"),  # [dd/mm/yyyy hh:mm:ss] Name: msg
        re.compile(r"(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2})\s?(am|pm)? - (.*?): (.+)", re.IGNORECASE),  # dd/mm/yyyy, hh:mm am - Name: msg
    ]

    messages = []

    for line in chat_text.splitlines():
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                messages.append(match.groups())
                break

    if not messages:
        st.warning("⚠️ No messages matched the expected patterns. Please check the file format.")
    else:
        # Handle different formats by length
        if len(messages[0]) == 4:
            df = pd.DataFrame(messages, columns=["date", "time", "sender", "message"])
            df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        elif len(messages[0]) == 5:
            df = pd.DataFrame(messages, columns=["date", "time", "am_pm", "sender", "message"])
            df["timestamp"] = pd.to_datetime(df["date"] + " " + df["time"] + " " + df["am_pm"].fillna(""), format="%d/%m/%Y %I:%M %p", errors="coerce")

        df["date_only"] = df["timestamp"].dt.date

        # Apply extractions
        df["category"] = df["message"].apply(classify_message)
        df["unit_type"] = df["message"].apply(extract_unit_type)
        df["date_mentioned"] = df["message"].apply(extract_date)

        st.success("✅ Chat processed successfully!")
        st.dataframe(df[["timestamp", "sender", "message", "category", "unit_type", "date_mentioned"]].head(10))

        # Excel Export
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        st.download_button(
            label="📥 Download Excel File",
            data=output.getvalue(),
            file_name="classified_messages.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
