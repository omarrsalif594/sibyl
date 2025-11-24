"""
RiverBank Finance - Interest Calculation Module

This module calculates interest for various account types.
All calculations must comply with interest_rate_policy.md

Policy Reference: INT-001 (Simple Interest Calculation)
Policy Reference: INT-002 (Compound Interest Requirements)
"""

import math


def calculate_simple_interest(principal: float, rate: float, time_years: float) -> float:
    """
    Calculate simple interest according to policy INT-001.

    Formula: I = P * R * T
    Where:
        P = Principal amount
        R = Annual interest rate (as decimal, e.g., 0.05 for 5%)
        T = Time in years

    Args:
        principal: The principal amount
        rate: Annual interest rate (as decimal)
        time_years: Time period in years

    Returns:
        Interest amount
    """
    # Policy INT-001: Simple interest must use exact formula P * R * T
    return principal * rate * time_years


def calculate_compound_interest(
    principal: float, annual_rate: float, time_years: float, compound_frequency: int = 12
) -> float:
    """
    Calculate compound interest according to policy INT-002.

    **BUG**: This implementation does NOT follow policy INT-002!
    Policy requires: A = P(1 + r/n)^(nt)
    This implementation incorrectly uses simple interest formula for each period.

    Args:
        principal: The principal amount
        annual_rate: Annual interest rate (as decimal)
        time_years: Time period in years
        compound_frequency: Number of times interest compounds per year (default: monthly)

    Returns:
        Total amount including interest
    """
    # BUG: This is INCORRECT! Should use compound interest formula
    # Current implementation just multiplies simple interest by frequency
    # This violates policy INT-002
    period_rate = annual_rate / compound_frequency
    total_periods = compound_frequency * time_years

    # WRONG: This is not how compound interest works!
    interest_per_period = principal * period_rate
    total_interest = interest_per_period * total_periods

    return principal + total_interest


def calculate_savings_account_interest(
    balance: float, days: int, annual_rate: float = 0.02
) -> float:
    """
    Calculate interest for savings accounts.

    Policy Reference: INT-003 (Savings Account Interest)
    According to policy, savings accounts use daily compounding.

    **BUG**: This implementation uses 365 days but should use 360 per policy INT-003!

    Args:
        balance: Account balance
        days: Number of days
        annual_rate: Annual interest rate (default 2%)

    Returns:
        Interest earned
    """
    # BUG: Policy INT-003 specifies 360-day year (banker's year)
    # This uses 365, causing incorrect calculations
    daily_rate = annual_rate / 365  # WRONG: Should be 360

    # Compound daily
    amount = balance * math.pow(1 + daily_rate, days)
    return amount - balance


def calculate_loan_payment(
    principal: float, annual_rate: float, num_payments: int
) -> dict[str, float]:
    """
    Calculate monthly loan payment using amortization formula.

    Policy Reference: INT-004 (Loan Payment Calculation)

    This implementation appears correct.

    Args:
        principal: Loan principal amount
        annual_rate: Annual interest rate (as decimal)
        num_payments: Total number of payments

    Returns:
        Dictionary with payment details
    """
    # Convert annual rate to monthly
    monthly_rate = annual_rate / 12

    # Standard amortization formula
    if monthly_rate == 0:
        payment = principal / num_payments
    else:
        payment = (
            principal
            * (monthly_rate * math.pow(1 + monthly_rate, num_payments))
            / (math.pow(1 + monthly_rate, num_payments) - 1)
        )

    total_paid = payment * num_payments
    total_interest = total_paid - principal

    return {
        "monthly_payment": round(payment, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "principal": principal,
    }


def apply_promotional_rate(base_rate: float, customer_tier: str, relationship_years: int) -> float:
    """
    Apply promotional interest rate adjustments.

    **POTENTIAL ISSUE**: This function lacks policy reference.
    No clear documentation on which policy governs promotional rates.
    Risk of non-compliance or inconsistent application.

    Args:
        base_rate: Base interest rate
        customer_tier: Customer tier (bronze, silver, gold, platinum)
        relationship_years: Years as customer

    Returns:
        Adjusted interest rate
    """
    # No policy reference - potential compliance risk!
    tier_bonuses = {
        "bronze": 0.0,
        "silver": 0.0025,  # +0.25%
        "gold": 0.005,  # +0.5%
        "platinum": 0.01,  # +1%
    }

    loyalty_bonus = min(relationship_years * 0.001, 0.01)  # Max 1%
    tier_bonus = tier_bonuses.get(customer_tier.lower(), 0.0)

    return base_rate + tier_bonus + loyalty_bonus


# Test cases for validation
if __name__ == "__main__":
    # Test simple interest
    simple = calculate_simple_interest(10000, 0.05, 2)

    # Test compound interest (HAS BUG!)
    compound = calculate_compound_interest(10000, 0.05, 2, 12)

    # Test savings (HAS BUG!)
    savings = calculate_savings_account_interest(5000, 365, 0.02)

    # Test loan payment
    loan = calculate_loan_payment(200000, 0.045, 360)

    # Test promotional rate
    promo_rate = apply_promotional_rate(0.02, "gold", 5)
