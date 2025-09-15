#!/usr/bin/env python3

import sys
import requests
import base64
import json
from datetime import datetime, UTC
import argparse

API_BASE = "https://services.inteliquent.com/Services/1.0.0"


def get_auth_header(api_key, api_secret):
    token = f"{api_key}:{api_secret}"
    b64_token = base64.b64encode(token.encode()).decode()
    return {"Authorization": f"Basic {b64_token}", "Content-Type": "application/json"}


def fetch_trunk_groups(api_key, api_secret, debug=False):
    trunk_groups = []
    headers = get_auth_header(api_key, api_secret)
    payload = {"privateKey": api_key}
    resp = requests.post(
        f"{API_BASE}/trunkGroupList",
        headers=headers,
        json=payload
    )
    if debug:
        print(f"Request URL: {API_BASE}/trunkGroupList")
        print(f"Request headers: {headers}")
        print(f"Request payload: {payload}")
        print(f"Response: {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
    if resp.status_code != 200:
        print(f"Error fetching trunk group list: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    if data.get("status") != "Success":
        print(f"API error: {data}")
        sys.exit(1)
    trunk_groups.extend(data.get("trunkGroupList", []))
    return trunk_groups


def fetch_trunk_group_detail(api_key, api_secret, trunk_group_name, debug=False):
    headers = get_auth_header(api_key, api_secret)
    payload = {
        "trunkGroupName": trunk_group_name,
        "privateKey": api_key
    }
    resp = requests.post(
        f"{API_BASE}/trunkGroupDetail",
        headers=headers,
        json=payload
    )
    if debug:
        print(f"Request URL: {API_BASE}/trunkGroupDetail")
        print(f"Request headers: {headers}")
        print(f"Request payload: {payload}")
        print(f"Response: {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
    if resp.status_code != 200:
        print(f"Error fetching trunk group detail for {trunk_group_name}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    if data.get("status") != "Success":
        print(f"API error for {trunk_group_name}: {data}")
        return None
    return data.get("trunkGroupDetail")


def fetch_trunk_group_utilization(api_key, api_secret, trunk_group_name, start_date, end_date, debug=False):
    headers = get_auth_header(api_key, api_secret)
    payload = {
        "privateKey": api_key,
        "trunkGroupName": trunk_group_name,
        "startDate": start_date,
        "endDate": end_date
    }
    resp = requests.post(
        f"{API_BASE}/trunkGroupUtilization",
        headers=headers,
        json=payload
    )
    if debug:
        print(f"Request URL: {API_BASE}/trunkGroupUtilization")
        print(f"Request headers: {headers}")
        print(f"Request payload: {payload}")
        print(f"Response: {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
    if resp.status_code != 200:
        print(f"Error fetching trunk group utilization for {trunk_group_name}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    if data.get("status") != "Success":
        print(f"API error for utilization {trunk_group_name}: {data}")
        return None
    util_list = data.get("trunkGroupUtilList", {})
    return util_list.get("trunkGroupUtilItem", [])[-1] if util_list.get("trunkGroupUtilItem") else {}


def main():
    parser = argparse.ArgumentParser(description="Fetch Inteliquent trunk group details and utilization.")
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--account', nargs=3, action='append', metavar=('API_KEY', 'API_SECRET', 'LABEL'), required=True,
                        help='API key, secret, and label triple. Can be specified multiple times.')
    args = parser.parse_args()

    # Use original date format: YYYY-MM-DD
    end_date = datetime.now(UTC).strftime("%Y-%m-%d")
    start_date = end_date  # Only poll for today

    all_results = {}
    for api_key, api_secret, label in args.account:
        if args.debug:
            print(f"\nFetching trunk group list for {label}")
        trunk_groups = fetch_trunk_groups(api_key, api_secret, args.debug)
        if args.debug:
            print(f"Found {len(trunk_groups)} trunk groups for {label}")

        results = {}
        for tg in trunk_groups:
            name = tg.get("trunkGroupName")
            if not name:
                continue
            if args.debug:
                print(f"\nFetching details for trunk group: {name}")
            detail = fetch_trunk_group_detail(api_key, api_secret, name, args.debug)
            utilization = fetch_trunk_group_utilization(api_key, api_secret, name, start_date, end_date, args.debug)
            if detail:
                customer_name = detail.get("customerTrunkGroupName")
                if not customer_name:
                    customer_name = name
                trunk_group_feature = detail.get("trunkGroupFeature", {})
                e911_enabled = trunk_group_feature.get("e911Enabled", "N")
                results[name] = {
                    "activeSessionCount": detail.get("activeSessionCount"),
                    "status": detail.get("status"),
                    "accessType": detail.get("accessType"),
                    "customerTrunkGroupName": customer_name,
                    "e911Enabled": e911_enabled,
                    "utilization": utilization
                }
        all_results[label] = results

    if all_results:
        print("<<<inteliquent_trunk_groups:sep(0)>>>")
        print(json.dumps(all_results, separators=(',', ':')))


if __name__ == "__main__":
    main()
