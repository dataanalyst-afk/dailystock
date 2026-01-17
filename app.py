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

    # Use the cleaned, long-format data
    df = st.session_state.clean_data.copy()
    st.markdown(f"**Current File:** `{st.session_state.filename}`")

    # --- Sidebar Filters ---
    st.sidebar.header("Filters & Settings")
    
    # 1. Date Filter (Single Day)
    # Get available dates from the data
    available_dates = sorted(df["Date"].dt.date.unique())
    if available_dates:
        selected_date = st.sidebar.selectbox(
            "Select Date", 
            available_dates, 
            index=len(available_dates)-1 # Default to latest
        )
        df = df[df["Date"].dt.date == selected_date]
    else:
        st.error("No date information found in data.")
        return

    # 2. Item Filter
    items = sorted(df["Item"].unique())
    selected_items = st.sidebar.multiselect("Filter Items (Leave empty for All)", items)
    if selected_items:
        df = df[df["Item"].isin(selected_items)]

    st.sidebar.markdown("---")
    st.sidebar.header("Stock Alerts")

    # 3. Low Stock Threshold
    threshold = st.sidebar.number_input("Low Stock Threshold", min_value=0, value=10, step=1)
    
    # 4. Low Stock Filter
    show_low_only = st.sidebar.checkbox("Show Only Low Stock Items", value=False)
    
    if show_low_only:
        df = df[df["Stock"] < threshold]

    # --- Sorting ---
    # Sort by Stock ascending so low stock items appear at the top
    df = df.sort_values("Stock", ascending=True)

    # --- Metrics ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items Listed", df["Item"].nunique())
    c2.metric("Total Stock Count", f"{df['Stock'].sum():,.0f}")
    
    low_stock_count = (df["Stock"] < threshold).sum()
    c3.metric(f"Items Below Threshold ({threshold})", low_stock_count, delta_color="inverse")

    # --- Display ---
    st.subheader("Inventory Data")
    
    # Conditional Formatting
    def highlight_low_stock(s, threshold):
        is_low = s["Stock"] < threshold
        return ['background-color: #ffcccc' if is_low else '' for _ in s]

    try:
        # Apply style
        styled_df = df.style.apply(highlight_low_stock, threshold=threshold, axis=1)
        
        # Formatting
        styled_df = styled_df.format({"Stock": "{:.0f}", "Date": "{:%Y-%m-%d}"})
        
        st.dataframe(styled_df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not apply styling: {e}")
        st.dataframe(df, use_container_width=True)

    # -------- DOWNLOAD --------
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download View as CSV",
        csv,
        "inventory_snapshot.csv",
        "text/csv"
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
