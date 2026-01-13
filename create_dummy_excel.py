import pandas as pd
import os

data = {
    "LinkedIn URL": [
        "https://www.linkedin.com/in/satyanadella",
        "https://www.linkedin.com/in/williamhgates"
    ]
}

df = pd.DataFrame(data)
os.makedirs("Search Snippet", exist_ok=True)
df.to_excel("Search Snippet/leads.xlsx", index=False)
print("Created Search Snippet/leads.xlsx")
