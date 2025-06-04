import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    Credentials = None

CONFIG_FILE = Path('wc_credentials.json')
ORDERS_CSV = Path('orders.csv')
SHEET_ID = '1kJH3Gk9IVJoLp6MqDj7lit_iqsMdYWYvEpsUz4pVDxc'
START_DATE = '2025-01-01T00:00:00'


class WooCommerceClient:
    def __init__(self, base_url: str, consumer_key: str, consumer_secret: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (consumer_key, consumer_secret)

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        url = f"{self.base_url}/wp-json/wc/v3{endpoint}"
        response = requests.get(url, params=params, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def iter_orders(self, after: str) -> List[Dict[str, Any]]:
        page = 1
        orders = []
        while True:
            params = {
                'per_page': 100,
                'page': page,
                'after': after,
            }
            batch = self.get('/orders', params=params)
            if not batch:
                break
            orders.extend(batch)
            page += 1
        return orders

    def get_product_cost(self, product_id: int) -> Optional[float]:
        product = self.get(f'/products/{product_id}')
        for meta in product.get('meta_data', []):
            if meta.get('key') == '_wc_cog_cost':
                try:
                    return float(meta.get('value'))
                except (TypeError, ValueError):
                    return None
        return None


def load_config(path: Path) -> Dict[str, str]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    creds = {
        'base_url': input('WooCommerce base URL: ').strip(),
        'consumer_key': input('Consumer key: ').strip(),
        'consumer_secret': input('Consumer secret: ').strip(),
    }
    with open(path, 'w') as f:
        json.dump(creds, f)
    return creds


def fetch_orders(client: WooCommerceClient) -> List[Dict[str, Any]]:
    orders = client.iter_orders(START_DATE)
    rows = []
    for order in orders:
        order_id = order['id']
        order_date = order['date_created']
        customer_id = order.get('customer_id')
        status = order.get('status')
        shipping = sum(sh.get('total', 0) for sh in order.get('shipping_lines', []))
        tax = sum(t.get('total', 0) for t in order.get('tax_lines', []))
        for item in order.get('line_items', []):
            sku = item.get('sku')
            quantity = int(item.get('quantity', 0))
            total = float(item.get('total', 0))
            product_id = item.get('product_id')
            product_cost = client.get_product_cost(product_id) or 0.0
            line_cogs = product_cost * quantity
            rows.append({
                'order_id': order_id,
                'order_date': order_date,
                'customer_id': customer_id,
                'line_item_sku': sku,
                'line_item_quantity': quantity,
                'line_item_total': total,
                'product_cost': product_cost,
                'line_COGS': line_cogs,
                'order_status': status,
                'shipping_paid': shipping,
                'taxes_paid': tax,
            })
    return rows


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        print('No orders found.')
        return
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f'Wrote {len(rows)} rows to {path}')


def upload_to_sheet(auth_file: str, csv_path: Path) -> None:
    if gspread is None or Credentials is None:
        print('gspread not available. Cannot upload.')
        return
    creds = Credentials.from_service_account_file(auth_file, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    try:
        worksheet = sheet.worksheet('order_data')
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet('order_data', rows='1000', cols='20')
    with open(csv_path, 'r') as f:
        content = f.read().splitlines()
        rows = [line.split(',') for line in content]
    worksheet.update('A1', rows, value_input_option='USER_ENTERED')
    print(f'Uploaded data to Google Sheet {SHEET_ID} worksheet order_data.')


def main():
    parser = argparse.ArgumentParser(description='Fetch WooCommerce orders and optionally upload to Google Sheets.')
    parser.add_argument('--config', type=Path, default=CONFIG_FILE, help='Path to credentials file.')
    parser.add_argument('--auth-file', type=str, help='Google service account JSON file.')
    args = parser.parse_args()

    creds = load_config(args.config)
    client = WooCommerceClient(creds['base_url'], creds['consumer_key'], creds['consumer_secret'])
    rows = fetch_orders(client)
    write_csv(rows, ORDERS_CSV)
    if args.auth_file:
        upload_to_sheet(args.auth_file, ORDERS_CSV)


if __name__ == '__main__':
    main()
