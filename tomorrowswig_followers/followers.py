# AUTOGENERATED! DO NOT EDIT! File to edit: 01_followers.ipynb (unless otherwise specified).

__all__ = ['get_followers', 'get_new_followers', 'get_dif', 'get_followers_change', 'get_ads_status', 'save_ads_status',
           'get_updated_followers', 'add_followers', 'more_stats', 'update_insights', 'save_followers', 'make_change',
           'save_change', 'update']

# Cell
import os
from datetime import datetime, timedelta
from typing import *

import pandas as pd
import numpy as np
from pyfacebook import IgProApi
from pyfacebook.error import *
from .core import *

# Cell
def get_followers() -> Tuple[str, Dict[str, int]]:
    api = IgProApi(
        app_id=APP_ID, app_secret=APP_SECRET, long_term_token=TOKEN, version="5.0"
    )
    try:
        response = api.get_user_insights(
            user_id=USER_ID,
            period="lifetime",
            metrics=["audience_country"],
            return_json=True,
        )[0]["values"][0]
        return response["end_time"].split("T")[0], response["value"]
    except PyFacebookException as e:
        return (e.message, {0: 0})

# Cell
def get_new_followers() -> Tuple[str, Dict[str, int]]:
    api = IgProApi(
        app_id=APP_ID, app_secret=APP_SECRET, long_term_token=TOKEN, version="5.0"
    )
    try:
        response = api.get_user_insights(
                user_id=USER_ID,
                period="day",
                metrics=["follower_count"],
                return_json=True,
            )[0]["values"][0]
        return response["end_time"].split("T")[0], response["value"]
    except PyFacebookException as e:
        return (e.message, 0)

# Cell
def get_dif(df: pd.DataFrame) -> pd.DataFrame:
    change_df = df.diff(axis=1, periods=-1)
    change_df = change_df.fillna(0).astype(int)
    return change_df


def get_followers_change(history_df: pd.DataFrame) -> pd.DataFrame:
    new_followers = get_dif(history_df)
    new_followers = new_followers.iloc[:,[0]].replace(0, np.nan)
    new_followers = new_followers.dropna(axis=1, how="all").iloc[:, :1].dropna().astype(int)
    return new_followers

# Cell
def get_ads_status(date: str):
    if get_df(date).empty:
        return "OFF"
    return "ON"

# Cell
def save_ads_status(history_df: pd.DataFrame):
    worksheet = "Ads Status History"
    ads_status_df = get_df(worksheet)
    date = history_df.columns[0].split("  ")[0]
    ads_status = get_ads_status(date)
    change = get_followers_change(history_df).sum().item()
    last_status = pd.Series([ads_status, change], name="", dtype=str, index=["Ads Status", "Change"])
    last_status.name = date
    write_df(pd.concat([last_status, ads_status_df], axis=1), worksheet)

# Cell
def get_updated_followers(
    df: pd.DataFrame, data: Dict[str, int], end_time: str
) -> pd.DataFrame:
    new_followers = pd.Series(data)
    date = (datetime.strptime(end_time, "%Y-%m-%d") - timedelta(days=1)).strftime(f"%b %d %Y{' '*16}")
    new_followers.name = f"{date} {str(datetime.utcnow()).split('.')[0]}"
    last_entry = df.iloc[:, 0]
    second_last_entry = df.iloc[:, 1]
    if np.array_equal(last_entry[last_entry != 0].values, new_followers.sort_index().values) or np.array_equal(second_last_entry[second_last_entry != 0].values, new_followers.sort_index().values):
        return pd.DataFrame()
    else:
        df = pd.concat([df, new_followers], axis=1)
        df = df[[df.columns[-1]] + df.columns[:-1].tolist()]
        df.index.name = "countries"
        df.sort_index(inplace=True)
        return df.fillna(0).astype(int)

# Cell
def add_followers(df: pd.DataFrame, new_followers: pd.DataFrame):
    df["Ads Followers Change"] = new_followers
    df.fillna(0, inplace=True)
    df["% (Clicks)"] = (df["Ads Followers Change"] / df["Clicks (All)"])
    df["% (Impressions)"] = (df["Ads Followers Change"] / df["Impressions"])
    df["Cost Per Follow"] = (df["Amount Spent (USD)"] / df["Ads Followers Change"])
    df.replace([np.inf], 0, inplace=True)
    df["% (Impressions)"] = df["% (Impressions)"].round(4)
    df[df.columns.difference(["% (Impressions)"])] = df[df.columns.difference(["% (Impressions)"])].round(2)

# Cell
def more_stats(df: pd.DataFrame, followers_change: pd.DataFrame) -> pd.DataFrame:
    stats = pd.Series(dtype=float, name="Followers")
    ads_followers_gain = df["Ads Followers Change"].sum()
    followers_gain = followers_change.sum().item()
    spent = df.loc["total", "Amount Spent (USD)"]
    stats["Ads Followers Change"] = ads_followers_gain
    new_followers = get_new_followers()[1]
    stats["Random Followers"] = new_followers - ads_followers_gain
    stats["New Followers"] = new_followers
    stats["Unfollowers"] = stats["New Followers"] - followers_gain
    stats["Followers Change"] = ads_followers_gain + stats["Random Followers"] - stats["Unfollowers"]

    stats_df = pd.DataFrame(stats)
    stats_df.index.name = "  "
    stats_df["Conversion Rate"] = stats_df["Followers"] / df.loc["total", "Clicks (All)"]
    stats_df[" "] = 0
    stats_df["Cost Per Follower/Increase"] = spent/ stats_df["Followers"]
    stats_df.iloc[1:, 1] = 0
    stats_df.iloc[[1,3,4], 3] = 0
    return stats_df.round(2)

# Cell
def update_insights(history_df: pd.DataFrame, date: str):
    followers_change = get_followers_change(history_df)
    df = get_df(date)
    if df.empty:
        return f"Nothing to update for {date}"
    if "PERFORMANCE:" in df.index:
        df = df.iloc[:df.index.get_loc("PERFORMANCE:") - 9, :]

    add_followers(df, followers_change)
    stats_df = more_stats(df, followers_change)

    empty = pd.Series(name="", dtype=str)
    df = df.append([empty] * 4)
    write_df(df, date)
    write_df(stats_df, date, loc=f"B{len(df)}")
    wsh = get_worksheet(date)
    wsh.format(f"C{wsh.find('Unfollowers').row}", {"textFormat": {
        "foregroundColor": {
            "red": 0.0,
            "green": 0.0,
            "blue": 1.0
        }}},)

# Cell
def save_followers() -> str:
    df = get_df("History")
    end_time, followers = get_followers()
    df = get_updated_followers(df, followers, end_time)
    if df.empty:
        return f"No followers change, end_time '{end_time}'"
    date = df.columns[0].split("  ")[0]
    write_df(df, "History")
    save_ads_status(df)
    update_insights(df, date)
    return f"Wrote followers and insights for '{date}'"

# Cell
def make_change(df: pd.DataFrame) -> pd.DataFrame:
    change_df = df.diff(axis=1, periods=-1)
    change_df = change_df.fillna(0).astype(int)
    zeros_mask  = (change_df != 0).any(axis=0)
    change_df = change_df.loc[:, zeros_mask]
    change_df = change_df.applymap(lambda x: f"+{x}" if x > 0 else x)
    change_df = "(" + change_df.astype(str) + ")" + " " + df.loc[:, zeros_mask].astype(str)
    return change_df.replace(["\(0\) 0", "\(0\) "], "", regex=True)

# Cell
def save_change():
    df = get_df("History")
    change_df = make_change(df)
    write_df(change_df, "Change History")
    ads_status = get_df("Ads Status History")
    write_df(ads_status, "Change History", f"A{len(change_df)+3}", columns=False)

# Cell
def update(event: Dict = None, context=None,):
    get_followers()
    message = save_followers()
    save_change()
    return message