import streamlit as st
import pandas as pd
from io import BytesIO
import requests

st.title("📊 Top Media Combiner")

st.markdown("""
Upload your daily **Sprinklr** and **Cision** files. This app will:

✅ Accept `.xlsx` or `.csv` for either file  
✅ Combine & align columns  
✅ Resolve URLs for deduplication  
✅ Mark duplicates (later ones) with `R` in `?`  
✅ Map `Outlet Group` & `Outlet` from master list  
✅ Flag `ExUS Author`  
✅ Add blank columns for manual entry  
✅ Make URLs clickable in Excel  
""")

sprinklr_file = st.file_uploader("Upload Sprinklr file (.xlsx or .csv)", type=["xlsx", "csv"])
cision_file = st.file_uploader("Upload Cision file (.xlsx or .csv)", type=["xlsx", "csv"])

if sprinklr_file and cision_file:
    def load_file(uploaded_file):
        if uploaded_file.name.endswith(".csv"):
            return pd.read_csv(uploaded_file, skiprows=3 if "cision" in uploaded_file.name.lower() else 0)
        else:
            return pd.read_excel(uploaded_file)

    sprinklr = load_file(sprinklr_file)
    cision = load_file(cision_file)
    cision.dropna(how='all', inplace=True)

    master_xl = pd.ExcelFile("2025_Master Outlet List.xlsx")
    detailed_list = master_xl.parse("Detailed List for Msmt")
    journalist_check = master_xl.parse("Journalist Check")

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

    common_cols = [
        "CreatedTime", "Source", "Publication Name", "Media Title",
        "Permalink", "Journalist", "Sentiment"
    ]

    sprinklr = sprinklr[common_cols]
    cision = cision[common_cols]

    combined = pd.concat([sprinklr, cision], ignore_index=True)

    # Resolve URLs
    st.info("🔄 Resolving URLs… this may take some time.")
    resolved_urls = []
    for url in combined['Permalink']:
        try:
            r = requests.head(url, allow_redirects=True, timeout=5)
            resolved_urls.append(r.url)
        except:
            resolved_urls.append(url)
    combined['Resolved_Permalink'] = resolved_urls

    # Deduplicate based on resolved URLs
    combined['?'] = combined.duplicated(subset=['Resolved_Permalink'], keep='first').map({True: 'R', False: ''})

    # Add blank manual columns
    for col in ['Campaign', 'Phase', 'Products', 'PreOrder', 'Outlet Group', 'Outlet', 'ExUS Author']:
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

    # Reorder columns
    final_cols = [
        'CreatedTime', 'Source', 'Publication Name', 'Outlet Group', 'Outlet',
        'Media Title', 'Permalink', 'Resolved_Permalink', '?', 'Campaign', 'Phase', 'Products', 'PreOrder',
        'Journalist', 'Sentiment', 'ExUS Author'
    ]

    for col in final_cols:
        if col not in combined.columns:
            combined[col] = ""

    combined = combined[final_cols]

    # Make URLs clickable
    combined['Permalink'] = combined['Permalink'].apply(lambda x: f'=HYPERLINK("{x}", "Link")')
    combined['Resolved_Permalink'] = combined['Resolved_Permalink'].apply(lambda x: f'=HYPERLINK("{x}", "Resolved")')

    st.success("✅ Processing complete! Download your combined file below:")

    out = BytesIO()
    combined.to_excel(out, index=False)
    st.download_button(
        label="📥 Download Combined File",
        data=out.getvalue(),
        file_name="Top_Media_Combined.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Please upload both files to begin.")