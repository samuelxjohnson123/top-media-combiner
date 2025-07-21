import streamlit as st
import pandas as pd
from io import BytesIO

st.title("📊 Top Media Combiner")

st.markdown("""
Upload your daily **Sprinklr** and **Cision** files. This app will:

✅ Combine & align columns  
✅ Mark duplicates (only later ones) with `R` in `?`  
✅ Map `Outlet Group` & `Outlet` from master list  
✅ Flag `ExUS Author` in a new column  
✅ Add blank columns for manual entry  
""")

sprinklr_file = st.file_uploader("Upload Sprinklr file (.xlsx)", type="xlsx")
cision_file = st.file_uploader("Upload Cision file (.csv)", type="csv")

if sprinklr_file and cision_file:
    sprinklr = pd.read_excel(sprinklr_file)
    cision = pd.read_csv(cision_file)
    master_xl = pd.ExcelFile("2025_Master Outlet List.xlsx")

    detailed_list = master_xl.parse("Detailed List for Msmt")
    journalist_check = master_xl.parse("Journalist Check")

    # Standardize Cision columns to match template
    cision = cision.rename(columns={
        "Date": "CreatedTime",
        "Media Type": "Source",
        "Media Outlet": "Publication Name",
        "Title": "Media Title",
        "Link": "Permalink",
        "Author": "Journalist",
        "Sentiment": "Sentiment"
    })

    # Align Sprinklr columns to match template names if needed
    sprinklr = sprinklr.rename(columns={
        "Resolved_URL": "Permalink"
    })

    combined = pd.concat([sprinklr, cision], ignore_index=True)

    # Blank manual columns
    combined['?'] = ""
    combined['Campaign'] = ""
    combined['Phase'] = ""
    combined['Products'] = ""
    combined['PreOrder'] = ""
    combined['Outlet Group'] = ""
    combined['Outlet'] = ""
    combined['ExUS Author'] = ""

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

    # Reorder columns as per final template
    final_cols = [
        'CreatedTime', 'Source', 'Publication Name', 'Outlet Group', 'Outlet',
        'Media Title', 'Permalink', '?', 'Campaign', 'Phase', 'Products', 'PreOrder',
        'Journalist', 'Sentiment', 'Country', 'Total News Media Potential Reach',
        'Web shares overall', 'EMV', 'ExUS Author'
    ]

    # Fill in missing columns if any
    for col in final_cols:
        if col not in combined.columns:
            combined[col] = ""

    combined = combined[final_cols]

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
