import pandas as pd
import numpy as np
import os
import re
import unicodedata

# Paths
base_dir = r"g:\Můj disk\Moto"
orv_dir = r"g:\Můj disk\ORV\Antigravity ORV"
zru_source_dir = r"g:\Můj disk\ORV\Vyřazeno"

whitelist_path = os.path.join(orv_dir, "ORV_Whitelist_FINAL.xlsx") # Used as blacklist
mapping_path = os.path.join(base_dir, "MOTO_Model_Mapping.xlsx")
existing_xlsx_reg = os.path.join(base_dir, "MOTO_Registrations_FINAL.xlsx")
existing_xlsx_zru = os.path.join(base_dir, "MOTO_Cancellations_FINAL.xlsx")
existing_csv_zru = os.path.join(base_dir, "MOTO_Cancellations_FINAL.csv")

print("=== STARTING MOTORCYCLE CANCELLATIONS INGESTION ===")

# 1. Load Whitelist/Blacklist
print("\nLoading ORV Whitelist (Negative Filter)...")
df_wl = pd.read_excel(whitelist_path)
orv_blacklist_normal = set()
orv_blacklist_shared = {}

for idx, row in df_wl.iterrows():
    prefix = str(row['Prefix']).strip().upper()
    brand = str(row['Brand']).strip().upper()
    
    if prefix in ['LLCLSN10', 'LLCLSU50']:
        if prefix not in orv_blacklist_shared:
            orv_blacklist_shared[prefix] = set()
        orv_blacklist_shared[prefix].add(brand)
    else:
        orv_blacklist_normal.add(prefix)

# 2. Load Model Mapping Override
print("\nLoading Model Mapping Overrides...")
df_mapping = pd.read_excel(mapping_path)
model_mapping_dict = {}
for idx, row in df_mapping.iterrows():
    brand = str(row['Brand']).strip().upper()
    pattern = str(row['Model_Pattern']).strip().upper()
    disp = float(row['Displacement']) if not pd.isna(row['Displacement']) else np.nan
    fuel = str(row['Fuel']).strip() if not pd.isna(row['Fuel']) else 'Petrol'
    seg = str(row['Segment']).strip() if not pd.isna(row['Segment']) else 'Naked'
    seats = int(row['Seats']) if not pd.isna(row['Seats']) else 2
    l_year = int(row['Launch_Year']) if not pd.isna(row['Launch_Year']) else np.nan
    
    if brand not in model_mapping_dict:
        model_mapping_dict[brand] = []
    model_mapping_dict[brand].append((pattern, disp, fuel, seg, seats, l_year))

# Helpers for cleaning and parsing
def clean_brand_name(brand_raw):
    if pd.isna(brand_raw):
        return 'UNKNOWN'
    b = str(brand_raw).strip().upper()
    
    # Remove quotes, apostrophes, backticks, and replacement characters to normalize spelling anomalies
    b = b.replace("'", "").replace("`", "").replace("’", "").replace("", "")
    
    # Standardize spacing and remove leading dots
    b = re.sub(r'^\.+', '', b)
    b = b.strip()
    
    # Handle Dnepr / Dněpr first (any combination of DN and PR)
    if 'DN' in b and 'PR' in b:
        return 'DNEPR'
        
    # Handle Jawa-ČZ first
    if b in ['JAWA - ČZ', 'JAWA - Z', 'JAWA-ČZ', 'JAWA-Z', 'JAWA ČZ', 'JAWA-Z', 'JAWA - Z'] or ('JAWA' in b and ('ČZ' in b or 'Z' in b or 'ÄŚZ' in b or 'Ă\x84\x81Z' in b)):
        return 'JAWA-ČZ'
        
    # Direct mappings for ČZ (handling spacing and number suffixes safely)
    if b in ['ČZ', 'Z', 'ÄŚZ', 'Ă\x84\x81Z', 'ČESKÁ ZBROJOVKA', 'CESKA ZBROJOVKA'] or \
       any(b.startswith(x) for x in ['ČZ', 'ÄŚZ', 'Ă\x84\x81Z', 'ČESKÁ ZBROJOVKA ', 'CESKA ZBROJOVKA ']) or \
       b.startswith('Z ') or re.match(r'^Z\d+', b):
        return 'ČZ'
    if 'HECHT' in b or 'FECHT' in b:
        return 'HECHT'
    if 'INDIAN' in b or 'SCOUT BOBBER' in b:
        return 'INDIAN'
    if 'HARLEY' in b:
        return 'HARLEY-DAVIDSON'
    if 'PLAGGIO' in b:
        return 'PIAGGIO'
    if 'ROYAL ENFIELD' in b or 'ROYALENFIELD' in b:
        return 'ROYAL ENFIELD'
    if 'CHANG JIANG' in b or 'CHANGJIANG' in b:
        return 'CHANGJIANG'
    if 'MV AGUSTA' in b or 'MV AUGUSTA' in b:
        return 'MV AGUSTA'
    if 'SUPERSOCO' in b or 'SUPER SOCO' in b:
        return 'SUPER SOCO'
    if 'HUSQARNA' in b or 'HUSQVARNA' in b or 'HUSGVARNA' in b:
        return 'HUSQVARNA'
    if 'SHARENGO' in b or 'SHARE' in b:
        return "SHARE'NGO"
    if 'BIG DOG' in b:
        return 'BIG DOG'
    if 'JINPENG' in b or 'JJINPENG' in b:
        return 'JINPENG'
    if 'MOVE ECO' in b or 'MOVEECO' in b:
        return 'MOVEECO'
    if 'RACCEWAY' in b or 'RACCWAY' in b:
        return 'RACCEWAY'
    if 'SANYANG' in b or 'SAN YANG' in b or 'SHANYANG' in b:
        return 'SANYANG'
    if 'SKY TEAM' in b or 'SKYTEAM' in b or 'SKYTEM' in b:
        return 'SKYTEAM'
    if 'OPAI' in b:
        return 'OPAI KUBA ELEKTROPOWER'
    if 'ASIA WING' in b or 'ASIAWING' in b:
        return 'ASIAWING'
    if 'ZEJIANG' in b or 'ZHEJIANG' in b:
        return 'ZHEJIANG'
    if 'WS-TRIKE' in b:
        return 'WS-TRIKES'
    if 'TOTH-TWA' in b or 'THOTH-TWA' in b:
        return 'TOTH-TWA'
    if 'CFMOTO' in b or 'CF MOTO' in b:
        return 'CFMOTO'
    if 'GASGAS' in b or 'GAS GAS' in b:
        return 'GASGAS'
    if 'SURON' in b or 'SUR-RON' in b or 'SURON' in b or 'SUN-RON' in b:
        return 'SUR-RON'
    if 'BABETA' in b or 'BABETTA' in b:
        return 'BABETTA'
    if 'QUADRO' in b or 'QADRO' in b:
        return 'QUADRO VEHICLES'
    if 'FANITIC' in b or 'FANTIC' in b:
        return 'FANTIC'
    if 'SCHERCO' in b or 'SHERCO' in b:
        return 'SHERCO'
    if 'BSA' in b or 'B.S.A' in b:
        return 'B.S.A.'
    if 'MONET' in b and 'GOYON' in b:
        return 'MONET GOYON'
    if 'SAUNRA' in b or 'SUNDRA' in b or 'SUNRA' in b:
        return 'SUNRA'
    if 'SENKE' in b or 'SHENKE' in b:
        return 'SENKE'
    if 'VELOR-X-TRIKE' in b or 'VELORXTRIKE' in b:
        return 'VELOR-X-TRIKE'
    if 'XEV' in b:
        return 'XEV'
    if 'HISUN' in b or 'HSUN' in b:
        return 'HISUN'
    if 'ZHONGNENG' in b or 'ZH0NGNENG' in b:
        return 'ZHONGNENG'
    if 'KSR MOTO' in b or 'KRS MOTO' in b:
        return 'KSR MOTO'
    if 'HERCULES' in b or 'HERKULES' in b:
        return 'HERCULES'
    if 'CHATENET' in b or 'CHATANET' in b:
        return 'CHATENET'
    if 'NERACAR' in b or 'NER A CAR' in b or 'NER-A-CAR' in b:
        return 'NERACAR'
    if 'STROLLWHEEL' in b or 'STROLL WHELL' in b:
        return 'STROLLWHEEL'
    if 'BUFFLER' in b or 'BEFFLER' in b or 'BUFFER' in b or 'BUFLLER' in b:
        return 'BUFFLER'
    if 'E-CRUIZER' in b or 'E-CRUISER' in b:
        return 'E-CRUIZER'
    if 'MOTOBECANE' in b or 'MOTOBEC' in b or 'MOTOBC' in b:
        return 'MOTOBECANE'
    if 'ZUNDAPP' in b or 'ZÜNDAPP' in b:
        return 'ZÜNDAPP'
    if 'TALARIA' in b or 'TALATIA' in b:
        return 'TALARIA'
    if 'M72' in b or 'M 72' in b or 'M-72' in b:
        return 'M72'
    if 'CAN-AM' in b or 'CAN AM' in b:
        return 'CAN-AM'
    if 'HORWIN' in b or 'BORWIN' in b:
        return 'HORWIN'
    if 'FANTIC' in b:
        return 'FANTIC'
    if 'KENTOYA' in b:
        return 'KENTOYA'
    if any(x in b for x in ['BOMBARDIER', 'BRP']):
        return 'BRP'
    if 'ROMET' in b:
        return 'ROMET'
    if 'BARTON' in b:
        return 'BARTON'
    if 'YUNLONG' in b:
        return 'YUNLONG'
    if 'SMARDA' in b:
        return 'SMARDA'
    if 'GOLDEN LION' in b or 'GOLDENLION' in b:
        return 'GOLDENLION'
    if 'HOOOON' in b:
        return 'HOOOON'
    if 'BOOM' in b:
        return 'BOOM'
    if 'CHAOYA' in b:
        return 'CHAOYA'
    if 'MODIKA' in b:
        return 'MODIKA'
    if 'YUKI' in b:
        return 'YUKI'
    if 'VICTORY' in b:
        return 'VICTORY'
    if 'ACCESS' in b or 'ACCES MOTOR' in b:
        return 'ACCESS'
    if 'VELOREX' in b:
        return 'VELOREX'
    if 'SIMSON' in b:
        return 'SIMSON'
    if 'NORTON' in b:
        return 'NORTON'
    if 'MZ' in b:
        return 'MZ'
    if 'MBK' in b:
        return 'MBK'
    if 'MANET' in b:
        return 'MANET'
    if 'ARIEL' in b:
        return 'ARIEL'
    if 'KMZ' in b:
        return 'KMZ'
    if 'DAELIM' in b:
        return 'DAELIM'
    if 'DKW' in b:
        return 'DKW'
    if 'IMZ' in b:
        return 'IMZ'
    if 'VESPA' in b:
        return 'VESPA'
    if 'SENKE' in b:
        return 'SENKE'
    if 'MATCHLESS' in b:
        return 'MATCHLESS'
    if 'HYOSUNG' in b:
        return 'HYOSUNG'
    if 'NSU' in b:
        return 'NSU'
    if 'BUELL' in b:
        return 'BUELL'
    if 'TATRAN' in b:
        return 'TATRAN'
    if 'TERROT' in b:
        return 'TERROT'
    if 'BAOTIAN' in b:
        return 'BAOTIAN'
    if 'DAYTONA' in b:
        return 'DAYTONA'
    if 'HUSABERG' in b:
        return 'HUSABERG'
    if 'KSR MOTO' in b:
        return 'KSR MOTO'
    if 'YIYING' in b:
        return 'YIYING'
    if 'LINTEX' in b:
        return 'LINTEX'
    if 'WK TRIKES' in b or 'WK' in b:
        return 'WK TRIKES'
    if 'SACHS' in b:
        return 'SACHS'
    if 'ČEZETA' in b or 'CEZETA' in b:
        return 'ČEZETA'
    if 'ECOOTER' in b:
        return 'ECOOTER'
    if 'LML' in b:
        return 'LML'
    if 'SFM' in b:
        return 'SFM'
    if 'PUCH' in b:
        return 'PUCH'
    if 'KREIDLER' in b:
        return 'KREIDLER'
    if 'QJ' in b:
        return 'QJ MOTOR'
    if 'DAYI' in b:
        return 'DAYI MOTOR'
    if b == 'RICH' or b == 'RICHS' or b.startswith('RICH '):
        return 'RICH MOTORS'
    if 'VMOTO' in b:
        return 'VMOTO'
        
    if 'JAWA' in b or b == '350 SPORT':
        return 'JAWA'
        
    b = b.replace(' MOTORCYKLY', '').replace(' MOTORCYKLE', '').replace(' MOTORCYCLE', '').replace(' MOTORCYCLES', '')
    b = b.replace(' MOTOR', '').replace(' MOTORS', '')
    b = b.replace(' S.R.O.', '').replace(' S R O', '').replace(' S. R. O.', '')
    b = b.replace(' A.S.', '').replace(' A S', '').replace(' A. S.', '')
    b = b.strip()
    
    if b == '125 C' or b == '125 ZDB' or b == '487.016' or b == '487' or b == '487 016':
        return 'ČZ'
    if b == '300 SEF-R' or b == '300 SEF R' or b == 'SEF-R':
        return 'SHERCO'
    if b == '2 RB' or b == '2RB':
        return 'GASGAS'
    if b == 'A. SCHUH' or b == 'A.SCHUH':
        return 'A.SCHUH'
    if b == 'A.J.S' or b == 'A.J.S.':
        return 'A.J.S.'
        
    return b

def clean_numeric(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    if ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except:
        return val

def clean_int(val):
    num = clean_numeric(val)
    if pd.isna(num):
        return np.nan
    try:
        return int(num)
    except:
        return val

def parse_date_dt(date_val):
    if pd.isna(date_val):
        return None, None
    d_str = str(date_val).strip()
    if ',' in d_str:
        d_str = d_str.split(',')[0]
    if '.' in d_str:
        d_str = d_str.split('.')[0]
    
    d_str = d_str.strip()
    if len(d_str) == 8 and d_str.isdigit():
        yyyy = int(d_str[:4])
        mm = int(d_str[4:6])
        dd = int(d_str[6:8])
        try:
            return pd.Timestamp(year=yyyy, month=mm, day=dd), mm
        except:
            return None, None
    return None, None

# Expanded list of electric brands
electric_brands = {
    'TALARIA', 'SMARDA', 'RACCEWAY', 'HECHT', 'GOLDENLION', 'VMOTO', 'ELS MOTO', 
    'STARK', 'CHAOYA', 'SUR-RON', 'SUPER SOCO', 'NERVA', 'JINPENG', 'SHANSU', 
    'KEREN', 'SLANE', 'HORWIN', 'NIU', 'TROMOX', 'TINY', 'AKUMOTO', 'HECHT MOTORS',
    'DAYI MOTOR', 'SUNRA', 'MOVEECO', 'LADEAEV', 'BENOD', 'SEGWAY'
}

def parse_moto_attributes(row):
    brand = clean_brand_name(row['Značka'])
    model = str(row['Model_Raw']).strip().upper() if not pd.isna(row['Model_Raw']) else ""
    cat = str(row['Category']).strip().upper() if not pd.isna(row['Category']) else ""
    
    # Check Model Mapping Override
    if brand in model_mapping_dict:
        for pattern, disp, fuel, seg, seats, l_year in model_mapping_dict[brand]:
            if pattern in model:
                disp_group = 'Unknown'
                if fuel == 'Electric':
                    disp_group = 'Electric'
                elif not pd.isna(disp):
                    if disp <= 50: disp_group = 'Until 50 ccm'
                    elif disp <= 125: disp_group = 'Until 125 ccm'
                    elif disp <= 350: disp_group = 'Until 350 ccm'
                    elif disp <= 500: disp_group = 'Until 500 ccm'
                    elif disp <= 800: disp_group = 'Until 800 ccm'
                    else: disp_group = 'Over 800 ccm'
                return fuel, disp, disp_group, seg, seats, l_year
                
    # Rule-based parsing
    fuel = 'Petrol'
    is_electric = False
    
    if any(eb in brand for eb in electric_brands):
        is_electric = True
    elif 'ELECTRIC' in model or 'EV' in model or 'ELEKTRICK' in model:
        is_electric = True
    elif brand == 'BMW' and ('CE 04' in model or 'CE 02' in model or 'CE04' in model or 'CE02' in model):
        is_electric = True
    elif brand == 'HONDA' and 'EM1' in model:
        is_electric = True
        
    if is_electric:
        fuel = 'Electric'
        
    displacement = 0.0
    if fuel == 'Petrol':
        nums_model = re.findall(r'\d+', model)
        parsed_ccm = None
        for num_str in nums_model:
            num = int(num_str)
            if 49 <= num <= 2500 and num not in [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]:
                parsed_ccm = float(num)
                break
                
        if parsed_ccm is None:
            if 'MT-07' in model or 'MT07' in model: parsed_ccm = 689.0
            elif 'MT-09' in model or 'MT09' in model: parsed_ccm = 890.0
            elif 'MT-03' in model or 'MT03' in model: parsed_ccm = 321.0
            elif 'MT-10' in model or 'MT10' in model: parsed_ccm = 998.0
            elif 'R7' in model: parsed_ccm = 689.0
            elif 'R1' in model: parsed_ccm = 998.0
            elif 'R3' in model: parsed_ccm = 321.0
            elif 'R6' in model: parsed_ccm = 599.0
            elif 'V7' in model: parsed_ccm = 744.0
            elif 'V9' in model: parsed_ccm = 853.0
            elif 'V85' in model: parsed_ccm = 853.0
            
        if parsed_ccm is not None:
            displacement = parsed_ccm
        else:
            displacement = np.nan
            
    disp_group = 'Unknown'
    if fuel == 'Electric':
        disp_group = 'Electric'
    elif not pd.isna(displacement):
        if displacement <= 50: disp_group = '≤ 50 ccm'
        elif displacement <= 125: disp_group = '≤ 125 ccm'
        elif displacement <= 350: disp_group = '≤ 350 ccm'
        elif displacement <= 500: disp_group = '≤ 500 ccm'
        elif displacement <= 800: disp_group = '≤ 800 ccm'
        else: disp_group = '> 800 ccm'
        
    segment = 'Naked'
    if brand == 'INDIAN':
        if 'FTR' in model:
            segment = 'Naked'
        elif any(x in model for x in ['ROADMASTER', 'CHALLENGER', 'PURSUIT', 'CHIEFTAIN', 'CHIEF TAIN']):
            segment = 'Touring'
        else:
            segment = 'Cruiser'
    elif cat == 'L51' or cat == 'L5' or cat.startswith('L5'):
        segment = 'Tricycle'
    elif 'MP3' in model or 'METROPOLIS' in model or 'RYKER' in model or 'SPYDER' in model or 'TRICITY' in model:
        segment = 'Tricycle'
    elif any(kw in model for kw in ['E-BABETA', 'BABETA', 'KORADO', 'BETIS', 'SUPERMAXI', 'MOPED']):
        segment = 'Moped'
    elif any(kw in model for kw in ['PCX', 'WW125', 'NSC', 'NSS', 'FORZA', 'SH125', 'SH150', 'SH300', 'SH350', 'VESPA', 'PRIMAVERA', 'MEDLEY', 'LIBERTY', 'BEVERLY', 'SR GT', 'ARDOUR', 'OPTIMUS', 'MATADOR', 'DISCOVER', 'BUCK', 'MOJITO', 'SCARABEO', 'FLY', 'TYPHOON', 'DJANGO', 'TWEET', 'KISBEE', 'VISTA', 'CITIS', 'COCIS', 'EQUIS']):
        segment = 'Scooter'
    elif any(kw in model for kw in ['GS', 'ADVENTURE', 'TENERE', 'XTZ', 'AFRICA', 'TRANSALP', 'HIMALAYAN', 'TIGER', 'V-STROM', 'DL650', 'DL1050', 'CRF300', 'CRF1100', '450MT', '800MT', '700MT', 'SRT', 'MARATHON', 'KAPLAN', 'VALKYRIE']):
        segment = 'Adventure / Enduro'
    elif any(kw in model for kw in ['REBEL', 'CMX', 'SHADOW', 'VT750', 'INTRUDER', 'VULCAN', 'DRAGSTAR', 'VIRAGO', 'VN900', 'SOFTAIL', 'ROAD KING', 'FAT BOY', 'FATBOY', 'BOBBER', 'SPEEDMASTER', 'CUSTOM', 'SPORTSTER', 'HERITAGE', 'BREAKOUT', 'ROAD GLIDE', 'STREET GLIDE', 'ELECTRA GLIDE', 'SUPER GLIDE', 'DYNA']):
        segment = 'Cruiser'
    elif any(kw in model for kw in ['CBR', 'YZF', 'R1', 'R6', 'R3', 'R7', 'R125', 'NINJA', 'ZX6R', 'ZX10R', 'GSXR', 'SR-R', '675SR', '450SR', 'PANIGALE', 'SUPERSPORT', 'RS660', 'RSV4']):
        segment = 'Sport'
    elif any(kw in model for kw in ['RT', 'K1600', 'GOLDWING', 'FJR', 'GTR', 'PAN EUROPEAN', 'NT1100', 'TRACER', 'VERSYS', 'GT', 'CONCOURS', 'MULTISTRADA']):
        segment = 'Touring'
    elif any(kw in model for kw in ['Z900', 'Z650', 'DUKE', 'MT-07', 'MT-09', 'MT-03', 'MT-10', 'CB500', 'CB650', 'CB1000', 'CB750', 'HORNET', 'MONSTER', 'STREET TRIPLE', 'SPEED TRIPLE', 'SV650', 'NAKED', 'SCRAMBLER', 'BONNEVILLE', 'THRUXTON', 'INTERCEPTOR', 'CONTINENTAL GT', 'V7', 'V9', 'NK', 'CL500', 'GB350', 'CB125']):
        segment = 'Naked'
        
    seats = 2
    if segment == 'Moped' or segment == 'Sport':
        seats = 1
        
    launch_year = np.nan
    return fuel, displacement, disp_group, segment, seats, launch_year

# 3. Process ZRU files
zru_cols = [
    'PŮV', 'Brand_Code', 'Model_Code', 'Model2_Code', 'Year', 'VIN', 'Type_Code', 
    'Category', 'Model_Raw', 'Total Mass', 'Fuel_Code', 'First_Reg_Date_Raw', 
    'Cancellation_Date_Raw', 'Cancellation_Reason', 'Značka'
]

zru_files = sorted([f for f in os.listdir(zru_source_dir) if f.startswith('ZRU') and f.endswith('.xlsx')])
print(f"Found {len(zru_files)} monthly ZRU files to process.")

ingested_cancellations = []
excluded_orv_blacklist = 0
excluded_l6_l7 = 0
total_raw_rows = 0

for zru_file in zru_files:
    file_path = os.path.join(zru_source_dir, zru_file)
    print(f"Processing Cancellation: {zru_file}...")
    
    # Read without header
    df_raw = pd.read_excel(file_path, header=None)
    df_raw = df_raw.iloc[:, :15]
    df_raw.columns = zru_cols
    total_raw_rows += len(df_raw)
    
    df_raw['Category'] = df_raw['Category'].astype(str).str.strip().str.upper()
    df_l = df_raw[df_raw['Category'].str.startswith('L')].copy()
    
    # Process all Category L rows (including L6/L7 quadricycles)
    for idx, row in df_l.iterrows():
        vin = str(row['VIN']).strip().upper()
        brand = clean_brand_name(row['Značka'])
        
        # Check ORV blacklist
        is_orv = False
        if vin.startswith('3223404'):
            is_orv = True
        elif len(vin) >= 8:
            p8 = vin[:8]
            if p8 in orv_blacklist_normal:
                is_orv = True
            elif p8 in orv_blacklist_shared:
                if any(ob in brand for ob in orv_blacklist_shared[p8]):
                    is_orv = True
                    
        # Count ORVs for info
        if is_orv:
            excluded_orv_blacklist += 1
            
        # Parse Dates
        first_reg_date, _ = parse_date_dt(row['First_Reg_Date_Raw'])
        cancellation_date, cancellation_month = parse_date_dt(row['Cancellation_Date_Raw'])
        
        cancellation_month_val = int(cancellation_month) if cancellation_month else None
        cancellation_year = int(cancellation_date.year) if cancellation_date else None
        
        # Clean numeric
        mass = clean_numeric(row['Total Mass'])
        mass_group = int(round(mass / 100.0) * 100.0) if not pd.isna(mass) else None
        puv_clean = clean_int(row['PŮV'])
        year_clean = clean_int(row['Year'])
        
        # Parse properties
        fuel, displacement, disp_group, segment, seats, launch_year = parse_moto_attributes(row)
        
        # Override Segment for quadricycles / ORVs / utility trikes
        cat_upper = str(row['Category']).strip().upper() if not pd.isna(row['Category']) else ""
        brand_upper = str(row['Značka']).strip().upper() if not pd.isna(row['Značka']) else "NONE"
        model_upper = str(row['Model_Raw']).strip().upper() if not pd.isna(row['Model_Raw']) else ""
        
        is_l6_l7 = cat_upper.startswith(('L6', 'L7'))
        
        if is_orv:
            segment = 'ATV / UTV (Category L)'
        elif is_l6_l7:
            if any(mb in brand_upper for mb in ['AIXAM', 'LIGIER', 'MICROCAR', 'XEV', 'ZHIDOU', 'CHATENET', 'BELLIER', 'CASALINI', 'GRECAV', 'JDM', 'CARGO']):
                segment = 'Microcar / Quadricycle'
            else:
                segment = 'Utility / Other L6-L7'
        elif any(ut in brand_upper for ut in ['HECHT', 'JINPENG', 'SELVO', 'SMARDA', 'GOLDENLION', 'SLANE', 'RACCEWAY', 'BENYCARGO', 'LMI']) or cat_upper.startswith(('L2', 'L5')):
            if any(mb in brand_upper for mb in ['AIXAM', 'LIGIER', 'MICROCAR', 'XEV', 'ZHIDOU']):
                segment = 'Microcar / Quadricycle'
            elif any(ob in brand_upper for ob in ['BRP', 'CAN-AM', 'POLARIS', 'TGB', 'CFMOTO', 'SEGWAY', 'GOES', 'LINHAI', 'ACCESS']) and ('GLADIATOR' in model_upper or 'SNARLER' in model_upper or 'RZR' in model_upper or 'RANGER' in model_upper or 'OUTLANDER' in model_upper):
                segment = 'ATV / UTV (Category L)'
            else:
                segment = 'Utility / Other Trike'
        
        ingested_cancellations.append({
            'Registration ID': puv_clean,
            'First Registration Date': first_reg_date,
            'Cancellation Date': cancellation_date,
            'Cancellation Month': cancellation_month_val,
            'Cancellation Year': cancellation_year,
            'VIN': row['VIN'],
            'VIN Prefix': vin[:8] if len(vin) >= 8 else vin,
            'Category': row['Category'],
            'Total Mass': mass,
            'Total Mass Group': mass_group,
            'Year of Manufacture': year_clean,
            'Cancellation Reason': row['Cancellation_Reason'],
            'Brand': brand,
            'Model': row['Model_Raw'],
            'Displacement': displacement,
            'Displacement Group': disp_group,
            'Fuel': fuel,
            'Segment': segment,
            'Total seats': seats,
            'Launch Year': launch_year
        })

print("\nIngestion Completed!")
print(f"  Total raw rows scanned: {total_raw_rows}")
print(f"  Excluded as L6/L7 quadricycles: {excluded_l6_l7}")
print(f"  Excluded by ORV Blacklist: {excluded_orv_blacklist}")
print(f"  Successfully Ingested Cancellations: {len(ingested_cancellations)}")

# 4. Enrich cancellations with registrations (join on VIN) to get geographical data
if len(ingested_cancellations) > 0:
    df_zru_df = pd.DataFrame(ingested_cancellations)
    
    # Load registrations database to join
    if os.path.exists(existing_xlsx_reg):
        print(f"\nLoading registrations database from {existing_xlsx_reg} to enrich cancellations with geographical data...")
        df_reg_all = pd.read_excel(existing_xlsx_reg)
        
        # Drop duplicates in registrations VIN to avoid many-to-one mapping
        df_reg_subset = df_reg_all.drop_duplicates(subset=['VIN'])[[
            'VIN', 'District', 'Kraj', 'Region', 'Municipality', 'Owner Type', 'Leasing', 'Color'
        ]]
        
        # Join
        df_enriched_zru = pd.merge(df_zru_df, df_reg_subset, on='VIN', how='left')
        print(f"Enriched {df_enriched_zru['Kraj'].notna().sum()} rows with geographical registration details out of {len(df_enriched_zru)}.")
        
        # Fill missing values
        df_enriched_zru['District'] = df_enriched_zru['District'].fillna('Unknown')
        df_enriched_zru['Kraj'] = df_enriched_zru['Kraj'].fillna('Unknown')
        df_enriched_zru['Region'] = df_enriched_zru['Region'].fillna('Unknown')
        df_enriched_zru['Municipality'] = df_enriched_zru['Municipality'].fillna('Unknown')
        df_enriched_zru['Owner Type'] = df_enriched_zru['Owner Type'].fillna(-1).astype(int)
        df_enriched_zru['Leasing'] = df_enriched_zru['Leasing'].fillna('Unknown')
        df_enriched_zru['Color'] = df_enriched_zru['Color'].fillna('Unknown')
        
    else:
        print("\nRegistrations database does not exist yet. Geographical fields will be set to Unknown.")
        df_enriched_zru = df_zru_df
        for col in ['District', 'Kraj', 'Region', 'Municipality', 'Leasing', 'Color']:
            df_enriched_zru[col] = 'Unknown'
        df_enriched_zru['Owner Type'] = -1
    
    # Sort
    df_enriched_zru = df_enriched_zru.sort_values(by=['Cancellation Date', 'Brand']).reset_index(drop=True)
    
    # Save Excel
    print(f"\nSaving cancellations database to Excel: {existing_xlsx_zru}")
    df_enriched_zru.to_excel(existing_xlsx_zru, index=False)
    print("Saved Excel successfully!")
    
    # Save CSV
    print(f"Saving cancellations database to CSV: {existing_csv_zru}")
    df_enriched_zru.to_csv(existing_csv_zru, sep=';', index=False, date_format='%d.%m.%Y', encoding='utf-8')
    print("Saved CSV successfully!")
    
else:
    print("\nNo cancellations were ingested. Finished.")

print("\n=== DATA INGESTION COMPLETED SUCCESSFULLY ===")
