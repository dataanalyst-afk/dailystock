import streamlit as st
import pandas as pd

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Smart Inventory Dashboard",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# CONFIG
# =========================================================
CAFE_LINKS = {
    "Nayakka": "https://docs.google.com/spreadsheets/d/1_oZ-d0r17HOGHlK-MoZSeoxvBrZKCZFj/edit#gid=0",
    "BSC Andheri": "https://docs.google.com/spreadsheets/d/1G-rHEstSh5JkkLKWDXzrpZYyysL9Li-X/edit#gid=1034438827"
}

# =========================================================
# SESSION STATE
# =========================================================
for key in ["clean_data", "filename"]:
    if key not in st.session_state:
        st.session_state[key] = None

# =========================================================
# SMART TRANSFORM
# =========================================================
def smart_transform(df):
    """
    Supports BOTH:
    1) LONG format  -> Date | Item | Stock
    2) WIDE format  -> Item | 2026-01-01 | 2026-01-02 ...
    """

    df = df.copy()
    df.columns = df.columns.astype(str)

    # ---------- CASE 1: LONG FORMAT ----------
    required = {"date", "item", "stock"}
    lower_cols = {c.lower() for c in df.columns}

    if required.issubset(lower_cols):
        rename_map = {}
        for c in df.columns:
            if c.lower() == "date":
                rename_map[c] = "Date"
            elif c.lower() == "item":
                rename_map[c] = "Item"
            elif c.lower() == "stock":
                rename_map[c] = "Stock"

        df = df.rename(columns=rename_map)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Stock"] = pd.to_numeric(df["Stock"], errors="coerce")
        df["Item"] = df["Item"].astype(str).str.strip()

        df.dropna(subset=["Date", "Item", "Stock"], inplace=True)
        return df

    # ---------- CASE 2: WIDE FORMAT ----------
    def is_date_column(col):
        try:
            pd.to_datetime(col)
            return True
        except:
            return False

    date_cols = [c for c in df.columns if is_date_column(c)]
    if not date_cols:
        raise ValueError("No date columns or Date/Item/Stock format found")

    item_cols = [c for c in df.columns if "item" in c.lower()]
    if not item_cols:
        raise ValueError("No Item column found")

    item_col = item_cols[0]
    id_vars = [c for c in df.columns if c not in date_cols]

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=date_cols,
        var_name="Date",
        value_name="Stock"
    )

    long_df["Date"] = pd.to_datetime(long_df["Date"], errors="coerce")
    long_df["Stock"] = pd.to_numeric(long_df["Stock"], errors="coerce")
    long_df["Item"] = long_df[item_col].astype(str).str.strip()

    long_df.dropna(subset=["Date", "Item", "Stock"], inplace=True)

    return long_df[["Date", "Item", "Stock"]]

# =========================================================
# DATA LOADER
# =========================================================
@st.cache_data(ttl=600)
def load_data(url):
    if "docs.google.com/spreadsheets" in url:
        sheet_id = url.split("/d/")[1].split("/")[0]
        gid = "0"
        if "gid=" in url:
            gid = url.split("gid=")[1].split("&")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}"

    df = pd.read_csv(url)
    return smart_transform(df)

# =========================================================
# MAIN
# =========================================================
def main():
    st.sidebar.title("Navigation")
    st.sidebar.header("Data Source")

    selected_cafe = st.sidebar.selectbox(
        "Select Cafe File",
        list(CAFE_LINKS.keys())
    )

    try:
        st.session_state.clean_data = load_data(CAFE_LINKS[selected_cafe])
        st.session_state.filename = selected_cafe
        dashboard_page()
    except Exception as e:
        st.error("Failed to load data")
        st.exception(e)

# =========================================================
# DASHBOARD
# =========================================================
def dashboard_page():
    st.title("📊 Smart Inventory Dashboard")

    df = st.session_state.clean_data
    if df is None or df.empty:
        st.warning("No data available")
        return

    st.markdown(f"**Current Cafe:** `{st.session_state.filename}`")

    # ---------- NORMALIZE ITEM ----------
    df["Item"] = df["Item"].astype(str).str.strip()

    # ---------- SIDEBAR FILTERS ----------
    st.sidebar.header("Filters")

    # Date filter
    available_dates = sorted(df["Date"].dt.date.unique())
    selected_date = st.sidebar.selectbox(
        "Select Date",
        available_dates,
        index=len(available_dates) - 1
    )
    df = df[df["Date"].dt.date == selected_date]

    # Item filter (SAFE)
    items = sorted(df["Item"].dropna().unique())
    selected_items = st.sidebar.multiselect("Filter Items", items)
    if selected_items:
        df = df[df["Item"].isin(selected_items)]

    # Stock threshold
    threshold = st.sidebar.number_input(
        "Low Stock Threshold",
        min_value=0,
        value=10
    )

    if st.sidebar.checkbox("Show Only Low Stock"):
        df = df[df["Stock"] < threshold]

    df = df.sort_values("Stock")

    # ---------- METRICS ----------
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items", df["Item"].nunique())
    c2.metric("Total Stock", int(df["Stock"].sum()))
    c3.metric("Low Stock Items", (df["Stock"] < threshold).sum())

    # ---------- TABLE ----------
    def highlight_low(row):
        return ["background-color:#ffcccc" if row["Stock"] < threshold else "" for _ in row]

    st.dataframe(
        df.style.apply(highlight_low, axis=1)
        .format({"Stock": "{:.0f}", "Date": "{:%Y-%m-%d}"}),
        use_container_width=True
    )

    # ---------- DOWNLOAD ----------
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "inventory_snapshot.csv",
        "text/csv"
    )

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    main()
