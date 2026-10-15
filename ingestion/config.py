"""Ingestion configuration: source files, expected columns, and paths.

The expected columns mirror the Olist Brazilian E-commerce dataset exactly,
including its original spelling quirks (e.g. ``product_name_lenght``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

RAW_SCHEMA = "raw"


@dataclass(frozen=True)
class TableSpec:
    """Describes one source CSV and the raw table it loads into."""

    name: str  # table name in the raw schema
    filename: str  # CSV file name inside the raw data directory
    columns: tuple[str, ...]  # columns that MUST exist in the CSV header


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        name="customers",
        filename="olist_customers_dataset.csv",
        columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
    TableSpec(
        name="geolocation",
        filename="olist_geolocation_dataset.csv",
        columns=(
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
    ),
    TableSpec(
        name="order_items",
        filename="olist_order_items_dataset.csv",
        columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    TableSpec(
        name="order_payments",
        filename="olist_order_payments_dataset.csv",
        columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    TableSpec(
        name="order_reviews",
        filename="olist_order_reviews_dataset.csv",
        columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
    TableSpec(
        name="orders",
        filename="olist_orders_dataset.csv",
        columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    TableSpec(
        name="products",
        filename="olist_products_dataset.csv",
        columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    TableSpec(
        name="sellers",
        filename="olist_sellers_dataset.csv",
        columns=(
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ),
    ),
    TableSpec(
        name="category_translation",
        filename="product_category_name_translation.csv",
        columns=(
            "product_category_name",
            "product_category_name_english",
        ),
    ),
)


def _resolve(path_str: str) -> Path:
    """Resolve a path from the environment; relative paths are anchored to the project root."""
    path = Path(path_str)
    return path if path.is_absolute() else PROJECT_ROOT / path


def get_raw_dir() -> Path:
    """Directory containing the source CSV files."""
    return _resolve(os.getenv("RAW_DATA_DIR", "data/raw"))


def get_warehouse_path() -> Path:
    """Path of the DuckDB warehouse file."""
    return _resolve(os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb"))
