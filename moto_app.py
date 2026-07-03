import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# 1. Page Configuration & Custom CSS
st.set_page_config(
    page_title="Moto Market CZ Dashboard",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium dark theme styling with custom alarm classes
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 5px solid #3b82f6;
        margin-bottom: 15px;
    }
    .metric-card-title {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .metric-card-value {
        font-size: 2rem;
        color: #f8fafc;
        font-weight: 700;
        line-height: 1;
    }
    .metric-card-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 5px;
    }
    
    /* Alarm & Status Banners */
    .alarm-banner {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ef4444;
        margin-bottom: 15px;
        font-size: 0.95rem;
        font-weight: 500;
    }
    .ok-banner {
        background-color: #064e3b;
        color: #a7f3d0;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #10b981;
        margin-bottom: 15px;
        font-size: 0.95rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# 2. Authentication Layer
passwords = {
    "admin": "moje-tajne-admin-heslo-123",
    "recruiter": "orv-recruiter-2026",
    "guest": "renegades-26"
}

try:
    if "passwords" in st.secrets:
        passwords.update(st.secrets["passwords"])
except Exception:
    pass

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["role"] = None

# Query parameter authentication fallback
if not st.session_state["authenticated"]:
    try:
        q_params = st.query_params
        if "password" in q_params:
            pwd_param = q_params["password"]
            if pwd_param == passwords["admin"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "admin"
            elif pwd_param == passwords["recruiter"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "recruiter"
            elif pwd_param == passwords["guest"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "guest"
    except Exception:
        try:
            q_params = st.experimental_get_query_params()
            if "password" in q_params:
                pwd_param = q_params["password"][0]
                if pwd_param == passwords["admin"]:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "admin"
                elif pwd_param == passwords["recruiter"]:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "recruiter"
                elif pwd_param == passwords["guest"]:
                    st.session_state["authenticated"] = True
                    st.session_state["role"] = "guest"
        except Exception:
            pass

if not st.session_state["authenticated"]:
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("🏍️ Motorcycle Market CZ Portal")
        st.subheader("Comprehensive Analysis of Motorcycle & Scooter Markets")
        st.markdown("---")
        password_input = st.text_input("Enter access password:", type="password")
        if st.button("Enter Dashboard"):
            if password_input == passwords["admin"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "admin"
                st.rerun()
            elif password_input == passwords["recruiter"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "recruiter"
                st.rerun()
            elif password_input == passwords["guest"]:
                st.session_state["authenticated"] = True
                st.session_state["role"] = "guest"
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("Recruiter Tip: For test access, use the password provided in the portfolio presentation.")
    st.stop()

# Hide Streamlit settings and menus for recruiters and guests (visitors)
if st.session_state.get("role") in ["recruiter", "guest"]:
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        .stAppDeployButton {display: none; visibility: hidden;}
        .stDeployButton {display: none; visibility: hidden;}
        footer {visibility: hidden;}
        [data-testid="sidebar-user-menu"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# 3. Data Loading
@st.cache_data(show_spinner="Loading and cleaning registrations database...")
def load_data(filepath, file_mtime):
    # Semicolon separator in CSV
    df = pd.read_csv(filepath, sep=';')
    
    # Parse dates from Czech format
    df['Registration Date'] = pd.to_datetime(df['CZ Registration Date'], dayfirst=True)
    df['First Registration Date'] = pd.to_datetime(df['First Registration Date'], dayfirst=True)
    df['Registration Month'] = pd.to_numeric(df['CZ Registration Month'], errors='coerce').fillna(1).astype(int)
    df['Registration Year'] = pd.to_numeric(df['CZ Registration Year'], errors='coerce').fillna(2018).astype(int)
    df['Month_Col'] = df['Registration Month'].apply(lambda x: f"{x:02d}")
    df['Total seats'] = pd.to_numeric(df['Total seats'], errors='coerce').fillna(2).astype(int)
    df['Displacement'] = pd.to_numeric(df['Displacement'], errors='coerce')
    
    return df

@st.cache_data(show_spinner="Loading cancellations database...")
def load_cancellations(filepath, file_mtime):
    df = pd.read_csv(filepath, sep=';')
    df['Cancellation Date'] = pd.to_datetime(df['Cancellation Date'], dayfirst=True)
    df['First Registration Date'] = pd.to_datetime(df['First Registration Date'], dayfirst=True)
    df['Age_at_Cancellation_Months'] = (df['Cancellation Date'] - df['First Registration Date']).dt.days / 30.4375
    return df

# Load registrations
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "MOTO_Registrations_FINAL.csv")
    file_mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else 0
    df_raw = load_data(filepath, file_mtime)
except Exception as e:
    st.error(f"Failed to load registrations database. Error: {e}")
    st.stop()

min_date = df_raw['Registration Date'].min().to_pydatetime()
max_date = df_raw['Registration Date'].max().to_pydatetime()

# Extract unique filters
new_used_avail = sorted(df_raw['New/Used'].dropna().unique())
years_avail = sorted([int(y) for y in df_raw['Registration Year'].dropna().unique()], reverse=True)
months_avail = sorted([int(m) for m in df_raw['Registration Month'].dropna().unique()])
regions_avail = sorted(df_raw['Region'].dropna().unique())
colors_avail = sorted(df_raw['Color'].dropna().unique())
fuel_avail = sorted(df_raw['Fuel'].dropna().unique())
segments_avail = sorted(df_raw['Segment'].dropna().unique())
categories_avail = sorted(df_raw['Category'].dropna().astype(str).unique())
disp_order = ['> 800 ccm', '≤ 800 ccm', '≤ 500 ccm', '≤ 350 ccm', '≤ 125 ccm', '≤ 50 ccm', 'Electric', 'Unknown']
disp_avail = sorted(df_raw['Displacement Group'].dropna().unique(), key=lambda x: disp_order.index(x) if x in disp_order else 99)
seats_avail = sorted([int(s) for s in df_raw['Total seats'].dropna().unique()])
brands_avail = sorted(df_raw['Brand'].dropna().unique())
vins_avail = sorted(df_raw['VIN Prefix'].dropna().unique())

# Initialize session state filters
if "new_used_filter" not in st.session_state: st.session_state["new_used_filter"] = ['N']
if "market_base_mode" not in st.session_state: st.session_state["market_base_mode"] = "TTL Market"
if "years_filter" not in st.session_state: st.session_state["years_filter"] = []
if "months_filter" not in st.session_state: st.session_state["months_filter"] = []
if "start_date_filter" not in st.session_state: st.session_state["start_date_filter"] = min_date
if "end_date_filter" not in st.session_state: st.session_state["end_date_filter"] = max_date
if "regions_filter" not in st.session_state: st.session_state["regions_filter"] = []
if "colors_filter" not in st.session_state: st.session_state["colors_filter"] = []
if "fuel_filter" not in st.session_state: st.session_state["fuel_filter"] = []
if "segments_filter" not in st.session_state: st.session_state["segments_filter"] = []
if "categories_filter" not in st.session_state: st.session_state["categories_filter"] = []
if "disp_filter" not in st.session_state: st.session_state["disp_filter"] = []
if "seats_filter" not in st.session_state: st.session_state["seats_filter"] = []
if "brands_filter" not in st.session_state: st.session_state["brands_filter"] = []
if "models_filter" not in st.session_state: st.session_state["models_filter"] = []
if "vins_filter" not in st.session_state: st.session_state["vins_filter"] = []

def clear_all_filters():
    st.session_state["years_filter"] = []
    st.session_state["months_filter"] = []
    st.session_state["start_date_filter"] = min_date
    st.session_state["end_date_filter"] = max_date
    st.session_state["regions_filter"] = []
    st.session_state["colors_filter"] = []
    st.session_state["brands_filter"] = []
    st.session_state["models_filter"] = []
    st.session_state["vins_filter"] = []
    st.session_state["categories_filter"] = []
    st.session_state["disp_filter"] = []
    st.session_state["segments_filter"] = []
    st.session_state["seats_filter"] = []
    st.session_state["new_used_filter"] = ['N']
    st.session_state["fuel_filter"] = []
    st.session_state["market_base_mode"] = "TTL Market"

# LOO (Leave-One-Out) associative matrix for active intersections
m_time = (df_raw['Registration Date'] >= pd.to_datetime(st.session_state["start_date_filter"])) & (df_raw['Registration Date'] <= pd.to_datetime(st.session_state["end_date_filter"]))
if st.session_state["years_filter"]: m_time &= df_raw['Registration Year'].isin(st.session_state["years_filter"])
if st.session_state["months_filter"]: m_time &= df_raw['Registration Month'].isin(st.session_state["months_filter"])

base = m_time & (df_raw['New/Used'].isin(st.session_state["new_used_filter"]) if st.session_state["new_used_filter"] else True)

m_region = df_raw['Region'].isin(st.session_state["regions_filter"]) if st.session_state["regions_filter"] else True
m_color = df_raw['Color'].isin(st.session_state["colors_filter"]) if st.session_state["colors_filter"] else True
m_fuel = df_raw['Fuel'].isin(st.session_state["fuel_filter"]) if st.session_state["fuel_filter"] else True
m_segment = df_raw['Segment'].isin(st.session_state["segments_filter"]) if st.session_state["segments_filter"] else True
m_category = df_raw['Category'].isin(st.session_state["categories_filter"]) if st.session_state["categories_filter"] else True
m_disp = df_raw['Displacement Group'].isin(st.session_state["disp_filter"]) if st.session_state["disp_filter"] else True
m_seats = df_raw['Total seats'].isin(st.session_state["seats_filter"]) if st.session_state["seats_filter"] else True
m_brand = df_raw['Brand'].isin(st.session_state["brands_filter"]) if st.session_state["brands_filter"] else True
m_model = df_raw['Model'].isin(st.session_state["models_filter"]) if st.session_state["models_filter"] else True
m_vin = df_raw['VIN Prefix'].isin(st.session_state["vins_filter"]) if st.session_state["vins_filter"] else True

green_brands = set(df_raw[base & m_region & m_color & m_fuel & m_segment & m_category & m_disp & m_seats & m_model & m_vin]['Brand'].dropna().unique())
green_models = set(df_raw[base & m_region & m_color & m_fuel & m_segment & m_category & m_disp & m_seats & m_brand & m_vin]['Model'].dropna().unique())
green_segments = set(df_raw[base & m_region & m_color & m_fuel & m_category & m_disp & m_seats & m_brand & m_model & m_vin]['Segment'].dropna().unique())
green_disp = set(df_raw[base & m_region & m_color & m_fuel & m_segment & m_category & m_seats & m_brand & m_model & m_vin]['Displacement Group'].dropna().unique())
green_fuel = set(df_raw[base & m_region & m_color & m_segment & m_category & m_disp & m_seats & m_brand & m_model & m_vin]['Fuel'].dropna().unique())
green_seats = set(df_raw[base & m_region & m_color & m_fuel & m_segment & m_category & m_disp & m_brand & m_model & m_vin]['Total seats'].dropna().unique())
green_regions = set(df_raw[base & m_color & m_fuel & m_segment & m_category & m_disp & m_seats & m_brand & m_model & m_vin]['Region'].dropna().unique())
green_colors = set(df_raw[base & m_region & m_fuel & m_segment & m_category & m_disp & m_seats & m_brand & m_model & m_vin]['Color'].dropna().unique())
green_categories = set(df_raw[base & m_region & m_color & m_fuel & m_segment & m_disp & m_seats & m_brand & m_model & m_vin]['Category'].dropna().unique())

# 4. Sidebar Layout Rendering
st.sidebar.title("🛠️ Controls & Filters")

if st.sidebar.button("🧹 Clear All Filters", use_container_width=True):
    clear_all_filters()
    st.rerun()

market_base_mode = st.sidebar.radio(
    "Market Base Mode (Shares & Trends)", options=["TTL Market", "Filters based"], index=0, key="market_base_mode"
)

selected_new_used = st.sidebar.multiselect(
    "Vehicle Status (New/Used)", options=new_used_avail, default=['N'], 
    format_func=lambda x: "New (N)" if x == 'N' else "Used (O)", key="new_used_filter"
)

selected_brands = st.sidebar.multiselect(
    "Manufacturer (Brand)", options=brands_avail, default=[], 
    format_func=lambda x: f"🟢 {x}" if x in green_brands else f"⚪ {x}", key="brands_filter"
)

if selected_brands:
    models_sorted = sorted(df_raw[df_raw['Brand'].isin(selected_brands)]['Model'].dropna().unique())
else:
    models_sorted = sorted(df_raw['Model'].dropna().unique())
selected_models = st.sidebar.multiselect(
    "Commercial Model", options=models_sorted, default=[], 
    format_func=lambda x: f"🟢 {x}" if x in green_models else f"⚪ {x}", key="models_filter"
)

st.sidebar.markdown("---")

# Date & Time
with st.sidebar.expander("📅 Date & Time", expanded=True):
    _ = st.multiselect("Registration Year", options=years_avail, default=[], key="years_filter")
    _ = st.multiselect("Registration Month", options=months_avail, default=[], format_func=lambda x: f"Month {x:02d}", key="months_filter")
    start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date, key="start_date_filter")
    end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date, key="end_date_filter")

# Specifications
with st.sidebar.expander("🏍️ Specifications", expanded=True):
    selected_segments = st.multiselect(
        "Market Segment", options=segments_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_segments else f"⚪ {x}", key="segments_filter"
    )
    selected_disp = st.multiselect(
        "Engine Displacement", options=disp_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_disp else f"⚪ {x}", key="disp_filter"
    )
    selected_fuel = st.multiselect(
        "Fuel Type", options=fuel_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_fuel else f"⚪ {x}", key="fuel_filter"
    )
    selected_seats = st.multiselect(
        "Seating Capacity", options=seats_avail, default=[], 
        format_func=lambda x: f"🟢 {int(float(x))} Seat(s)" if x in green_seats else f"⚪ {int(float(x))} Seat(s)", key="seats_filter"
    )

# Geography & Cosmetics
with st.sidebar.expander("📍 Geography & Cosmetics", expanded=False):
    selected_regions = st.multiselect(
        "Region", options=regions_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_regions else f"⚪ {x}", key="regions_filter"
    )
    selected_colors = st.multiselect(
        "Vehicle Color", options=colors_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_colors else f"⚪ {x}", key="colors_filter"
    )
    selected_categories = st.multiselect(
        "Homologation Category", options=categories_avail, default=[], 
        format_func=lambda x: f"🟢 {x}" if x in green_categories else f"⚪ {x}", key="categories_filter"
    )
    selected_vins = st.sidebar.multiselect("VIN Prefix (8 chars)", options=vins_avail, default=[], key="vins_filter")

# 5. FINAL DATAFRAME EVALUATION
m_time_f = (df_raw['Registration Date'] >= pd.to_datetime(start_date)) & (df_raw['Registration Date'] <= pd.to_datetime(end_date))
if st.session_state["years_filter"]: m_time_f &= df_raw['Registration Year'].isin(st.session_state["years_filter"])
if st.session_state["months_filter"]: m_time_f &= df_raw['Registration Month'].isin(st.session_state["months_filter"])

m_status_f = df_raw['New/Used'].isin(selected_new_used) if selected_new_used else True
m_region_f = df_raw['Region'].isin(selected_regions) if selected_regions else True
m_color_f = df_raw['Color'].isin(selected_colors) if selected_colors else True
m_fuel_f = df_raw['Fuel'].isin(selected_fuel) if selected_fuel else True
m_segment_f = df_raw['Segment'].isin(selected_segments) if selected_segments else True
m_category_f = df_raw['Category'].isin(selected_categories) if selected_categories else True
m_disp_f = df_raw['Displacement Group'].isin(selected_disp) if selected_disp else True
m_seats_f = df_raw['Total seats'].isin(selected_seats) if selected_seats else True
m_brand_f = df_raw['Brand'].isin(selected_brands) if selected_brands else True
m_model_f = df_raw['Model'].isin(selected_models) if selected_models else True
m_vin_f = df_raw['VIN Prefix'].isin(selected_vins) if selected_vins else True

df_time_status = df_raw[m_time_f & m_status_f & m_region_f]
df_context_final = df_raw[m_time_f & m_status_f & m_region_f & m_color_f & m_fuel_f & m_segment_f & m_category_f & m_disp_f & m_seats_f]
df_filt = df_raw[m_time_f & m_status_f & m_region_f & m_color_f & m_fuel_f & m_segment_f & m_category_f & m_disp_f & m_seats_f & m_brand_f & m_model_f & m_vin_f]
df_non_time = df_raw[m_status_f & m_region_f & m_color_f & m_fuel_f & m_segment_f & m_category_f & m_disp_f & m_seats_f & m_brand_f & m_model_f & m_vin_f]

# 6. Main Dashboard Area Layout
st.markdown(f"**User Role:** `{st.session_state['role'].upper()}` | **Active Filter Count:** `{len(df_filt):,}` out of `{len(df_raw):,}`")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1: st.markdown(f'<div class="metric-card"><div class="metric-card-title">Total Registrations</div><div class="metric-card-value">{len(df_filt):,}</div><div class="metric-card-subtitle">For selected filters</div></div>', unsafe_allow_html=True)

if not df_filt.empty:
    brand_counts = df_filt['Brand'].value_counts()
    top_brand, top_brand_units = brand_counts.index[0], brand_counts.iloc[0]
    top_brand_share = (top_brand_units / len(df_filt)) * 100
else: top_brand, top_brand_units, top_brand_share = "N/A", 0, 0.0

with kpi2: st.markdown(f'<div class="metric-card"><div class="metric-card-title">Market Leader</div><div class="metric-card-value">{top_brand}</div><div class="metric-card-subtitle">{top_brand_units:,} units ({top_brand_share:.1f}% share)</div></div>', unsafe_allow_html=True)

if not df_filt.empty:
    seg_counts = df_filt['Segment'].value_counts()
    top_seg, top_seg_share = seg_counts.index[0], (seg_counts.iloc[0] / len(df_filt)) * 100
else: top_seg, top_seg_share = "N/A", 0.0

with kpi3: st.markdown(f'<div class="metric-card"><div class="metric-card-title">Top Segment</div><div class="metric-card-value">{top_seg}</div><div class="metric-card-subtitle">Market share: {top_seg_share:.1f}%</div></div>', unsafe_allow_html=True)

new_ratio = ((df_filt['New/Used'] == 'N').sum() / len(df_filt)) * 100 if not df_filt.empty else 0.0
with kpi4: st.markdown(f'<div class="metric-card"><div class="metric-card-title">New Vehicles Ratio</div><div class="metric-card-value">{new_ratio:.1f}%</div><div class="metric-card-subtitle">Used imports represent {100 - new_ratio:.1f}%</div></div>', unsafe_allow_html=True)

# Shared Brand Color Palette for all visualizations
brand_color_map = {
    'HONDA': '#ea580c', 'YAMAHA': '#2563eb', 'BMW': '#38bdf8', 'KTM': '#f97316',
    'KAWASAKI': '#22c55e', 'JAWA': '#dc2626', 'HARLEY-DAVIDSON': '#ea580c', 'SUZUKI': '#3b82f6',
    'TRIUMPH': '#64748b', 'DUCATI': '#ef4444', 'CFMOTO': '#06b6d4', 'VESPA': '#10b981',
    'PIAGGIO': '#0d9488', 'KEEWAY': '#a855f7', 'BETA': '#f43f5e'
}

# Tabs
tab_overview, tab_yoy, tab_pivot, tab_grey = st.tabs(["📊 Market Overview", "📈 Period Comparison", "🧮 Pivot Matrix", "🚨 Vehicles Pool & Grey Market"])

# --- TAB 1: MARKET OVERVIEW ---
with tab_overview:
    st.header("Motorcycle Registration Analytics")
    if df_filt.empty: st.warning("No registrations found for the selected filters.")
    else:
        brand_color_map_extended = brand_color_map.copy()
        brand_color_map_extended['Other Brands'] = '#475569'

        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)
        row3_col1, row3_col2 = st.columns(2)
        
        with row1_col1:
            sel_brands = st.session_state.get("brands_filter", [])
            num_sel = len(sel_brands)
            
            if market_base_mode == "TTL Market":
                df_chart_base = df_time_status.copy()
                if 1 <= num_sel <= 5:
                    df_chart_base['Chart_Brand'] = df_chart_base['Brand'].apply(lambda b: b if b in sel_brands else 'Other Brands')
                    df_chart_vol = df_chart_base.groupby(['Month_Col', 'Chart_Brand']).size().reset_index(name='Units')
                    df_chart_vol['sort_key'] = df_chart_vol['Chart_Brand'].apply(lambda x: len(sel_brands) if x == 'Other Brands' else sel_brands.index(x))
                    df_chart_vol = df_chart_vol.sort_values(by=['Month_Col', 'sort_key'])
                    
                    fig_vol = px.bar(
                        df_chart_vol, x='Month_Col', y='Units', color='Chart_Brand', barmode='stack',
                        title='Monthly Registration Volume of Motorcycles (units)',
                        labels={'Month_Col': 'Month', 'Units': 'Registrations', 'Chart_Brand': 'Brand'},
                        color_discrete_map=brand_color_map_extended,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                else:
                    df_chart_base['Year_Str'] = df_chart_base['Registration Year'].apply(lambda y: str(int(float(y))) if pd.notna(y) else 'Unknown')
                    df_chart_vol = df_chart_base.groupby(['Month_Col', 'Year_Str']).size().reset_index(name='Units')
                    fig_vol = px.bar(
                        df_chart_vol, x='Month_Col', y='Units', color='Year_Str', barmode='group',
                        title='Monthly Registration Volume of Motorcycles (units)',
                        labels={'Month_Col': 'Month', 'Units': 'Registrations', 'Year_Str': 'Year'},
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
            else:
                df_chart_base = df_filt.copy()
                if 1 <= num_sel <= 5:
                    df_chart_vol = df_chart_base.groupby(['Month_Col', 'Brand']).size().reset_index(name='Units')
                    df_chart_vol['sort_key'] = df_chart_vol['Brand'].apply(lambda x: sel_brands.index(x) if x in sel_brands else 99)
                    df_chart_vol = df_chart_vol.sort_values(by=['Month_Col', 'sort_key'])
                    
                    fig_vol = px.bar(
                        df_chart_vol, x='Month_Col', y='Units', color='Brand', barmode='stack',
                        title='Monthly Registration Volume of Motorcycles (units)',
                        labels={'Month_Col': 'Month', 'Units': 'Registrations', 'Brand': 'Brand'},
                        color_discrete_map=brand_color_map_extended,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                else:
                    df_chart_base['Year_Str'] = df_chart_base['Registration Year'].apply(lambda y: str(int(float(y))) if pd.notna(y) else 'Unknown')
                    df_chart_vol = df_chart_base.groupby(['Month_Col', 'Year_Str']).size().reset_index(name='Units')
                    fig_vol = px.bar(
                        df_chart_vol, x='Month_Col', y='Units', color='Year_Str', barmode='group',
                        title='Monthly Registration Volume of Motorcycles (units)',
                        labels={'Month_Col': 'Month', 'Units': 'Registrations', 'Year_Str': 'Year'},
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
            
            fig_vol.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis=dict(tickformat="d"))
            st.plotly_chart(fig_vol, use_container_width=True)
            
        with row1_col2:
            top_brands = df_filt['Brand'].value_counts().head(10).index.tolist()
            if top_brands:
                if "trend_chart_key" not in st.session_state: st.session_state["trend_chart_key"] = 0
                if st.button("Reset Legend", key="reset_trend_legend_btn", use_container_width=True): st.session_state["trend_chart_key"] += 1; st.rerun()
                
                df_top = df_filt[df_filt['Brand'].isin(top_brands)].copy()
                df_top_monthly = df_top.groupby(['Registration Year', 'Month_Col', 'Brand']).size().reset_index(name='Units')
                
                if market_base_mode == "TTL Market": df_monthly_total = df_time_status.groupby(['Registration Year', 'Month_Col']).size().reset_index(name='Total')
                else: df_monthly_total = df_filt.groupby(['Registration Year', 'Month_Col']).size().reset_index(name='Total')
                
                df_share = pd.merge(df_top_monthly, df_monthly_total, on=['Registration Year', 'Month_Col'])
                df_share['Share %'] = (df_share['Units'] / df_share['Total']) * 100
                df_share['Date_Axis'] = pd.to_datetime(df_share['Registration Year'].astype(int).astype(str) + '-' + df_share['Month_Col'] + '-01')
                df_share = df_share.sort_values(by=['Brand', 'Date_Axis']).reset_index(drop=True)
                
                fig_share = px.line(
                    df_share, x='Date_Axis', y='Share %', color='Brand', 
                    custom_data=['Brand'],
                    title=f'Market Share Trend of Top 10 Brands (% - Base: {market_base_mode})', 
                    color_discrete_map=brand_color_map, 
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_share.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20))
                fig_share.update_xaxes(type='date', tickformat="%b %Y")
                fig_share.update_traces(hovertemplate="<b>Brand: %{customdata[0]}</b><br>Period: %{x|%b %Y}<br>Share: %{y:.2f}%<extra></extra>")
                st.plotly_chart(fig_share, use_container_width=True, key=f"trend_chart_plotly_{st.session_state['trend_chart_key']}")
            
        with row2_col1:
            df_seg = df_filt.groupby(['Segment', 'Category']).size().reset_index(name='Count')
            fig_seg = px.sunburst(df_seg, path=['Segment', 'Category'], values='Count', title='Market Segment & Category Distribution', color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_seg.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig_seg, use_container_width=True)
            
        with row2_col2:
            df_region = df_filt['Region'].value_counts().reset_index(); df_region.columns = ['Region', 'Units']
            fig_region = px.bar(df_region, x='Units', y='Region', orientation='h', title='Registrations by Region', labels={'Units': 'Registrations'}, color='Units', color_continuous_scale='Viridis')
            fig_region.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis={'categoryorder': 'total ascending'}, xaxis=dict(tickformat="d"))
            st.plotly_chart(fig_region, use_container_width=True)

        with row3_col1:
            df_color = df_filt['Color'].value_counts().reset_index(); df_color.columns = ['Color', 'Units']
            color_hex_map = {'Black': '#1e293b', 'Grey': '#64748b', 'Orange': '#f97316', 'Green': '#16a34a', 'Brown': '#78350f', 'Red': '#dc2626', 'Yellow': '#eab308', 'White': '#f8fafc', 'Blue': '#2563eb', 'Other / Multicolor': '#475569', 'Violet': '#a855f7'}
            fig_color = px.bar(df_color, x='Color', y='Units', title='Popularity of Vehicle Colors', color='Color', color_discrete_map=color_hex_map)
            fig_color.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), showlegend=False, xaxis={'categoryorder': 'total descending'}, yaxis=dict(tickformat="d"))
            fig_color.update_traces(hovertemplate="<b>Color: %{x}</b><br>Units: %{y:d}<extra></extra>")
            st.plotly_chart(fig_color, use_container_width=True)
            
        with row3_col2:
            df_disp_group = df_filt['Displacement Group'].value_counts().reset_index()
            df_disp_group.columns = ['Class', 'Units']
            class_colors = {
                '> 800 ccm': '#dc2626', 
                '≤ 800 ccm': '#f43f5e', 
                '≤ 500 ccm': '#a855f7', 
                '≤ 350 ccm': '#f59e0b', 
                '≤ 125 ccm': '#10b981', 
                '≤ 50 ccm': '#2563eb', 
                'Electric': '#06b6d4', 
                'Unknown': '#475569'
            }
            fig_disp = px.pie(df_disp_group, names='Class', values='Units', hole=0.4, title='Displacement Class Distribution', color='Class', color_discrete_map=class_colors, category_orders={'Class': disp_order})
            fig_disp.update_layout(
                template='plotly_dark', 
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(
                    categoryorder="array",
                    categoryarray=disp_order
                )
            )
            st.plotly_chart(fig_disp, use_container_width=True)

# --- TAB 2: PERIOD COMPARISON ---
with tab_yoy:
    st.header("Period Comparison Analysis")
    filter_left_col, filter_right_col = st.columns([3, 2])
    col_y1, col_y2 = filter_left_col.columns(2)
    with col_y1: base_year = st.selectbox("Base Year (Period A)", options=years_avail, index=0)
    with col_y2:
        default_comp_idx = 1 if len(years_avail) > 1 else 0
        if base_year in years_avail:
            base_idx = years_avail.index(base_year)
            if base_idx + 1 < len(years_avail): default_comp_idx = base_idx + 1
        comp_year = st.selectbox("Comparison Year (Period B)", options=years_avail, index=default_comp_idx)
    with filter_right_col:
        if st.session_state["months_filter"]:
            months_to_use = sorted(list(st.session_state["months_filter"]))
            st.info(f"ℹ️ Months from sidebar filter: {', '.join(map(str, months_to_use))}")
            month_range = (min(months_to_use), max(months_to_use))
            _ = st.slider("Month Range (Overridden by sidebar)", min_value=1, max_value=12, value=month_range, disabled=True)
        else:
            max_month_in_base = int(df_raw[df_raw['Registration Year'] == base_year]['Registration Month'].max()) if not df_raw[df_raw['Registration Year'] == base_year].empty else 12
            month_range = st.slider("Month Range (e.g., Jan-May)", min_value=1, max_value=12, value=(1, max_month_in_base))
            months_to_use = list(range(month_range[0], month_range[1] + 1))
        
    if base_year == comp_year: st.warning("Please select two different years to perform a comparison.")
    else:
        df_base = df_non_time[(df_non_time['Registration Year'] == base_year) & (df_non_time['Registration Month'].isin(months_to_use))]
        df_comp = df_non_time[(df_non_time['Registration Year'] == comp_year) & (df_non_time['Registration Month'].isin(months_to_use))]
        
        df_context_non_time = df_raw[m_status_f & m_region_f & m_color_f & m_fuel_f & m_segment_f & m_category_f & m_disp_f & m_seats_f]
        df_base_market = df_context_non_time[(df_context_non_time['Registration Year'] == base_year) & (df_context_non_time['Registration Month'].isin(months_to_use))]
        df_comp_market = df_context_non_time[(df_context_non_time['Registration Year'] == comp_year) & (df_context_non_time['Registration Month'].isin(months_to_use))]
        
        total_base, total_comp = len(df_base), len(df_comp)
        total_base_market, total_comp_market = len(df_base_market), len(df_comp_market)
        
        if market_base_mode == "TTL Market":
            disp_base_vol = total_base_market
            disp_comp_vol = total_comp_market
            denom_base = total_base_market
            denom_comp = total_comp_market
            label_suffix = " (TTL Market)"
        else:
            disp_base_vol = total_base
            disp_comp_vol = total_comp
            denom_base = total_base
            denom_comp = total_comp
            label_suffix = " (Selected Brands)"
            
        kpi_left_col, kpi_right_col = st.columns([3, 2])
        kpi_col1, kpi_col2 = kpi_left_col.columns(2)
        kpi_col3 = kpi_right_col
        kpi_col1.metric(label=f"Volume in {base_year}{label_suffix}", value=f"{disp_base_vol:,} units")
        kpi_col2.metric(label=f"Volume in {comp_year}{label_suffix}", value=f"{disp_comp_vol:,} units")
        vol_diff = disp_base_vol - disp_comp_vol
        vol_pct = (vol_diff / disp_comp_vol * 100) if disp_comp_vol > 0 else 0.0
        kpi_col3.metric(label=f"Absolute & Relative Change{label_suffix}", value=f"{vol_diff:+,} units", delta=f"{vol_pct:+.2f}%")
            
        if total_base == 0 and total_comp == 0: st.info("No data found for the selected periods.")
        else:
            brand_base = df_base['Brand'].value_counts().reset_index(); brand_base.columns = ['Brand', 'Base_Units']
            brand_comp = df_comp['Brand'].value_counts().reset_index(); brand_comp.columns = ['Brand', 'Comp_Units']
            df_yoy = pd.merge(brand_base, brand_comp, on='Brand', how='outer').fillna(0)
            df_yoy['Abs_Change'] = df_yoy['Base_Units'] - df_yoy['Comp_Units']
            df_yoy['Pct_Change'] = df_yoy.apply(lambda r: (r['Abs_Change'] / r['Comp_Units'] * 100) if r['Comp_Units'] > 0 else (100.0 if r['Base_Units'] > 0 else 0.0), axis=1)
            df_yoy['Base_Share'] = (df_yoy['Base_Units'] / denom_base * 100) if denom_base > 0 else 0.0
            df_yoy['Comp_Share'] = (df_yoy['Comp_Units'] / denom_comp * 100) if denom_comp > 0 else 0.0
            df_yoy['Share_Change'] = df_yoy['Base_Share'] - df_yoy['Comp_Share']
            
            df_yoy_sorted = df_yoy.sort_values(by='Base_Units', ascending=False).reset_index(drop=True)
            top_yoy_brands = df_yoy_sorted['Brand'].head(20).tolist()
            df_yoy_main = df_yoy_sorted[df_yoy_sorted['Brand'].isin(top_yoy_brands)].copy()
            df_yoy_other = df_yoy_sorted[~df_yoy_sorted['Brand'].isin(top_yoy_brands)].copy()
            
            df_yoy_total = pd.DataFrame([{
                'Brand': '— TOTAL —', 
                'Base_Units': total_base, 
                'Comp_Units': total_comp, 
                'Abs_Change': total_base - total_comp,
                'Pct_Change': ((total_base - total_comp) / total_comp * 100) if total_comp > 0 else 0.0,
                'Base_Share': (total_base / denom_base * 100) if denom_base > 0 else 0.0, 
                'Comp_Share': (total_comp / denom_comp * 100) if denom_comp > 0 else 0.0, 
                'Share_Change': ((total_base / denom_base * 100) - (total_comp / denom_comp * 100)) if (denom_base > 0 and denom_comp > 0) else 0.0
            }])
            
            yoy_col_config = {
                'Brand': st.column_config.TextColumn("Brand", width=200),
                'Base_Units': st.column_config.NumberColumn(f"{base_year} (Units)", format="%d", width=100),
                'Comp_Units': st.column_config.NumberColumn(f"{comp_year} (Units)", format="%d", width=100),
                'Abs_Change': st.column_config.NumberColumn("Abs Change", format="%+d", width=95),
                'Pct_Change': st.column_config.NumberColumn("Pct Change", format="%+.2f %%", width=95),
                'Base_Share': st.column_config.NumberColumn(f"{base_year} Share", format="%.2f %%", width=95),
                'Comp_Share': st.column_config.NumberColumn(f"{comp_year} Share", format="%.2f %%", width=95),
                'Share_Change': st.column_config.NumberColumn("Share Change (pp)", format="%+.2f pp", width=115)
            }
            
            yoy_left, yoy_right = st.columns([3, 2])
            with yoy_left:
                st.markdown(f"**YoY Registration Details by Brand ({'TTL Market' if market_base_mode == 'TTL Market' else 'Filters based'}):**")
                st.dataframe(df_yoy_main, column_config=yoy_col_config, use_container_width=True, height=400, hide_index=True)
                if not df_yoy_other.empty:
                    ob, oc = df_yoy_other['Base_Units'].sum(), df_yoy_other['Comp_Units'].sum()
                    df_yoy_other_row = pd.DataFrame([{
                        'Brand': 'Other Brands Subtotal', 
                        'Base_Units': ob, 
                        'Comp_Units': oc, 
                        'Abs_Change': ob - oc, 
                        'Pct_Change': ((ob - oc) / oc * 100) if oc > 0 else 0.0, 
                        'Base_Share': (ob / denom_base * 100) if denom_base > 0 else 0.0, 
                        'Comp_Share': (oc / denom_comp * 100) if denom_comp > 0 else 0.0, 
                        'Share_Change': ((ob / denom_base * 100) - (oc / denom_comp * 100)) if (denom_base > 0 and denom_comp > 0) else 0.0
                    }])
                    st.dataframe(df_yoy_other_row, column_config=yoy_col_config, use_container_width=True, hide_index=True)
                st.dataframe(df_yoy_total, column_config=yoy_col_config, use_container_width=True, hide_index=True)
                
            with yoy_right:
                df_plot_yoy = df_yoy_sorted.head(10).copy()
                if not df_plot_yoy.empty:
                    df_plot_melt = df_plot_yoy.melt(id_vars=['Brand'], value_vars=['Base_Units', 'Comp_Units'], var_name='Period', value_name='Registrations')
                    df_plot_melt['Period'] = df_plot_melt['Period'].apply(lambda x: f"Base ({base_year})" if x == 'Base_Units' else f"Comp ({comp_year})")
                    fig_yoy = px.bar(df_plot_melt, x='Brand', y='Registrations', color='Period', barmode='group', title=f"Brand Volume Comparison: {base_year} vs {comp_year}",
                                     labels={'Brand': 'Brand', 'Registrations': 'Registrations (units)', 'Period': 'Period'}, color_discrete_sequence=['#3b82f6', '#ef4444'])
                    fig_yoy.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis=dict(tickformat="d"))
                    st.plotly_chart(fig_yoy, use_container_width=True)

            # Historical performance trendline
            st.markdown("---")
            if market_base_mode == "TTL Market":
                df_source = df_context_non_time.copy()
            else:
                df_source = df_non_time.copy()
                
            years_to_use = st.session_state["years_filter"] if st.session_state["years_filter"] else list(range(2018, int(df_raw['Registration Year'].max()) + 1))
            df_source_filtered = df_source[
                (df_source['Registration Month'].isin(months_to_use)) & 
                (df_source['Registration Year'].isin(years_to_use))
            ]
            
            if market_base_mode == "Filters based" and selected_brands:
                target_brands = selected_brands
            else:
                if not df_source_filtered.empty:
                    target_brands = df_source_filtered['Brand'].value_counts().head(10).index.tolist()
                else:
                    target_brands = []
            
            if target_brands:
                all_years_range = sorted(list(years_to_use))
                mux = pd.MultiIndex.from_product([target_brands, all_years_range], names=['Brand', 'Registration Year'])
                df_line_data = df_source_filtered[df_source_filtered['Brand'].isin(target_brands)].groupby(['Brand', 'Registration Year']).size().reindex(mux, fill_value=0).reset_index(name='Units')
                df_line_data = df_line_data.sort_values(by=['Brand', 'Registration Year'])
                
                months_label = f"{month_range[0]}-{month_range[1]}" if not st.session_state["months_filter"] else ", ".join(map(str, sorted(months_to_use)))
                years_label = "2018-present" if not st.session_state["years_filter"] else ", ".join(map(str, sorted(years_to_use)))
                
                fig_line = px.line(
                    df_line_data, x='Registration Year', y='Units', color='Brand',
                    title=f"Historical Brand Performance (Months: {months_label}, Years: {years_label})",
                    labels={'Registration Year': 'Year', 'Units': 'Registrations (units)', 'Brand': 'Brand'},
                    color_discrete_map=brand_color_map,
                    category_orders={'Registration Year': all_years_range}
                )
                fig_line.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), xaxis=dict(type='category'), yaxis=dict(tickformat="d"))
                fig_line.update_traces(mode='lines+markers')
                
                if "hist_chart_key" not in st.session_state: st.session_state["hist_chart_key"] = 0
                if st.button("Reset Legend", key="reset_hist_legend_btn", use_container_width=True): st.session_state["hist_chart_key"] += 1; st.rerun()
                st.plotly_chart(fig_line, use_container_width=True, key=f"hist_chart_plotly_{st.session_state['hist_chart_key']}")

# --- TAB 3: PIVOT MATRIX ---
if st.session_state.get("authenticated"):
    with tab_pivot:
        st.header("Interactive Pivot Table")
        if df_filt.empty: st.warning("No data found matching the selected filters.")
        else:
            all_months = [f"{m:02d}" for m in range(1, 13)]
            
            if market_base_mode == "TTL Market":
                df_market_base = df_time_status
            else:
                df_market_base = df_filt
                
            df_market_gp = df_market_base.groupby(['Month_Col']).size().reset_index(name='Count')
            col_totals_market = df_market_gp.set_index('Month_Col')['Count']
            for m in all_months:
                if m not in col_totals_market.index: col_totals_market[m] = 0.0
            col_totals_market = col_totals_market[all_months].astype(float)
            col_totals_market['YTD'] = float(len(df_market_base))
            
            ctrl_col1, ctrl_col2 = st.columns([1, 2])
            metric_type = ctrl_col1.radio("Select metric:", options=["Absolute Units (Count)", f"Market Share % ({market_base_mode})"], horizontal=True)
            
            with ctrl_col2:
                top_brands = list(set(df_context_final['Brand'].value_counts().head(20).index.tolist()) | set(selected_brands))
                all_brands_in_filt = sorted(df_filt['Brand'].dropna().unique())
                if not df_filt[~df_filt['Brand'].isin(top_brands)].empty: all_brands_in_filt.append('Other Brands')
                all_brands_in_filt = sorted(list(set(all_brands_in_filt)))
                
                if "expanded_brands" not in st.session_state: st.session_state["expanded_brands"] = []
                b_c1, b_c2, _ = st.columns([1, 1, 3])
                if b_c1.button("Expand All"): st.session_state["expanded_brands"] = all_brands_in_filt; st.rerun()
                if b_c2.button("Collapse All"): st.session_state["expanded_brands"] = []; st.rerun()
                expanded_brands = st.multiselect("Expand brands to models:", options=all_brands_in_filt, key="expanded_brands_selector", default=st.session_state["expanded_brands"])
                st.session_state["expanded_brands"] = expanded_brands

            df_matrix = df_filt.copy()
            df_matrix['Disp_Brand'] = df_matrix['Brand']
            df_matrix['Disp_Model'] = '— Total —'
            is_exp_top = df_matrix['Brand'].isin(top_brands) & df_matrix['Brand'].isin(expanded_brands)
            df_matrix.loc[is_exp_top, 'Disp_Model'] = df_matrix.loc[is_exp_top, 'Model']
            df_matrix.loc[~df_matrix['Brand'].isin(top_brands), 'Disp_Brand'] = 'Other Brands'
            if 'Other Brands' in expanded_brands: df_matrix.loc[~df_matrix['Brand'].isin(top_brands), 'Disp_Model'] = df_matrix.loc[~df_matrix['Brand'].isin(top_brands), 'Brand']
                
            df_gp = df_matrix.groupby(['Disp_Brand', 'Disp_Model', 'Month_Col']).size().reset_index(name='Count')
            if df_gp.empty: st.warning("No rows after grouping.")
            else:
                df_pivot = df_gp.pivot(index=['Disp_Brand', 'Disp_Model'], columns='Month_Col', values='Count').fillna(0)
                for m in all_months:
                    if m not in df_pivot.columns: df_pivot[m] = 0.0
                df_pivot = df_pivot[all_months]
                df_pivot['YTD'] = df_pivot.sum(axis=1)
                
                col_totals_filt = df_pivot.sum(axis=0)
                
                def format_cz_int(val):
                    try: return f"{int(val):,}".replace(",", ".")
                    except: return str(val)

                col_config = {
                    'Brand': st.column_config.TextColumn("Brand", width=200),
                    'Model': st.column_config.TextColumn("Model", width=130)
                }
                for col in all_months + ['YTD']:
                    col_width = 85 if col == 'YTD' else 75
                    if "Market Share" in metric_type:
                        col_config[col] = st.column_config.NumberColumn(col, format="%.2f %%", width=col_width)
                    else:
                        col_config[col] = st.column_config.Column(col, width=col_width)
                
                is_brand_filtered = len(selected_brands) > 0 or len(selected_models) > 0
                
                if is_brand_filtered:
                    # CASE A: Brand/Model filter IS active
                    brand_totals = {}
                    for idx in df_pivot.index:
                        brand, model = idx
                        if model == '— Total —':
                            brand_totals[brand] = df_pivot.loc[idx, 'YTD']
                    for idx in df_pivot.index:
                        brand, model = idx
                        if brand not in brand_totals:
                            brand_totals[brand] = 0.0

                    rows_to_sort = []
                    for idx in df_pivot.index:
                        brand, model = idx
                        is_total = 0 if model == '— Total —' else 1
                        ytd_val = df_pivot.loc[idx, 'YTD']
                        key = (-brand_totals[brand], brand, is_total, -ytd_val)
                        rows_to_sort.append((key, idx))
                    rows_to_sort.sort(key=lambda x: x[0])
                    df_main_abs = df_pivot.loc[[idx for _, idx in rows_to_sort]]
                    df_main_abs.index.names = ['Brand', 'Model']
                    
                    df_sel_total_abs = pd.DataFrame([col_totals_filt])
                    df_sel_total_abs.index = pd.MultiIndex.from_tuples([('Selected Brands Total', '— Total —')], names=['Brand', 'Model'])
                    
                    other_diff = col_totals_market - col_totals_filt
                    other_diff = other_diff.clip(lower=0)
                    df_other_abs = pd.DataFrame([other_diff])
                    df_other_abs.index = pd.MultiIndex.from_tuples([('Other Brands', '— Total —')], names=['Brand', 'Model'])
                    
                    df_total_abs = pd.DataFrame([col_totals_market])
                    df_total_abs.index = pd.MultiIndex.from_tuples([('— TOTAL MARKET —', '— TOTAL MARKET —')], names=['Brand', 'Model'])
                    
                    df_download = pd.concat([df_main_abs, df_sel_total_abs, df_other_abs, df_total_abs])
                    if "Market Share" in metric_type:
                        df_download = (df_download.div(col_totals_market, axis=1) * 100).fillna(0)
                    
                    if "Market Share" in metric_type:
                        df_main_display = (df_main_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                        df_sel_total_display = (df_sel_total_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                        df_other_display = (df_other_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                        df_total_display = (df_total_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                    else:
                        df_main_display = df_main_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        df_sel_total_display = df_sel_total_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        df_other_display = df_other_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        df_total_display = df_total_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                    
                    st.dataframe(df_main_display, column_config=col_config, use_container_width=True, height=350, hide_index=True)
                    st.markdown("**Selected Brands Summary:**")
                    st.dataframe(df_sel_total_display, column_config=col_config, use_container_width=True, hide_index=True)
                    st.markdown("**Other Brands (Rest of Market):**")
                    st.dataframe(df_other_display, column_config=col_config, use_container_width=True, hide_index=True)
                    st.markdown("**Total Market Volume:**")
                    st.dataframe(df_total_display, column_config=col_config, use_container_width=True, hide_index=True)
                    
                else:
                    # CASE B: NO Brand filter is active
                    brand_totals = {}
                    for idx in df_pivot.index:
                        brand, model = idx
                        if model == '— Total —':
                            brand_totals[brand] = df_pivot.loc[idx, 'YTD']
                    for idx in df_pivot.index:
                        brand, model = idx
                        if brand not in brand_totals:
                            brand_totals[brand] = 0.0

                    rows_to_sort = []
                    for idx in df_pivot.index:
                        brand, model = idx
                        is_total = 0 if model == '— Total —' else 1
                        ytd_val = df_pivot.loc[idx, 'YTD']
                        key = (-brand_totals[brand], brand, is_total, -ytd_val)
                        rows_to_sort.append((key, idx))
                    rows_to_sort.sort(key=lambda x: x[0])
                    df_pivot_sorted = df_pivot.loc[[idx for _, idx in rows_to_sort]]
                    
                    has_other = 'Other Brands' in df_pivot_sorted.index.get_level_values(0)
                    if has_other:
                        df_main_abs = df_pivot_sorted.drop(index='Other Brands', level=0)
                        df_other_abs = df_pivot_sorted.loc[['Other Brands']]
                    else:
                        df_main_abs = df_pivot_sorted
                        df_other_abs = pd.DataFrame()
                        
                    df_main_sum_abs = pd.DataFrame([df_main_abs.sum(axis=0)])
                    df_main_sum_abs.index = pd.MultiIndex.from_tuples([('Top 20 Brands Total', '— Total —')], names=['Brand', 'Model'])
                    
                    df_total_abs = pd.DataFrame([col_totals_market])
                    df_total_abs.index = pd.MultiIndex.from_tuples([('— TOTAL MARKET —', '— TOTAL MARKET —')], names=['Brand', 'Model'])
                    
                    df_main_abs.index.names = ['Brand', 'Model']
                    df_main_sum_abs.index.names = ['Brand', 'Model']
                    if not df_other_abs.empty: df_other_abs.index.names = ['Brand', 'Model']
                    df_total_abs.index.names = ['Brand', 'Model']
                    
                    if not df_other_abs.empty: df_download = pd.concat([df_main_abs, df_main_sum_abs, df_other_abs, df_total_abs])
                    else: df_download = pd.concat([df_main_abs, df_main_sum_abs, df_total_abs])
                    
                    if "Market Share" in metric_type: df_download = (df_download.div(col_totals_market, axis=1) * 100).fillna(0)

                    if "Market Share" in metric_type:
                        df_main_display = (df_main_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                        df_main_sum_display = (df_main_sum_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                        df_other_display = (df_other_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index() if not df_other_abs.empty else pd.DataFrame()
                        df_total_display = (df_total_abs.div(col_totals_market, axis=1) * 100).fillna(0).reset_index()
                    else:
                        df_main_display = df_main_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        df_main_sum_display = df_main_sum_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        df_other_display = df_other_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD']) if not df_other_abs.empty else pd.DataFrame()
                        df_total_display = df_total_abs.reset_index().style.format(format_cz_int, subset=all_months + ['YTD'])
                        
                    st.dataframe(df_main_display, column_config=col_config, use_container_width=True, height=450, hide_index=True)
                    st.markdown("**Top 20 Brands Summary:**")
                    st.dataframe(df_main_sum_display, column_config=col_config, use_container_width=True, hide_index=True)
                    if not df_other_abs.empty:
                        st.markdown("**Other Brands (Low Volume Rollup):**")
                        st.dataframe(df_other_display, column_config=col_config, use_container_width=True, hide_index=True)
                    st.markdown("**Total Market Volume:**")
                    st.dataframe(df_total_display, column_config=col_config, use_container_width=True, hide_index=True)

                st.markdown("---")
                df_download_res = df_download.reset_index()
                is_market_share = "Market Share" in metric_type
                
                for col in df_download_res.columns:
                    if col not in ['Brand', 'Model']:
                        if is_market_share:
                            df_download_res[col] = df_download_res[col].apply(lambda x: f"{float(x):.2f}".replace('.', ',') if pd.notna(x) else "")
                        else:
                            df_download_res[col] = df_download_res[col].apply(lambda x: f"{int(round(float(x)))}" if pd.notna(x) else "")
                
                rename_dict = {}
                for col in df_download_res.columns:
                    if col not in ['Brand', 'Model']:
                        rename_dict[col] = f"{col} (%)" if is_market_share else f"{col} (pcs)"
                df_download_res = df_download_res.rename(columns=rename_dict)
                
                csv_data = df_download_res.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button(
                    label="📥 Download Pivot Matrix (CSV)",
                    data=csv_data,
                    file_name=f"MOTO_Market_CZ_Pivot_{metric_type.replace(' ', '_').replace('%', 'pct')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.info("💡 **Chart download tip:** You can download any chart in the **Market Overview** and **YoY** tabs as a PNG image by clicking the camera icon in the top-right corner of the chart (visible when hovering).")

# --- TAB 4: VEHICLES POOL & GREY MARKET ---
@st.cache_data(show_spinner="Parsing vehicles pool PDF reports...")
def load_fleet_data():
    pdf_path = os.path.join(script_dir, "SDA_Fleet", "2025-12.CFC-Fleet.EN.pdf")
    
    # Secure fallback static values
    fallback = {
        2018: (1147971, 32.20),
        2019: (1180321, 32.40),
        2020: (1214586, 32.72),
        2021: (1249255, 32.68),
        2022: (1287748, 32.58),
        2023: (1326116, 32.65),
        2024: (1362321, 32.75),
        2025: (1392963, 32.63)
    }
    
    if not os.path.exists(pdf_path):
        return fallback
        
    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
        data = {}
        for year in range(2018, 2026):
            pos = text.find(str(year))
            if pos != -1:
                sub = text[pos:pos+400]
                # Look for fleet units (number starting with 1,xxx,xxx)
                units_m = re.findall(r'\b(1,\d{3},\d{3})\b', sub)
                # Look for average age (e.g. 32.63 or 32.2)
                age_m = re.findall(r'\b(32\.\d{2}|32\.\d{1})\b', sub)
                
                if units_m and age_m:
                    units_val = int(units_m[0].replace(',', ''))
                    age_val = float(age_m[0])
                    data[year] = (units_val, age_val)
                    
        # Check if we parsed all years, otherwise combine with fallback
        for y in fallback:
            if y not in data:
                data[y] = fallback[y]
        return data
    except Exception:
        return fallback

with tab_grey:
    st.header("Vehicles Pool & Grey Market Analysis")
    
    # 1. Vehicles Pool Overview
    pool_data = load_fleet_data()
    years = sorted(list(pool_data.keys()))
    units = [pool_data[y][0] for y in years]
    ages = [pool_data[y][1] for y in years]
    
    st.subheader("Official Czech Motorcycle Fleet (Category L)")
    
    kpi_p1, kpi_p2, kpi_p3 = st.columns(3)
    latest_year = years[-1]
    latest_units = pool_data[latest_year][0]
    latest_age = pool_data[latest_year][1]
    
    kpi_p1.markdown(f'<div class="metric-card"><div class="metric-card-title">Total Registered Fleet ({latest_year})</div><div class="metric-card-value">{latest_units:,} pcs</div><div class="metric-card-subtitle">Official category L fleet size</div></div>', unsafe_allow_html=True)
    kpi_p2.markdown(f'<div class="metric-card"><div class="metric-card-title">Average Vehicle Age ({latest_year})</div><div class="metric-card-value">{latest_age:.2f} yrs</div><div class="metric-card-subtitle">Czech motorcycle park age</div></div>', unsafe_allow_html=True)
    
    prev_year = years[-2]
    prev_units = pool_data[prev_year][0]
    fleet_grow_diff = latest_units - prev_units
    fleet_grow_pct = (fleet_grow_diff / prev_units) * 100.0
    
    kpi_p3.markdown(f'<div class="metric-card"><div class="metric-card-title">YoY Fleet Growth</div><div class="metric-card-value">+{fleet_grow_diff:,} pcs</div><div class="metric-card-subtitle">Grow rate: +{fleet_grow_pct:.2f}%</div></div>', unsafe_allow_html=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        df_fleet_chart = pd.DataFrame({'Year': years, 'Fleet Size (Units)': units})
        fig_fleet_u = px.line(df_fleet_chart, x='Year', y='Fleet Size (Units)', title='Official Category L Fleet Growth (2018-2025)', markers=True)
        fig_fleet_u.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis=dict(tickformat="d"))
        st.plotly_chart(fig_fleet_u, use_container_width=True)
        
    with col_p2:
        df_fleet_age = pd.DataFrame({'Year': years, 'Average Age (Years)': ages})
        fig_fleet_a = px.line(df_fleet_age, x='Year', y='Average Age (Years)', title='Average Vehicle Age Trend (2018-2025)', markers=True, color_discrete_sequence=['#ef4444'])
        fig_fleet_a.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_fleet_a, use_container_width=True)
        
    # 2. Speculative Exports Section
    st.markdown("---")
    st.subheader("Grey Market & Speculative Export Analysis")
    st.markdown("""
    **Speculative exports** (dealer registration manipulations / homologation bypasses) represent young motorcycles 
    (under 12 or 24 months old) registered in the Czech Republic and subsequently de-registered/exported.
    - **Dealer Targets:** Dealers register vehicles locally to satisfy year-end targets and claim volume bonuses, then export them.
    - **Homologation Bypass:** Vehicles are imported, registered under easier rules in the CR, and immediately exported as "used ojetina" (already registered) to bypass homologation barriers in destination countries.
    """)
    
    cancellations_file = os.path.join(script_dir, "MOTO_Cancellations_FINAL.csv")
    if os.path.exists(cancellations_file):
        df_zru = load_cancellations(cancellations_file, os.path.getmtime(cancellations_file))
        
        age_threshold = st.slider("Select maximum vehicle age for speculative export (months):", min_value=3, max_value=36, value=24, step=1)
        
        df_young_e = df_zru[(df_zru['Age_at_Cancellation_Months'] <= age_threshold) & (df_zru['Cancellation Reason'] == 'E')]
        df_young_all = df_zru[(df_zru['Age_at_Cancellation_Months'] <= age_threshold)]
        
        col_z1, col_z2, col_z3 = st.columns(3)
        col_z1.metric(label="Total Ingested Cancellations (2022+)", value=f"{len(df_zru):,}")
        col_z2.metric(label=f"Young Cancellations (<= {age_threshold}m)", value=f"{len(df_young_all):,}")
        
        young_exp_share = (len(df_young_e) / len(df_young_all) * 100) if len(df_young_all) > 0 else 0.0
        col_z3.metric(label="Export Share of Young Cancellations", value=f"{len(df_young_e):,} units", delta=f"{young_exp_share:.1f}% of young cancellations")
        
        col_zc1, col_zc2 = st.columns(2)
        with col_zc1:
            df_brand_exp = df_young_e['Brand'].value_counts().reset_index()
            df_brand_exp.columns = ['Brand', 'Exports']
            fig_brand_exp = px.bar(df_brand_exp.head(10), x='Exports', y='Brand', orientation='h', 
                                   title=f'Top 10 Exported Brands (Age <= {age_threshold} Months)',
                                   color='Exports', color_continuous_scale='Reds')
            fig_brand_exp.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis={'categoryorder': 'total ascending'}, xaxis=dict(tickformat="d"))
            st.plotly_chart(fig_brand_exp, use_container_width=True)
            
        with col_zc2:
            df_seg_exp = df_young_e['Segment'].value_counts().reset_index()
            df_seg_exp.columns = ['Segment', 'Exports']
            fig_seg_exp = px.bar(df_seg_exp, x='Segment', y='Exports', 
                                 title=f'Exported Vehicles by Segment (Age <= {age_threshold} Months)',
                                 color_discrete_sequence=['#eab308'])
            fig_seg_exp.update_layout(template='plotly_dark', margin=dict(l=20, r=20, t=50, b=20), yaxis=dict(tickformat="d"))
            st.plotly_chart(fig_seg_exp, use_container_width=True)
            
        alarm_threshold_pct = st.slider("Set Brand Export Alarm Threshold (% of registrations):", min_value=0.5, max_value=10.0, value=3.0, step=0.1)
        
        df_reg_brand_counts = df_filt['Brand'].value_counts()
        df_zru_brand_counts = df_young_e['Brand'].value_counts()
        
        export_brand_stats = []
        for b in df_filt['Brand'].unique():
            reg_c = df_reg_brand_counts.get(b, 0)
            exp_c = df_zru_brand_counts.get(b, 0)
            exp_share = (exp_c / reg_c * 100) if reg_c > 0 else 0.0
            
            if reg_c > 10:
                export_brand_stats.append({
                    'Brand': b,
                    'Selected Registrations': reg_c,
                    'Speculative Exports': exp_c,
                    'Export Ratio': exp_share,
                    'Status': "🚨 EXPORT ALARM" if exp_share > alarm_threshold_pct else "✅ OK"
                })
                
        df_exp_stats = pd.DataFrame(export_brand_stats)
        if not df_exp_stats.empty:
            df_exp_stats = df_exp_stats.sort_values(by='Speculative Exports', ascending=False).reset_index(drop=True)
            alarms = df_exp_stats[df_exp_stats['Status'] == "🚨 EXPORT ALARM"]
            
            if not alarms.empty:
                st.markdown(f'<div class="alarm-banner">🚨 <b>Speculative Export Alarm:</b> Threshold exceeded for: <b>{", ".join(alarms["Brand"].tolist())}</b>! These brands show abnormal short-term de-registration patterns.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="ok-banner">✅ All brands are currently below the speculative export threshold.</div>', unsafe_allow_html=True)
                
            st.dataframe(df_exp_stats, column_config={
                'Export Ratio': st.column_config.NumberColumn("Export Ratio", format="%.2f %%"),
                'Selected Registrations': st.column_config.NumberColumn("Selected Registrations", format="%d"),
                'Speculative Exports': st.column_config.NumberColumn("Speculative Exports", format="%d")
            }, use_container_width=True)
            
    else:
        st.warning("Cancellations database file not found. Speculative export analysis is disabled.")
