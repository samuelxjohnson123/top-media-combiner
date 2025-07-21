# Define common columns
common_cols = [
    "CreatedTime", "Source", "Publication Name", "Media Title",
    "Permalink", "Journalist", "Sentiment"
]

# Enforce columns
for col in common_cols:
    if col not in sprinklr.columns:
        sprinklr[col] = ""
    if col not in cision.columns:
        cision[col] = ""

# Only keep common columns in order, and drop duplicates if any
sprinklr = sprinklr[common_cols].loc[:, ~sprinklr.columns.duplicated()]
cision = cision[common_cols].loc[:, ~cision.columns.duplicated()]

# Now safe to concatenate
combined = pd.concat([sprinklr, cision], ignore_index=True)