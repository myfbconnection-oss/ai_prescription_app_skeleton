# delivery.py
from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, conint, confloat

router = APIRouter(prefix="/delivery", tags=["Delivery"])

# ---------- Configuration (tune as needed) ----------
SMALL_ORDER_THRESHOLD: float = 10.0         # surcharge if cart_value < 10
BASE_DISTANCE_METERS: int = 1000            # first 1000 m
BASE_FEE: float = 2.0                        # base fee for first 1 km
ADDITIONAL_BLOCK_METERS: int = 500           # step for extra distance
ADDITIONAL_BLOCK_FEE: float = 1.0            # fee per 500 m block beyond 1 km
ITEM_SURCHARGE_START_AT: int = 5             # surcharge applies from the 5th item (inclusive)
ITEM_SURCHARGE_PER_ITEM: float = 0.50        # surcharge amount per item from 5th onward
FREE_DELIVERY_CART_VALUE: float = 100.0      # free delivery if cart >= 100
MAX_DELIVERY_FEE: float = 15.0               # cap the delivery fee

def money(value: float) -> float:
    """Round monetary values to two decimals (half-even)."""
    # Slight epsilon to avoid floating rounding artifacts
    return round(value + 1e-12, 2)

# ---------- Models ----------
class DeliveryRequest(BaseModel):
    cart_value: confloat(ge=0) = Field(..., description="Total cart value in currency units (e.g., 12.35)")
    delivery_distance: conint(ge=0) = Field(..., description="Delivery distance in meters (e.g., 1499)")
    item_count: conint(ge=0) = Field(..., description="Total number of items in the cart")
    time: Optional[datetime] = Field(
        None,
        description="ISO8601 datetime (optional, for future rules like rush-hour)"
    )

class DeliveryBreakdown(BaseModel):
    small_order_surcharge: float
    distance_fee: float
    item_surcharge: float
    capped: bool
    free_delivery_applied: bool

class DeliveryResponse(BaseModel):
    total_fee: float = Field(..., description="Final delivery fee after rules, cap, and free delivery check")
    currency: str = Field("EUR", description="Currency code for the amounts returned")
    breakdown: DeliveryBreakdown

# ---------- Core calculation ----------
def calculate_fee(payload: DeliveryRequest) -> DeliveryResponse:
    # Free delivery if cart value hits threshold
    if payload.cart_value >= FREE_DELIVERY_CART_VALUE:
        breakdown = DeliveryBreakdown(
            small_order_surcharge=0.0,
            distance_fee=0.0,
            item_surcharge=0.0,
            capped=False,
            free_delivery_applied=True,
        )
        return DeliveryResponse(total_fee=0.0, currency="EUR", breakdown=breakdown)

    # Small-order surcharge
    small_order_surcharge = 0.0
    if payload.cart_value < SMALL_ORDER_THRESHOLD:
        small_order_surcharge = SMALL_ORDER_THRESHOLD - payload.cart_value

    # Distance fee
    distance_fee = BASE_FEE
    if payload.delivery_distance > BASE_DISTANCE_METERS:
        extra_meters = payload.delivery_distance - BASE_DISTANCE_METERS
        extra_blocks = ceil(extra_meters / ADDITIONAL_BLOCK_METERS)
        distance_fee += extra_blocks * ADDITIONAL_BLOCK_FEE

    # Item surcharge (from 5th item inclusive)
    # If item_count >= 5, surcharge applies to items: 5, 6, ..., item_count
    item_surcharge_items = max(0, payload.item_count - (ITEM_SURCHARGE_START_AT - 1))
    item_surcharge = item_surcharge_items * ITEM_SURCHARGE_PER_ITEM

    # Sum & cap
    raw_total = small_order_surcharge + distance_fee + item_surcharge
    free_delivery_applied = False
    capped = False

    total_fee = raw_total
    if total_fee > MAX_DELIVERY_FEE:
        total_fee = MAX_DELIVERY_FEE
        capped = True

    # Round all monetary values
    breakdown = DeliveryBreakdown(
        small_order_surcharge=money(small_order_surcharge),
        distance_fee=money(distance_fee),
        item_surcharge=money(item_surcharge),
        capped=capped,
        free_delivery_applied=free_delivery_applied,
    )
    return DeliveryResponse(total_fee=money(total_fee), currency="EUR", breakdown=breakdown)

# ---------- Route ----------
@router.post("/calculate", response_model=DeliveryResponse, summary="Calculate delivery fee")
def calculate_delivery(payload: DeliveryRequest) -> DeliveryResponse:
    """
    Calculate the delivery fee based on:
      - Small-order surcharge if `cart_value < 10`.
      - Base distance fee for first `1000 m` (2.0).
      - +1.0 for each additional `500 m` block beyond the first 1 km (ceil).
      - +0.50 per item from the 5th item inclusive.
      - Free delivery if `cart_value >= 100`.
      - Fee cap at `15.0`.

    Returns a detailed breakdown and the final total fee.
    """
    try:
        return calculate_fee(payload)
    except Exception as exc:
        # In case of an unexpected internal error; helps Swagger show a clear message.
        raise HTTPException(status_code=500, detail=f"Delivery fee calculation failed: {exc}")
