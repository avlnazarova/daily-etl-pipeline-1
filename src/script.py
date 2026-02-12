import argparse
import logging
import os
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from detect_cms import detect_cms
from dotenv import load_dotenv

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",  # timestamp + level + message
    handlers=[
        logging.FileHandler("pipeline.log"),  # store logs in a file
        logging.StreamHandler()  # also print to console
    ]
)

load_dotenv()

# -------------------------
# GET NEW CSV FILE
# -------------------------

# today's date
parser = argparse.ArgumentParser(
    description="Run daily ETL pipeline with a specified date"
)

parser.add_argument(
    "--date",          # argument name, e.g., --date 2025-09-02
    type=str,          
    required=True,
    help="Date of the CSV to process in YYYY-MM-DD format"
)

args = parser.parse_args()

try:
    date = datetime.strptime(args.date, "%Y-%m-%d").date()
except ValueError:
    raise ValueError("Invalid date format. Use YYYY-MM-DD.")

# get new csv file with today's date
df = pd.read_csv(f'data/input/customers-{date}.csv')
logging.info(f"File customers-{date}.csv is fetched. Number of rows: {len(df)}.")

# preprocessing csv file
df =  df.drop_duplicates()
logging.info(f"File customers-{date}.csv is processed. Number of rows: {len(df)}.")

# -------------------------
# ENRICH WITH CRM DATA USING API
# -------------------------

# get api token
api_key = os.getenv("HSAutomationToken")

headers = {
    "Authorization": f"Bearer {api_key}"
}

base_url = "https://api.hubapi.com/crm/v3/objects/contacts"

# define parameters for request
params = {
    "limit": 100,
    "archived": "false",
    "properties": "email, firstname, lastname, hs_lead_status"
}

all_contacts = []
after = None

# get all contacts from CRM
while True:
    if after:
        params["after"] = after
    else:
        params.pop("after", None)

    response = requests.get(base_url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    # collect results
    all_contacts.extend(data.get("results", []))

    # check for next page
    paging = data.get("paging")
    if paging and "next" in paging:
        after = paging["next"]["after"]
    else:
        break

# normalize to DataFrame
crm_contacts = pd.json_normalize(all_contacts)

logging.info(f"All contacts are retrieved from CRM. Number of contacts: {len(crm_contacts)}.")

# join contacts info from crm to the main dataset
df = pd.merge(df, crm_contacts[["properties.email", "properties.hs_lead_status"]], how="left", left_on="Email", right_on="properties.email")

logging.info(f"Dataset is enriched with CRM lead status. Number of rows: {len(df)}.")

# -------------------------
# SCRAPE CMS
# -------------------------

results = [None] * len(df)

# run CMS detection in parallel
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {
        executor.submit(detect_cms, url): idx
        for idx, url in enumerate(df["Website"])
    }

    for future in as_completed(futures):
        idx = futures[future]
        results[idx] = future.result()

df[["cms", "cms_confidence", "cms_evidence"]] = pd.DataFrame(
    results,
    index=df.index
)

logging.info(f"CMS is parsed from the websites. CMS is detected for {(df['cms'] != 'unknown').sum()} out of {len(df)} websites.")

# -------------------------
# UPDATE INPUT FILE
# -------------------------

# read input file
dashboard_input = pd.read_csv(f'data/output/dashboard_input.csv')
logging.info(f"Dashboard input file before: {len(dashboard_input)} rows.")

# concatenate new data to input file
dashboard_input = pd.concat([dashboard_input, df], ignore_index=True)
dashboard_input['cms_evidence'] = dashboard_input['cms_evidence'].apply(str)
dashboard_input = dashboard_input.drop_duplicates()
logging.info(f"Dashboard input file after: {len(dashboard_input)} rows.")

# save updated input file
dashboard_input.to_csv('data/output/dashboard_input.csv', index=False)
logging.info("Dashboard input file updated.")



