# AUTOGENERATED! DO NOT EDIT! File to edit: 02_ads.ipynb (unless otherwise specified).

__all__ = ['AD_ACC_ID', 'account', 'get_active_ads', 'COLUMNS', 'get_insights', 'get_action', 'add_country_total',
           'get_delivery', 'get_countries', 'add_total', 'get_insights_df', 'create_insights']

# Cell
from .core import *

# Cell
import os
from typing import *

from datetime import datetime, timedelta
from functools import partial

import pandas as pd
import numpy as np
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adaccount import AdAccount

AD_ACC_ID = os.environ.get("AD_ACC_ID")

# Cell
FacebookAdsApi.init(APP_ID, APP_SECRET, TOKEN)
account = AdAccount(AD_ACC_ID)

# Cell
get_active_ads = account.get_ad_sets(fields=["status", "name"], params = {
  'effective_status': ['ACTIVE'], "is_completed": False,
})

# Cell
COLUMNS = ["Ad Name", "Ads Followers Change", "% (Clicks)", "% (Impressions)", "Cost Per Follow", "Delivery Type",
           "Clicks (All)", "Link Clicks", "CPC (All)" , "CPC (Cost per Link Click)",
           "CTR (All)", "CPM (Cost per 1,000 Impressions)", "Amount Spent (USD)", "Impressions", "Reach", "Post Reactions", "Post Shares",
           "Video Average Play Time", "Video Plays at 50%", "Video Plays at 75%", "Video Plays at 95%"]

# Cell
def get_insights(date: str) -> Dict:
    return account.get_insights(fields=[
        "ad_id",
        "adset_id",
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
        "level": "ad",
        "time_range": {"since": date,
                       "until": date},
    })

# Cell
def get_action(cell, name):
    action = [a for a in cell if a["action_type"] == name]
    if action:
        return float(action[0]["value"])
    return 0

# Cell
def add_country_total(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    dupes = df[df.index.duplicated(False)]
    if not len(dupes):
        return

    to_mean = ["cpc", "cpm", "ctr", "CPC (Cost per Link Click)"]
    to_sum = set(df.columns).difference(set(to_mean + ["ad_name", "Delivery Type"]))
    total = dupes.iloc[0,:].copy()
    index = dupes.index[0]
    total["ad_name"] = f"{index} total"
    total[to_mean] = dupes[to_mean].apply(np.mean)
    total[to_sum] = dupes[to_sum].astype(int).apply(sum)
    return df.append(total), index

# Cell
def get_delivery(ids: List[str]) -> List[Dict]:
    deliveries = []
    for id in ids:
        adset = AdSet(id[0]).api_get(fields=["learning_stage_info", "status"])
        delivery = adset.get("learning_stage_info")
        if delivery:
            delivery = delivery.get("status")
        else:
            delivery = adset.get("status")
        deliveries.append({"ad_id": id[1], "adset_id": id[0], "Delivery Type": delivery})
    return deliveries

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
def get_insights_df(insights: List) -> pd.DataFrame:
    df = pd.DataFrame(insights)
    floats = ["cpc", "cpm", "ctr", "spend"]
    df[floats] = df[floats].astype(float)
    ints = ["clicks", "impressions", "reach"]
    df[ints] = df[ints].astype(int)

    df = df.merge(pd.DataFrame(get_countries(df["ad_id"].values)))
    df = df.merge(pd.DataFrame(get_delivery(df[["adset_id", "ad_id"]].values)))
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
                     "video_avg_time_watched_actions", "ad_id", "adset_id", "country"] +
            [f"video_p{p}_watched_actions" for p in [50,75,95]], inplace=True)
    dupes = add_country_total(df)
    df = add_total(df)
    df.rename(columns={"ad_name": "Ad Name", "clicks": "Clicks (All)", "cpc": "CPC (All)",
                       "ctr": "CTR (All)", "cpm": "CPM (Cost per 1,000 Impressions)",
                       "reach": "Reach", "impressions": "Impressions", "spend": "Amount Spent (USD)"}, inplace=True)
    df["Ads Followers Change"] = 0
    df["% (Clicks)"] = 0
    df["% (Impressions)"] = 0
    df["Cost Per Follow"] = 0
    return df[COLUMNS].round(2)

# Cell
def create_insights(event: Dict = None, context=None,) -> str:
    yesterday = datetime.today() - timedelta(days=1)
    insights = get_insights(yesterday.strftime("%Y-%m-%d"))
    if not insights:
        return f"No insights found for {yesterday.strftime('%Y-%m-%d')}"
    df = get_insights_df(insights)
    df_size = len(df)

    empty = pd.Series(name="", dtype=str)
    df = df.append([empty] * 25)

    worksheet_name = yesterday.strftime("%b %d %Y")
    write_df(df, worksheet_name)
    notes_df = pd.DataFrame([["", "CONSIDER:", "", "", "TO DO:"]], index=["PERFORMANCE:"], columns=[""] * 5)
    write_df(notes_df, worksheet_name, loc=f"A{df_size+10}")

    wsh = get_worksheet(worksheet_name)
    wsh.format(f"C1:F{df_size+1}", {"textFormat": {
        "foregroundColor": {
            "red": 0.45,
            "green": 0.0,
            "blue": 0.0
        }}},)
    wsh.format(f"D:E", {"numberFormat": {"type": "PERCENT"}},)
    wsh.format(f"F", {"numberFormat": {"type": "CURRENCY"}},)
    return f"Created insights in '{worksheet_name}'"