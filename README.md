# ecommdashboard

This project provides a script to download WooCommerce orders for Naturesseed starting on **January 1, 2025**. The orders are written to `orders.csv` and can optionally be uploaded to a Google Sheet for analysis.

## Setup

1. Clone the repository and navigate into it.
2. *(Optional)* create a Python virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the script:
   ```bash
   python fetch_orders.py
   ```
   On first run you will be prompted for your WooCommerce base URL and API credentials. These are stored in `wc_credentials.json`. Use `--config FILE` to change the path.
5. To upload the results to Google Sheets, supply a service account JSON file:
   ```bash
   python fetch_orders.py --auth-file your-service-account.json
   ```
   The data is uploaded to the `order_data` worksheet of the sheet at:
   https://docs.google.com/spreadsheets/d/1kJH3Gk9IVJoLp6MqDj7lit_iqsMdYWYvEpsUz4pVDxc

After running, `orders.csv` will contain:
`order_id`, `order_date`, `customer_id`, `line_item_sku`, `line_item_quantity`, `line_item_total`, `product_cost`, `line_COGS`, `order_status`, `shipping_paid`, and `taxes_paid`.
