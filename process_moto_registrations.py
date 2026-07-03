import pandas as pd
import numpy as np
import os
import re
import unicodedata

# Paths
base_dir = r"g:\Můj disk\Moto"
orv_dir = r"g:\Můj disk\ORV\Antigravity ORV"
reg_source_dir = r"g:\Můj disk\ORV\Registrace"

whitelist_path = os.path.join(orv_dir, "ORV_Whitelist_FINAL.xlsx") # Used as blacklist
mapping_path = os.path.join(base_dir, "MOTO_Model_Mapping.xlsx")
existing_xlsx = os.path.join(base_dir, "MOTO_Registrations_FINAL.xlsx")
existing_csv = os.path.join(base_dir, "MOTO_Registrations_FINAL.csv")

print("=== STARTING MOTORCYCLE DATA INGESTION (HISTORICAL & MONTHLY) ===")

# 1. Load Whitelist/Blacklist
print("\nLoading ORV Whitelist (Negative Filter)...")
df_wl = pd.read_excel(whitelist_path)
print(f"Loaded {len(df_wl)} ORV whitelist rows.")

# Create blacklist set for fast lookup
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
print(f"Loaded {len(df_mapping)} model mapping override rows.")

# Create mapping dictionary for fast matching
# Structure: {brand: [(pattern, displacement, fuel, segment, seats, launch_year)]}
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
def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.upper().strip()
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

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
    if 'SURRON' in b or 'SUR-RON' in b or 'SURON' in b or 'SUN-RON' in b:
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

district_to_region = {
    'HLAVNI MESTO PRAHA': 'Hlavní město Praha', 'PRAHA': 'Hlavní město Praha',
    'BENESOV': 'Středočeský kraj', 'BEROUN': 'Středočeský kraj', 'KLADNO': 'Středočeský kraj',
    'KOLIN': 'Středočeský kraj', 'KUTNA HORA': 'Středočeský kraj', 'MELNIK': 'Středočeský kraj',
    'MLADA BOLESLAV': 'Středočeský kraj', 'NYMBURK': 'Středočeský kraj', 'PRAHA-VYCHOD': 'Středočeský kraj',
    'PRAHA-ZAPAD': 'Středočeský kraj', 'PRIBRAM': 'Středočeský kraj', 'RAKOVNIK': 'Středočeský kraj',
    'CESKE BUDEJOVICE': 'Jihočeský kraj', 'CESKY KRUMLOV': 'Jihočeský kraj', 'JINDRICHUV HRADEC': 'Jihočeský kraj',
    'PISEK': 'Jihočeský kraj', 'PRACHATICE': 'Jihočeský kraj', 'STRAKONICE': 'Jihočeský kraj', 'TABOR': 'Jihočeský kraj',
    'DOMAZLICE': 'Plzeňský kraj', 'KLATOVY': 'Plzeňský kraj', 'PLZEN-MESTO': 'Plzeňský kraj', 'PLZEN-JIH': 'Plzeňský kraj',
    'PLZEN-SEVER': 'Plzeňský kraj', 'ROKYCANY': 'Plzeňský kraj', 'TACHOV': 'Plzeňský kraj', 'PLZEN': 'Plzeňský kraj',
    'CHEB': 'Karlovarský kraj', 'KARLOVY VARY': 'Karlovarský kraj', 'SOKOLOV': 'Karlovarský kraj',
    'DECIN': 'Ústecký kraj', 'CHOMUTOV': 'Ústecký kraj', 'LITOMERICE': 'Ústecký kraj', 'LOUNY': 'Ústecký kraj',
    'MOST': 'Ústecký kraj', 'TEPLICE': 'Ústecký kraj', 'USTI NAD LABEM': 'Ústecký kraj',
    'CESKA LIPA': 'Liberecký kraj', 'JABLONEC NAD NISOU': 'Liberecký kraj', 'LIBEREC': 'Liberecký kraj', 'SEMILY': 'Liberecký kraj',
    'HRADEC KRALOVE': 'Královéhradecký kraj', 'JICIN': 'Královéhradecký kraj', 'NACHOD': 'Královéhradecký kraj',
    'RYCHNOV NAD KNEZNOU': 'Královéhradecký kraj', 'TRUTNOV': 'Královéhradecký kraj',
    'CHRUDIM': 'Pardubický kraj', 'PARDUBICE': 'Pardubický kraj', 'SVITAVY': 'Pardubický kraj', 'USTI NAD ORLICI': 'Pardubický kraj',
    'HAVLICKUV BROD': 'Kraj Vysočina', 'JIHLAVA': 'Kraj Vysočina', 'PELHRIMOV': 'Kraj Vysočina', 'TREBIC': 'Kraj Vysočina', 'ZDAR NAD SAZAVOU': 'Kraj Vysočina',
    'BLANSKO': 'Jihomoravský kraj', 'BRNO-MESTO': 'Jihomoravský kraj', 'BRNO-VENKOV': 'Jihomoravský kraj', 'BRECLAV': 'Jihomoravský kraj',
    'HODONIN': 'Jihomoravský kraj', 'VYSKOV': 'Jihomoravský kraj', 'ZNOJMO': 'Jihomoravský kraj', 'BRNO': 'Jihomoravský kraj',
    'JESENIK': 'Olomoucký kraj', 'OLOMOUC': 'Olomoucký kraj', 'PROSTEJOV': 'Olomoucký kraj', 'PREROV': 'Olomoucký kraj', 'SUMPERK': 'Olomoucký kraj',
    'KROMERIZ': 'Zlínský kraj', 'UHERSKE HRADISTE': 'Zlínský kraj', 'VSETIN': 'Zlínský kraj', 'ZLIN': 'Zlínský kraj',
    'BRUNTAL': 'Moravskoslezský kraj', 'FRYDEK-MISTEK': 'Moravskoslezský kraj', 'KARVINA': 'Moravskoslezský kraj',
    'NOVY JICIN': 'Moravskoslezský kraj', 'OPAVA': 'Moravskoslezský kraj', 'OSTRAVA-MESTO': 'Moravskoslezský kraj'
}

region_en_mapping = {
    'Praha': 'Prague', 'Středočeský': 'Central Bohemia', 'Jihočeský': 'South Bohemia', 'Plzeňský': 'Plzeň',
    'Karlovarský': 'Karlovy Vary', 'Ústecký': 'Ústí nad Labem', 'Liberecký': 'Liberec', 'Královéhradecký': 'Hradec Králové',
    'Pardubický': 'Pardubice', 'Vysočina': 'Vysočina', 'Jihomoravský': 'South Moravia', 'Olomoucký': 'Olomouc',
    'Zlínský': 'Zlín', 'Moravskoslezský': 'Moravia-Silesia', 'Unknown': 'Unknown'
}

def get_region(district):
    if not isinstance(district, str) or pd.isna(district):
        return "Neznámý kraj"
    d_norm = normalize_text(district)
    if d_norm in district_to_region:
        return district_to_region[d_norm]
    if "PRAHA" in d_norm:
        return "Hlavní město Praha"
    if "PLZEN" in d_norm:
        return "Plzeňský kraj"
    if "BRNO" in d_norm:
        return "Jihomoravský kraj"
    if "OSTRAVA" in d_norm:
        return "Moravskoslezský kraj"
    if "RYCHNOV" in d_norm:
        return "Královéhradecký kraj"
    if "HRADISTE" in d_norm:
        return "Zlínský kraj"
    if "USTI" in d_norm:
        if "LABEM" in d_norm:
            return "Ústecký kraj"
        if "ORLICI" in d_norm:
            return "Pardubický kraj"
    return "Neznámý kraj"

def map_color_code(code):
    if pd.isna(code):
        return 'Other / Multicolor'
    try:
        c = int(float(str(code).replace(',', '.')))
    except:
        return 'Other / Multicolor'
    color_map = {
        50: 'Black', 100: 'Black',
        207: 'Grey', 10: 'Grey', 20: 'Grey', 30: 'Grey', 40: 'Grey', 70: 'Grey', 80: 'Grey', 120: 'Grey',
        202: 'Orange', 18: 'Orange', 28: 'Orange', 38: 'Orange', 48: 'Orange', 98: 'Orange',
        206: 'Green', 14: 'Green', 24: 'Green', 34: 'Green', 44: 'Green', 84: 'Green',
        15: 'Green', 25: 'Green', 35: 'Green', 45: 'Green', 85: 'Green',
        16: 'Green', 26: 'Green', 36: 'Green', 46: 'Green', 86: 'Green',
        203: 'Red', 19: 'Red', 29: 'Red', 39: 'Red', 49: 'Red', 89: 'Red',
        208: 'Brown', 11: 'Brown', 21: 'Brown', 31: 'Brown', 41: 'Brown', 81: 'Brown',
        201: 'Yellow', 17: 'Yellow', 27: 'Yellow', 37: 'Yellow', 47: 'Yellow', 88: 'Yellow', 97: 'Yellow', 138: 'Yellow',
        200: 'White',
        205: 'Blue', 13: 'Blue', 23: 'Blue', 33: 'Blue', 43: 'Blue', 83: 'Blue',
        204: 'Violet', 12: 'Violet', 22: 'Violet', 32: 'Violet', 42: 'Violet', 82: 'Violet',
        300: 'Other / Multicolor', 91: 'Other / Multicolor', 92: 'Other / Multicolor'
    }
    return color_map.get(c, 'Other / Multicolor')

def clean_numeric(val):
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    if ',' in val_str:
        val_str = val_str.split(',')[0]
    if '.' in val_str:
        val_str = val_str.split('.')[0]
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
    elif len(d_str) == 6 and d_str.isdigit():
        yy = int(d_str[:2])
        mm = int(d_str[2:4])
        dd = int(d_str[4:6])
        try:
            return pd.Timestamp(year=2000 + yy, month=mm, day=dd), mm
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
    model = str(row['Model']).strip().upper() if not pd.isna(row['Model']) else ""
    model2 = str(row['Model2']).strip().upper() if not pd.isna(row['Model2']) else ""
    cat = str(row['Kategorie']).strip().upper() if not pd.isna(row['Kategorie']) else ""
    
    # STEP 1: Check Model Mapping Override
    if brand in model_mapping_dict:
        for pattern, disp, fuel, seg, seats, l_year in model_mapping_dict[brand]:
            if pattern in model or pattern in model2:
                # Found override!
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
                
    # STEP 2: Rule-based parsing
    # 1. Determine Fuel
    fuel = 'Petrol'
    is_electric = False
    
    if any(eb in brand for eb in electric_brands):
        is_electric = True
    elif 'ELECTRIC' in model or 'ELECTRIC' in model2 or 'EV' in model or 'ELEKTRICK' in model or 'ELEKTRICK' in model2:
        is_electric = True
    elif brand == 'BMW' and ('CE 04' in model or 'CE 02' in model or 'CE04' in model or 'CE02' in model):
        is_electric = True
    elif brand == 'HONDA' and 'EM1' in model:
        is_electric = True
        
    if is_electric:
        fuel = 'Electric'
        
    # 2. Determine Displacement
    displacement = 0.0
    if fuel == 'Petrol':
        nums_model = re.findall(r'\d+', model)
        nums_model2 = re.findall(r'\d+', model2)
        all_nums = nums_model + nums_model2
        
        parsed_ccm = None
        for num_str in all_nums:
            num = int(num_str)
            if 49 <= num <= 2500 and num not in [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]:
                parsed_ccm = float(num)
                break
                
        # Specific model adjustments if regex missed
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
            
    # 3. Determine Displacement Group
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
        
    # 4. Determine Segment
    segment = 'Naked'  # Default
    if brand == 'INDIAN':
        if 'FTR' in model or 'FTR' in model2:
            segment = 'Naked'
        elif any(x in model or x in model2 for x in ['ROADMASTER', 'CHALLENGER', 'PURSUIT', 'CHIEFTAIN', 'CHIEF TAIN']):
            segment = 'Touring'
        else:
            segment = 'Cruiser'
    elif cat == 'L51' or cat == 'L5' or cat.startswith('L5'):
        segment = 'Tricycle'
    elif 'MP3' in model or 'METROPOLIS' in model or 'RYKER' in model or 'SPYDER' in model or 'TRICITY' in model:
        segment = 'Tricycle'
    elif any(kw in model or kw in model2 for kw in ['E-BABETA', 'BABETA', 'KORADO', 'BETIS', 'SUPERMAXI', 'MOPED']):
        segment = 'Moped'
    elif any(kw in model or kw in model2 for kw in ['PCX', 'WW125', 'NSC', 'NSS', 'FORZA', 'SH125', 'SH150', 'SH300', 'SH350', 'VESPA', 'PRIMAVERA', 'MEDLEY', 'LIBERTY', 'BEVERLY', 'SR GT', 'ARDOUR', 'OPTIMUS', 'MATADOR', 'DISCOVER', 'BUCK', 'MOJITO', 'SCARABEO', 'FLY', 'TYPHOON', 'DJANGO', 'TWEET', 'KISBEE', 'VISTA', 'CITIS', 'COCIS', 'EQUIS']):
        segment = 'Scooter'
    elif any(kw in model or kw in model2 for kw in ['GS', 'ADVENTURE', 'TENERE', 'XTZ', 'AFRICA', 'TRANSALP', 'HIMALAYAN', 'TIGER', 'V-STROM', 'DL650', 'DL1050', 'CRF300', 'CRF1100', '450MT', '800MT', '700MT', 'SRT', 'MARATHON', 'KAPLAN', 'VALKYRIE']):
        segment = 'Adventure / Enduro'
    elif any(kw in model or kw in model2 for kw in ['REBEL', 'CMX', 'SHADOW', 'VT750', 'INTRUDER', 'VULCAN', 'DRAGSTAR', 'VIRAGO', 'VN900', 'SOFTAIL', 'ROAD KING', 'FAT BOY', 'FATBOY', 'BOBBER', 'SPEEDMASTER', 'CUSTOM', 'SPORTSTER', 'HERITAGE', 'BREAKOUT', 'ROAD GLIDE', 'STREET GLIDE', 'ELECTRA GLIDE', 'SUPER GLIDE', 'DYNA']):
        segment = 'Cruiser'
    elif any(kw in model or kw in model2 for kw in ['CBR', 'YZF', 'R1', 'R6', 'R3', 'R7', 'R125', 'NINJA', 'ZX6R', 'ZX10R', 'GSXR', 'SR-R', '675SR', '450SR', 'DUCATI PANIGALE', 'PANIGALE', 'SUPERSPORT', 'RS660', 'RSV4']):
        segment = 'Sport'
    elif any(kw in model or kw in model2 for kw in ['RT', 'K1600', 'GOLDWING', 'FJR', 'GTR', 'PAN EUROPEAN', 'NT1100', 'TRACER', 'VERSYS', 'GT', 'CONCOURS', 'TROPHY', 'MULTISTRADA']):
        segment = 'Touring'
    elif any(kw in model or kw in model2 for kw in ['Z900', 'Z650', 'DUKE', 'MT-07', 'MT-09', 'MT-03', 'MT-10', 'CB500', 'CB650', 'CB1000', 'CB750', 'HORNET', 'MONSTER', 'STREET TRIPLE', 'SPEED TRIPLE', 'SV650', 'NAKED', 'SCRAMBLER', 'BONNEVILLE', 'THRUXTON', 'INTERCEPTOR', 'CONTINENTAL GT', 'V7', 'V9', 'NK', 'CL500', 'GB350', 'CB125']):
        segment = 'Naked'
        
    seats = 2
    if segment == 'Moped' or segment == 'Sport':
        seats = 1
        
    launch_year = np.nan
    return fuel, displacement, disp_group, segment, seats, launch_year

# 3. Main Data Processing Loop
ingested_records = []
excluded_orv_blacklist = 0
excluded_l6_l7 = 0
total_raw_rows = 0

# 3a. Process REG2018_2021.csv
csv_path = os.path.join(reg_source_dir, "REG2018_2021.csv")
print(f"\nProcessing large historical file: {csv_path}...")

# Columns mapping for CSV
csv_cols_to_use = [
    'PŮV', 'Kategorie', 'VIN', 'TP', 'Nové/ojeté', 'DatREG CR', 'DatREG svet', 
    'Celkhm', 'Vlastník', 'Leasing', 'IČO provoz', 'IČO vlastník', 'ZTP', 
    'Okres reg', 'ORP', 'Barva', 'Doplbarva', 'Přestavba', 'Značka', 'Model', 'Model2'
]

# Read CSV in chunks
chunk_idx = 0
csv_file_obj = open(csv_path, 'r', encoding='cp1250', errors='ignore')
for chunk in pd.read_csv(csv_file_obj, sep=';', usecols=list(range(1, 22)), chunksize=100000, low_memory=False):
    chunk_idx += 1
    total_raw_rows += len(chunk)
    chunk.columns = csv_cols_to_use
    
    # Keep only Category L
    chunk['Kategorie'] = chunk['Kategorie'].astype(str).str.strip().str.upper()
    df_l = chunk[chunk['Kategorie'].str.startswith('L')].copy()
    
    # Process each row (including L6/L7 quadricycles and ORVs, classifying them into specific segments)
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
        reg_date, reg_month = parse_date_dt(row['DatREG CR'])
        first_reg_date, _ = parse_date_dt(row['DatREG svet'])
        
        # Swap check if dates are swapped (veteran first reg swapped with CZ reg)
        if reg_date and first_reg_date:
            if reg_date.year < 2018 and first_reg_date.year >= 2018:
                reg_date, first_reg_date = first_reg_date, reg_date
                
        # If reg_date is still before 2018, fallback to 2018 (start of CSV database)
        if reg_date and reg_date.year < 2018:
            reg_date = pd.Timestamp(year=2018, month=1, day=1)
            reg_month = 1
        
        reg_month_val = int(reg_month) if reg_month else None
        reg_year = int(reg_date.year) if reg_date else None
        
        new_used_val = str(row['Nové/ojeté']).strip().upper() if not pd.isna(row['Nové/ojeté']) else None
        if new_used_val == 'N':
            first_reg_date = reg_date
        elif not first_reg_date:
            first_reg_date = reg_date
            
        # Parse Regions
        raw_region = get_region(row['Okres reg'])
        kraj_clean = raw_region.strip()
        if kraj_clean == "Hlavní město Praha": kraj_clean = "Praha"
        if kraj_clean.endswith(" kraj"): kraj_clean = kraj_clean[:-5].strip()
        if kraj_clean.startswith("Kraj "): kraj_clean = kraj_clean[5:].strip()
        region_en = region_en_mapping.get(kraj_clean, 'Unknown')
        
        # Clean numeric
        mass = clean_numeric(row['Celkhm'])
        mass_group = int(round(mass / 100.0) * 100.0) if not pd.isna(mass) else None
        puv_clean = clean_int(row['PŮV'])
        owner_clean = clean_int(row['Vlastník'])
        color_clean = clean_int(row['Barva'])
        
        # Parse motorcycle properties
        fuel, displacement, disp_group, segment, seats, launch_year = parse_moto_attributes(row)
        
        # Override Segment for quadricycles / ORVs / utility trikes
        cat_upper = str(row['Kategorie']).strip().upper() if not pd.isna(row['Kategorie']) else ""
        brand_upper = str(row['Značka']).strip().upper() if not pd.isna(row['Značka']) else "NONE"
        model_upper = str(row['Model']).strip().upper() if not pd.isna(row['Model']) else ""
        
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
        
        ingested_records.append({
            'Registration ID': puv_clean,
            'First Registration Date': first_reg_date,
            'CZ Registration Date': reg_date,
            'CZ Registration Month': reg_month_val,
            'CZ Registration Year': reg_year,
            'VIN': row['VIN'],
            'VIN Prefix': vin[:8] if len(vin) >= 8 else vin,
            'Category': row['Kategorie'],
            'New/Used': new_used_val,
            'Total Mass': mass,
            'Total Mass Group': mass_group,
            'Owner Type': owner_clean,
            'Leasing': row['Leasing'],
            'District': row['Okres reg'],
            'Kraj': kraj_clean,
            'Region': region_en,
            'Municipality': row['ORP'],
            'Color code': color_clean,
            'Color': map_color_code(color_clean),
            'Brand': brand,
            'Model': row['Model'],
            'Displacement': displacement,
            'Displacement Group': disp_group,
            'Fuel': fuel,
            'Segment': segment,
            'Total seats': seats,
            'Launch Year': launch_year
        })
        
    print(f"  Finished chunk {chunk_idx}. Total category L motorcycles so far: {len(ingested_records)}")

csv_file_obj.close()

# 3b. Process monthly Excel files (2022 to June 2026)
excel_cols = [
    'PŮV', 'Kategorie', 'VIN', 'TP', 'Nové/ojeté', 'DatREG CR', 'DatREG svet', 
    'Celkhm', 'Vlastník', 'Leasing', 'IČO provoz', 'IČO vlastník', 'ZTP', 
    'Okres reg', 'ORP', 'Barva', 'Doplbarva', 'Přestavba', 'Značka', 'Model', 'Model2'
]

# Find all Excel files
excel_files = sorted([f for f in os.listdir(reg_source_dir) if f.startswith('REG') and f.endswith('.xlsx')])
print(f"\nFound {len(excel_files)} monthly Excel files to process.")

for excel_file in excel_files:
    file_path = os.path.join(reg_source_dir, excel_file)
    print(f"Processing Excel: {excel_file}...")
    
    # Extract file year and month from filename (e.g. REG2201.xlsx -> 2022, 1)
    file_yy = int(excel_file[3:5]) + 2000
    file_mm = int(excel_file[5:7])
    
    # Read without header
    df_raw = pd.read_excel(file_path, header=None)
    df_raw = df_raw.iloc[:, :21]
    df_raw.columns = excel_cols
    total_raw_rows += len(df_raw)
    
    df_raw['Kategorie'] = df_raw['Kategorie'].astype(str).str.strip().str.upper()
    df_l = df_raw[df_raw['Kategorie'].str.startswith('L')].copy()
    
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
        reg_date, reg_month = parse_date_dt(row['DatREG CR'])
        first_reg_date, _ = parse_date_dt(row['DatREG svet'])
        
        # Swap check if dates are swapped
        if reg_date and first_reg_date:
            if reg_date.year < 2018 and first_reg_date.year >= 2018:
                reg_date, first_reg_date = first_reg_date, reg_date
                
        # If reg_date is still before 2018, fallback to the monthly Excel file date
        if not reg_date or reg_date.year < 2018:
            reg_date = pd.Timestamp(year=file_yy, month=file_mm, day=1)
            reg_month = file_mm
            
        reg_month_val = int(reg_month) if reg_month else None
        reg_year = int(reg_date.year) if reg_date else None
        
        new_used_val = str(row['Nové/ojeté']).strip().upper() if not pd.isna(row['Nové/ojeté']) else None
        if new_used_val == 'N':
            first_reg_date = reg_date
        elif not first_reg_date:
            first_reg_date = reg_date
            
        # Parse Regions
        raw_region = get_region(row['Okres reg'])
        kraj_clean = raw_region.strip()
        if kraj_clean == "Hlavní město Praha": kraj_clean = "Praha"
        if kraj_clean.endswith(" kraj"): kraj_clean = kraj_clean[:-5].strip()
        if kraj_clean.startswith("Kraj "): kraj_clean = kraj_clean[5:].strip()
        region_en = region_en_mapping.get(kraj_clean, 'Unknown')
        
        # Clean numeric
        mass = clean_numeric(row['Celkhm'])
        mass_group = int(round(mass / 100.0) * 100.0) if not pd.isna(mass) else None
        puv_clean = clean_int(row['PŮV'])
        owner_clean = clean_int(row['Vlastník'])
        color_clean = clean_int(row['Barva'])
        
        # Parse motorcycle properties
        fuel, displacement, disp_group, segment, seats, launch_year = parse_moto_attributes(row)
        
        # Override Segment for quadricycles / ORVs / utility trikes
        cat_upper = str(row['Kategorie']).strip().upper() if not pd.isna(row['Kategorie']) else ""
        brand_upper = str(row['Značka']).strip().upper() if not pd.isna(row['Značka']) else "NONE"
        model_upper = str(row['Model']).strip().upper() if not pd.isna(row['Model']) else ""
        
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
        
        ingested_records.append({
            'Registration ID': puv_clean,
            'First Registration Date': first_reg_date,
            'CZ Registration Date': reg_date,
            'CZ Registration Month': reg_month_val,
            'CZ Registration Year': reg_year,
            'VIN': row['VIN'],
            'VIN Prefix': vin[:8] if len(vin) >= 8 else vin,
            'Category': row['Kategorie'],
            'New/Used': new_used_val,
            'Total Mass': mass,
            'Total Mass Group': mass_group,
            'Owner Type': owner_clean,
            'Leasing': row['Leasing'],
            'District': row['Okres reg'],
            'Kraj': kraj_clean,
            'Region': region_en,
            'Municipality': row['ORP'],
            'Color code': color_clean,
            'Color': map_color_code(color_clean),
            'Brand': brand,
            'Model': row['Model'],
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
print(f"  Successfully Ingested Motorcycles: {len(ingested_records)}")

# 4. Save and export
if len(ingested_records) > 0:
    df_merged = pd.DataFrame(ingested_records)
    
    # Sort
    df_merged = df_merged.sort_values(by=['CZ Registration Date', 'Brand']).reset_index(drop=True)
    
    # Save to Excel
    print(f"\nSaving merged database to Excel: {existing_xlsx}")
    df_merged.to_excel(existing_xlsx, index=False)
    print("Saved Excel successfully!")
    
    # Save to CSV (excluding Description/etc. columns to save size if needed)
    print(f"Saving merged database to CSV: {existing_csv}")
    df_merged.to_csv(existing_csv, sep=';', index=False, date_format='%d.%m.%Y', encoding='utf-8')
    print("Saved CSV successfully!")
    
else:
    print("\nNo records were ingested. Finished.")

print("\n=== DATA INGESTION COMPLETED SUCCESSFULLY ===")
