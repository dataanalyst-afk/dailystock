import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Inventory Dashboard",
    page_icon="📊",
    layout="wide"
)

# ---------------- CSS ----------------
st.markdown("""
<style>
.metric-box {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "raw_data" not in st.session_state:
    st.session_state.raw_data = None
if "clean_data" not in st.session_state:
    st.session_state.clean_data = None
if "filename" not in st.session_state:
    st.session_state.filename = None

# ---------------- HELPERS ----------------
def is_date_column(col):
    try:
        pd.to_datetime(col)
        return True
    except:
        return False

def smart_transform(df):
    """
    Converts wide inventory sheet into clean long format
    """
    df = df.copy()

    # Rename columns to string
    df.columns = df.columns.astype(str)

    # Drop category header rows (Opening Stock missing)
    opening_col = [c for c in df.columns if "opening" in c.lower()][0]
    df = df[df[opening_col].notna()]

    # Detect date columns
    date_cols = [c for c in df.columns if is_date_column(c)]

    # Identify item column
    item_col = [c for c in df.columns if "item" in c.lower()][0]

    # Melt (wide → long)
    long_df = df.melt(
        id_vars=[item_col],
        value_vars=date_cols,
        var_name="Date",
        value_name="Stock"
    )

    long_df["Date"] = pd.to_datetime(long_df["Date"], errors="coerce")
    long_df["Stock"] = pd.to_numeric(long_df["Stock"], errors="coerce")

    long_df.dropna(subset=["Date", "Stock"], inplace=True)

    return long_df.rename(columns={item_col: "Item"})

# ---------------- MAIN ----------------
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Upload Data", "Dashboard"])

    if page == "Upload Data":
        upload_page()
    else:
        dashboard_page()

# ---------------- UPLOAD ----------------
def upload_page():
    st.title("📂 Upload Inventory File")

    file = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"])

    if file:
        try:
            df = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)

            st.session_state.raw_data = df
            st.session_state.clean_data = smart_transform(df)
            st.session_state.filename = file.name

            st.success("File processed successfully ✅")

            st.subheader("Preview (Cleaned Data)")
            st.dataframe(st.session_state.clean_data.head(20), use_container_width=True)

        except Exception as e:
            st.error(f"Processing error: {e}")

# ---------------- DASHBOARD ----------------
def dashboard_page():
    st.title("📊 Smart Inventory Dashboard")

    if st.session_state.clean_data is None:
        st.warning("Please upload data first.")
        st.stop()

    df = st.session_state.clean_data.copy()

    # -------- SIDEBAR FILTERS --------
    st.sidebar.header("Filters")

    selected_date = st.sidebar.date_input(
        "Select Date",
        value=df["Date"].max().date(),
        min_value=df["Date"].min().date(),
        max_value=df["Date"].max().date()
    )

    items = sorted(df["Item"].unique())
    selected_items = st.sidebar.multiselect("Select Items", items, default=items)

    df = df[
        (df["Date"].dt.date == selected_date) &
        (df["Item"].isin(selected_items))
    ]

    # -------- KPIs --------
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items", df["Item"].nunique())
    c2.metric("Total Stock", int(df["Stock"].sum()))
    c3.metric("Low Stock Items (<10)", int((df["Stock"] < 10).sum()))

    # -------- TABLE --------
    st.markdown("### Inventory Snapshot")
    st.dataframe(
        df.sort_values("Stock"),
        use_container_width=True
    )

    # -------- DOWNLOAD --------
    st.download_button(
        "Download View as CSV",
        df.to_csv(index=False).encode("utf-8"),
        "inventory_snapshot.csv",
        "text/csv"
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
