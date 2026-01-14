import pandas as pd
import os

# Create 51 dummy profiles
urls = [
    "https://www.linkedin.com/in/satyanadella",
    "https://www.linkedin.com/in/williamhgates",
    "https://www.linkedin.com/in/jeffweiner",
    "https://www.linkedin.com/in/reidhoffman",
    "https://www.linkedin.com/in/sundarpichai"
] * 11

df = pd.DataFrame({"LinkedIn URL": urls[:51]})
df.to_excel("Search Snippet/test_founder_v2.xlsx", index=False)
print("Created Search Snippet/test_founder_v2.xlsx")