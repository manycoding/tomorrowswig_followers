# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['APP_ID', 'APP_SECRET', 'TOKEN', 'USER_ID', 'SHEET', 'SH', 'get_df', 'get_worksheet', 'write_df']

# Cell
import os
from typing import *

import gspread
from gspread.models import *
import pandas as pd
import numpy as np

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
TOKEN = os.environ.get("TOKEN")
USER_ID = os.environ.get("USER_ID")
SHEET = os.environ.get("SHEET", "Followers API")
SH = gspread.service_account(filename="creds.json").open(SHEET)
# SH = gspread.service_account(filename=path.parent/"careful-form-283418-d1afb9670368.json").open("Test of Followers API)


# Cell
def get_df(worksheet: str) -> pd.DataFrame:
    wsh = SH.worksheet(worksheet)
    df = pd.DataFrame(wsh.get_all_records()).replace("", 0)
    index = df.columns[0]
    df.set_index(df[index], inplace=True)
    return df.drop(columns=index)

# Cell
def get_worksheet(name: str) -> Worksheet:
    worksheets = [w.title for w in SH.worksheets()]
    if name in worksheets:
        return SH.worksheet(name)
    else:
        return SH.add_worksheet(name, 1, 1, 4)

# Cell
def write_df(df: pd.DataFrame, worksheet: str, loc: str = "A1"):
    worksheet = get_worksheet(worksheet)
    df.insert(0, df.index.name, df.index)
    df.replace([0, np.inf, np.nan], "", inplace=True)
    worksheet.update(loc, [df.columns.to_list()] + df.values.tolist(), raw=False)