import streamlit as st
import pandas as pd
from io import BytesIO
import os

st.title("📊 Top Media Combiner")

st.markdown("""
Upload your daily **Sprinklr** and **Cision** files. This app will:

✅ Combine & align columns  
✅ Mark duplicates (only later ones) with `R` in `?`  
✅ Map `Outlet Group` & `Outlet` from master list  
✅ Flag `ExUS Author` in a new column  
✅ Add blank columns for manual entry  
✅ Make URLs clickable in Excel
""")

sprinklr_file = st.file_uploader("Upload Sprinklr file (.xlsx or .csv)", type=["xlsx", "csv"])
cision_file = st.file_uploader("Upload Cision file (.xlsx or .csv)", type=["xlsx", "csv"])

# Check that master list exists
MASTER_FILE = "2025_Master Outlet List.xlsx"
if not os.path.exists(MASTER_FILE):
    st.error(f"Master outlet list file `{MASTER_FILE}` not found in app folder.")
    st.stop()

master_xl = pd.ExcelFile(MASTER_FILE)

if sprinklr_file and cision_file:
    # Read Sprinklr
    if sprinklr_file.name.endswith(".csv"):
        sprinklr = pd.read_csv(sprinklr_file, encoding='utf-8', errors='ignore')
    else:
        sprinklr = pd.read_excel(sprinklr_file)

    # Read Cision
    if cision_file.name.endswith(".csv"):
        cision = pd.read_csv(cision_file, skiprows=3, encoding='utf-8')
    else:
        cision = pd.read_excel(cision_file, skiprows=3)

    # Clean up blanks
    cision.dropna(how='all', inplace=True)

    if sprinklr.empty or cision.empty:
        st.error("One of the uploaded files appears to be empty or malformed.")
        st.stop()

    # Strip column names
    sprinklr.columns = sprinklr.columns.str.strip()
    cision.columns = cision.columns.str.strip()

    # Master sheets
    detailed_list = master_xl.parse("Detailed List for Msmt")
    journalist_check = master_xl.parse("Journalist Check")

    # Rename Sprinklr where needed
    sprinklr = sprinklr.rename(columns={
        "Conversation Stream": "Media Title",
        "Resolved_URL": "Permalink"
    })

    cision = cision.rename(columns={
        "Date": "CreatedTime",
        "Media Type": "Source",
        "Media Outlet": "Publication Name",
        "Title": "Media Title",
        "Link": "Permalink",
        "Author": "Journalist",
        "Sentiment": "Sentiment"
    })

    # Define expected columns
    common_cols = [
        "CreatedTime", "Source", "Publication Name", "Media Title",
        "Permalink", "Journalist", "Sentiment"
    ]

    if not sprinklr.columns.is_unique:
        st.error("Sprinklr file has duplicate columns. Please check and re-upload.")
        st.stop()

    if not cision.columns.is_unique:
        st.error("Cision file has duplicate columns. Please check and re-upload.")
        st.stop()

    sprinklr = sprinklr.reindex(columns=common_cols, fill_value="")
    cision = cision.reindex(columns=common_cols, fill_value="")

    # Combine both datasets
    combined = pd.concat([sprinklr, cision], ignore_index=True)

    # Add blank manual columns
    for col in ['?', 'Campaign', 'Phase', 'Products', 'PreOrder', 'Outlet Group', 'Outlet', 'ExUS Author']:
        combined[col] = ""

    # Map Outlet Group and Outlet
    outlet_map = detailed_list[['Outlet Name', 'Vertical (FOR VLOOKUP)']].dropna()
    combined = combined.merge(outlet_map, how='left', left_on='Publication Name', right_on='Outlet Name')
    combined['Outlet Group'] = combined['Vertical (FOR VLOOKUP)']
    combined['Outlet'] = combined['Outlet Name']
    combined.drop(columns=['Vertical (FOR VLOOKUP)', 'Outlet Name'], inplace=True)

    # Flag ExUS authors
    journalist_check['key'] = journalist_check['Publication'].str.lower() + "|" + journalist_check['Name'].str.lower()
    combined['key'] = combined['Publication Name'].str.lower() + "|" + combined['Journalist'].str.lower()
    exus_keys = set(journalist_check[journalist_check['Geo'].str.upper() == 'EXUS']['key'])
    combined['ExUS Author'] = combined['key'].apply(lambda x: 'Yes' if x in exus_keys else '')
    combined.drop(columns=['key'], inplace=True)

    # Mark duplicates (only later ones)
    combined['Permalink_lower'] = combined['Permalink'].str.lower()
    combined['?'] = combined.duplicated(subset=['Permalink_lower'], keep='first').map({True: 'R', False: ''})
    combined.drop(columns=['Permalink_lower'], inplace=True)

    # Make URLs clickable
    combined['Permalink'] = combined['Permalink'].apply(lambda x: f'=HYPERLINK("{x}", "Link")' if pd.notna(x) and x != "" else "")

    # Reorder columns
    final_cols = [
        'CreatedTime', 'Source', 'Publication Name', 'Outlet Group', 'Outlet',
        'Media Title', 'Permalink', '?', 'Campaign', 'Phase', 'Products', 'PreOrder',
        'Journalist', 'Sentiment', 'Country', 'Total News Media Potential Reach',
        'Web shares overall', 'EMV', 'ExUS Author'
    ]

    for col in final_cols:
        if col not in combined.columns:
            combined[col] = ""

    combined = combined[final_cols]

    st.success("✅ Processing complete! Download your combined file below:")

    out = BytesIO()
    combined.to_excel(out, index=False, engine='openpyxl')
    st.download_button(
        label="📥 Download Combined File",
        data=out.getvalue(),
        file_name="Top_Media_Combined.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Please upload both files to begin.")