import pandas as pd
import json

# Load your CSV
csv_file = "//Users/lavyaagrawal/Downloads/ Questions.csv"   
df = pd.read_csv(csv_file, encoding="latin1")

converted = {}

for _, row in df.iterrows():
    cat = str(row["Category"]).strip() if not pd.isna(row["Category"]) else "General"
    q = str(row["Question"]).strip()
    ans = str(row["Answer"]).strip() if not pd.isna(row["Answer"]) else ""
    diff = str(row["Difficulty"]).strip() if not pd.isna(row["Difficulty"]) else "Unknown"

    if cat not in converted:
        converted[cat] = []

    converted[cat].append({
        "q": q,
        "answer": ans,
        "difficulty": diff
    })

# Save JSON
out_file = "questions_dataset.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(converted, f, indent=2, ensure_ascii=False)

print(f"✅ Converted {len(df)} rows into {len(converted)} categories → {out_file}")
