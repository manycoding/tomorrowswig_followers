# AUTOGENERATED! DO NOT EDIT! File to edit: 02_ads.ipynb (unless otherwise specified).

__all__ = ['AD_ACC_ID', 'account', 'get_dif', 'COLUMNS', 'get_insights', 'get_action', 'get_followers_change',
           'add_country_total', 'add_followers', 'get_countries', 'add_total', 'get_insights_df', 'more_stats',
           'create_insights']

# Cell
from .core import *
from .followers import get_new_followers

# Cell
import os
from typing import *

from datetime import datetime
from functools import partial

import pandas as pd
import numpy as np
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount

AD_ACC_ID = os.environ.get("AD_ACC_ID")

# Cell
FacebookAdsApi.init(APP_ID, APP_SECRET, TOKEN)
account = AdAccount(AD_ACC_ID)

# Cell
def get_dif(df: pd.DataFrame) -> pd.DataFrame:
    change_df = df.diff(axis=1, periods=-1)
    change_df = change_df.fillna(0).astype(int)
    return change_df

# Cell
COLUMNS = ["Ad Name", "Ads Followers Change", "% (Clicks)", "% (Impressions)", "Cost Per Follow",
           "Clicks (All)", "Link Clicks", "CPC (All)" , "CPC (Cost per Link Click)",
           "CTR (All)", "CPM (Cost per 1,000 Impressions)", "Amount Spent (USD)", "Impressions", "Reach", "Post Reactions", "Post Shares",
           "Video Average Play Time", "Video Plays at 50%", "Video Plays at 75%", "Video Plays at 95%"]

# Cell
get_insights = partial(account.get_insights, fields=[
        "ad_id",
        "ad_name",
        "clicks",
        "cpc",
        "ctr",
        "cpm",
        "cost_per_action_type",
        "spend",
        "impressions",
        "reach",
        "actions",
        "video_avg_time_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p95_watched_actions",
    ], params={
        'level': "ad",
        'date_preset': "yesterday",
    })

# Cell
def get_action(cell, name):
    action = [a for a in cell if a["action_type"] == name]
    if action:
        return float(action[0]["value"])
    return 0

# Cell
def get_followers_change(date: datetime) -> pd.DataFrame:
    history_df = get_df("History")
    new_followers = get_dif(history_df)
    followers_date = date.strftime("%b %d %Y")
    new_followers = new_followers.iloc[:,new_followers.columns.str.startswith(followers_date)].replace(0, np.nan)
    new_followers = new_followers.dropna(axis=1, how="all").iloc[:, :1].dropna().astype(int)
    if not new_followers.values.size:
        new_followers["no change"] = 0
    return new_followers

# Cell
def add_country_total(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    dupes = df[df.index.duplicated(False)]
    if not len(dupes):
        return

    to_mean = ["cpc", "cpm", "ctr", "CPC (Cost per Link Click)"]
    to_sum = set(df.columns).difference(set(to_mean + ["ad_name"]))
    total = dupes.iloc[0,:].copy()
    index = dupes.index[0]
    total["ad_name"] = f"{index} total"
    total[to_mean] = dupes[to_mean].apply(np.mean)
    total[to_sum] = dupes[to_sum].astype(int).apply(sum)
    return df.append(total), index

# Cell
def add_followers(df: pd.DataFrame, date: datetime):
    new_followers = get_followers_change(date)
    df["Ads Followers Change"] = new_followers
    df.fillna(0, inplace=True)
    df["% (Clicks)"] = (df["Ads Followers Change"] / df["clicks"])
    df["% (Impressions)"] = (df["Ads Followers Change"] / df["impressions"])
    df["Cost Per Follow"] = (df["spend"] / df["Ads Followers Change"])
    df.replace([np.inf], 0, inplace=True)

# Cell
def get_countries(ids: List[str]) -> List[Dict]:
    countries = []
    for id in ids:
        ad = Ad(id).api_get(fields=["targeting"])
        country = ad["targeting"]["geo_locations"]["countries"][0]
        countries.append({"ad_id": id, "country": country})
    return countries

# Cell
def add_total(df: pd.DataFrame) -> pd.DataFrame:
    to_mean = ["cpc", "cpm", "ctr", "CPC (Cost per Link Click)", "Video Average Play Time"]
    empty = ["Ads Followers Change", "% (Clicks)", "% (Impressions)", "Cost Per Follow", "ad_name"]
    to_sum = df.columns.difference(to_mean + empty)
    total = pd.Series(name="total", index=df.columns, dtype=float)
    total[to_mean] = df[to_mean].apply(np.mean)
    total[to_sum] = df[to_sum].apply(sum)
    df = df.append(total)
    return pd.concat([df.iloc[-1:], df.iloc[:-1]])

# Cell
def get_insights_df(insights: List, date: datetime) -> pd.DataFrame:
    df = pd.DataFrame(insights)
    floats = ["cpc", "cpm", "ctr", "spend"]
    df[floats] = df[floats].astype(float)
    ints = ["clicks", "impressions", "reach"]
    df[ints] = df[ints].astype(int)

    df = df.merge(pd.DataFrame(get_countries(df["ad_id"].values)))
    df.set_index(df["country"], inplace=True)
    df.sort_values("ad_name", inplace=True)

    df["Post Reactions"] = df["actions"].apply(partial(get_action, name="post_reaction"))
    df["Post Shares"] = df["actions"].apply(partial(get_action, name="post"))
    df["Link Clicks"] = df["actions"].apply(partial(get_action, name="link_click"))
    df["CPC (Cost per Link Click)"] = df["cost_per_action_type"].apply(partial(get_action, name="link_click"))
    get_video_action = partial(get_action, name="video_view")
    df["Video Average Play Time"] = df["video_avg_time_watched_actions"].apply(get_video_action)
    df["Video Plays at 50%"] = df["video_p50_watched_actions"].apply(get_video_action)
    df["Video Plays at 75%"] = df["video_p75_watched_actions"].apply(get_video_action)
    df["Video Plays at 95%"] = df["video_p95_watched_actions"].apply(get_video_action)

    df.drop(columns=["actions", "cost_per_action_type", "date_start", "date_stop",
                     "video_avg_time_watched_actions", "ad_id", "country"] +
            [f"video_p{p}_watched_actions" for p in [50,75,95]], inplace=True)

    dupes = add_country_total(df)
    add_followers(df, date)
    df = add_total(df)
    df.rename(columns={"ad_name": "Ad Name", "clicks": "Clicks (All)", "cpc": "CPC (All)",
                       "ctr": "CTR (All)", "cpm": "CPM (Cost per 1,000 Impressions)",
                       "reach": "Reach", "impressions": "Impressions", "spend": "Amount Spent (USD)"}, inplace=True)
    df["% (Impressions)"] = df["% (Impressions)"].round(4)
    df[df.columns.difference(["% (Impressions)"])] = df[df.columns.difference(["% (Impressions)"])].round(2)
    return df[COLUMNS]

# Cell
def more_stats(df: pd.DataFrame, date: datetime) -> pd.DataFrame:
    stats = pd.Series(dtype=float, name="Followers")
    ads_followers_gain = df["Ads Followers Change"].sum()
    followers_gain = get_followers_change(date).sum().item()
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
def create_insights(event: Dict = None, context=None,) -> str:
    insights = get_insights()
    date = datetime.strptime(insights[0]["date_stop"], "%Y-%m-%d")
    worksheet_name = date.strftime("%b %d %Y")
    df = get_insights_df(insights, date)
    stats_df = more_stats(df, date)
    empty = pd.Series(name="", dtype=str)
    df = df.append([empty] * 4)
    write_df(df, worksheet_name)
    stats_df = stats_df.append([empty] * 15)
    write_df(stats_df, worksheet_name, loc=f"B{len(df)}")
    notes_df = pd.DataFrame([["", "CONSIDER:", "", "", "TO DO:"]], index=["PERFORMANCE:"], columns=[""] * 5)
    write_df(notes_df, worksheet_name, loc=f"A{len(stats_df) + len(df) - 14}")

    wsh = get_worksheet(worksheet_name)
    wsh.format(f"C1:F{len(df)-1}", {"textFormat": {
        "foregroundColor": {
            "red": 0.45,
            "green": 0.0,
            "blue": 0.0
        }}},)
    wsh.format(f"D:E", {"numberFormat": {"type": "PERCENT"}},)
    wsh.format(f"F", {"numberFormat": {"type": "CURRENCY"}},)

    unf_cell = wsh.find("Unfollowers")
    wsh.format(f"C{wsh.find('Unfollowers').row}", {"textFormat": {
        "foregroundColor": {
            "red": 0.0,
            "green": 0.0,
            "blue": 1.0
        }}},)
    return f"Created insights in '{worksheet_name}'"