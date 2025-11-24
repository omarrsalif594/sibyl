"""
RiverBank Finance - Customer Risk Scoring Module

This module calculates risk scores for customers based on various factors.
All risk assessments must comply with KYC and AML policies.

Policy Reference: KYC-001 (Customer Due Diligence)
Policy Reference: AML-002 (Risk-Based Approach)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class RiskLevel(Enum):
    """Customer risk level classification per policy AML-002."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionType(Enum):
    """Transaction types for risk assessment."""

    DOMESTIC = "domestic"
    INTERNATIONAL = "international"
    CASH = "cash"
    WIRE = "wire"
    ACH = "ach"


@dataclass
class CustomerProfile:
    """Customer profile data for risk assessment."""

    customer_id: str
    account_age_days: int
    occupation: str
    country: str
    expected_monthly_volume: float
    actual_monthly_volume: float
    kyc_verified: bool
    kyc_last_updated: datetime
    pep_status: bool  # Politically Exposed Person
    sanctions_check: bool
    adverse_media_hits: int


@dataclass
class TransactionHistory:
    """Transaction history for pattern analysis."""

    total_transactions: int
    total_volume: float
    international_count: int
    cash_transactions: int
    high_risk_countries: list[str]
    suspicious_flags: int
    average_transaction: float
    max_transaction: float


def calculate_kyc_risk_score(profile: CustomerProfile) -> dict[str, any]:
    """
    Calculate KYC-related risk score according to policy KYC-001.

    Policy KYC-001 requires:
    - KYC verification within last 12 months
    - PEP screening
    - Sanctions list checking
    - Enhanced due diligence for high-risk customers

    Args:
        profile: Customer profile data

    Returns:
        Dictionary with KYC risk score and factors
    """
    risk_score = 0
    risk_factors = []

    # Policy KYC-001: KYC verification recency
    if not profile.kyc_verified:
        risk_score += 40
        risk_factors.append("KYC not verified")
    else:
        days_since_kyc = (datetime.now() - profile.kyc_last_updated).days
        if days_since_kyc > 365:  # noqa: PLR2004
            risk_score += 30
            risk_factors.append(f"KYC outdated ({days_since_kyc} days)")
        elif days_since_kyc > 180:  # noqa: PLR2004
            risk_score += 15
            risk_factors.append(f"KYC aging ({days_since_kyc} days)")

    # Policy KYC-001: PEP status increases risk
    if profile.pep_status:
        risk_score += 25
        risk_factors.append("Politically Exposed Person (PEP)")

    # Policy KYC-001: Sanctions check
    if not profile.sanctions_check:
        risk_score += 50  # Critical - must be checked
        risk_factors.append("Sanctions screening not completed")

    # Policy KYC-001: Adverse media
    if profile.adverse_media_hits > 0:
        risk_score += min(profile.adverse_media_hits * 10, 30)
        risk_factors.append(f"Adverse media hits: {profile.adverse_media_hits}")

    # Policy KYC-001: High-risk jurisdictions
    high_risk_countries = ["XX", "YY", "ZZ"]  # Placeholder
    if profile.country in high_risk_countries:
        risk_score += 20
        risk_factors.append(f"High-risk jurisdiction: {profile.country}")

    return {
        "kyc_risk_score": min(risk_score, 100),
        "risk_factors": risk_factors,
        "policy_reference": "KYC-001",
    }


def calculate_transaction_risk_score(
    profile: CustomerProfile, history: TransactionHistory
) -> dict[str, any]:
    """
    Calculate transaction pattern risk score according to policy AML-002.

    **BUG**: This implementation has an error in volume variance calculation!
    The expected vs actual volume comparison uses wrong threshold.

    Args:
        profile: Customer profile
        history: Transaction history

    Returns:
        Dictionary with transaction risk score and factors
    """
    risk_score = 0
    risk_factors = []

    # Policy AML-002: Transaction volume variance
    expected = profile.expected_monthly_volume
    actual = profile.actual_monthly_volume

    if expected > 0:
        variance = abs(actual - expected) / expected

        # BUG: Policy AML-002 specifies 50% variance threshold
        # This code uses 30%, which is TOO STRICT and will flag normal customers
        if variance > 0.30:  # WRONG: Should be 0.50 per policy  # noqa: PLR2004
            risk_score += 25
            risk_factors.append(
                f"Volume variance: {variance:.1%} "
                f"(expected: ${expected:.0f}, actual: ${actual:.0f})"
            )

    # Policy AML-002: International transaction ratio
    if history.total_transactions > 0:
        intl_ratio = history.international_count / history.total_transactions
        if intl_ratio > 0.5:  # noqa: PLR2004
            risk_score += 20
            risk_factors.append(f"High international ratio: {intl_ratio:.1%}")

    # Policy AML-002: Cash transaction frequency
    if history.total_transactions > 0:
        cash_ratio = history.cash_transactions / history.total_transactions
        if cash_ratio > 0.3:  # noqa: PLR2004
            risk_score += 15
            risk_factors.append(f"High cash transaction ratio: {cash_ratio:.1%}")

    # Policy AML-002: High-risk country transactions
    if len(history.high_risk_countries) > 0:
        risk_score += len(history.high_risk_countries) * 10
        risk_factors.append(
            f"Transactions with high-risk countries: {', '.join(history.high_risk_countries)}"
        )

    # Policy AML-002: Previous suspicious activity
    if history.suspicious_flags > 0:
        risk_score += min(history.suspicious_flags * 15, 40)
        risk_factors.append(f"Previous suspicious activity flags: {history.suspicious_flags}")

    # Policy AML-002: Transaction size anomalies
    if history.average_transaction > 0:
        size_ratio = history.max_transaction / history.average_transaction
        if size_ratio > 10:  # noqa: PLR2004
            risk_score += 20
            risk_factors.append(f"Large transaction size variance: {size_ratio:.1f}x average")

    return {
        "transaction_risk_score": min(risk_score, 100),
        "risk_factors": risk_factors,
        "policy_reference": "AML-002",
    }


def calculate_behavioral_risk_score(profile: CustomerProfile) -> dict[str, any]:
    """
    Calculate behavioral risk score.

    **ISSUE**: This function lacks clear policy references!
    Behavioral risk factors should be defined in a policy document.

    Args:
        profile: Customer profile

    Returns:
        Dictionary with behavioral risk score
    """
    risk_score = 0
    risk_factors = []

    # No clear policy reference for these thresholds!

    # New account risk
    if profile.account_age_days < 90:  # noqa: PLR2004
        risk_score += 25
        risk_factors.append(f"New account ({profile.account_age_days} days)")
    elif profile.account_age_days < 180:  # noqa: PLR2004
        risk_score += 10
        risk_factors.append(f"Recent account ({profile.account_age_days} days)")

    # Occupation-based risk (where is this defined?)
    high_risk_occupations = ["cash_business", "money_services", "gambling"]
    if profile.occupation.lower() in high_risk_occupations:
        risk_score += 20
        risk_factors.append(f"High-risk occupation: {profile.occupation}")

    return {
        "behavioral_risk_score": min(risk_score, 100),
        "risk_factors": risk_factors,
        "policy_reference": "UNDEFINED",  # No policy reference!
    }


def calculate_composite_risk_score(
    profile: CustomerProfile, history: TransactionHistory, weights: dict[str, float] | None = None
) -> dict[str, any]:
    """
    Calculate composite risk score combining all risk factors.

    Policy Reference: AML-002 (Risk-Based Approach)

    Default weights:
    - KYC Risk: 40%
    - Transaction Risk: 40%
    - Behavioral Risk: 20%

    Args:
        profile: Customer profile
        history: Transaction history
        weights: Optional custom weights for risk components

    Returns:
        Comprehensive risk assessment
    """
    if weights is None:
        weights = {"kyc": 0.40, "transaction": 0.40, "behavioral": 0.20}

    # Calculate component scores
    kyc_result = calculate_kyc_risk_score(profile)
    transaction_result = calculate_transaction_risk_score(profile, history)
    behavioral_result = calculate_behavioral_risk_score(profile)

    # Calculate weighted composite score
    composite_score = (
        kyc_result["kyc_risk_score"] * weights["kyc"]
        + transaction_result["transaction_risk_score"] * weights["transaction"]
        + behavioral_result["behavioral_risk_score"] * weights["behavioral"]
    )

    # Determine risk level per policy AML-002
    if composite_score >= 75:  # noqa: PLR2004
        risk_level = RiskLevel.CRITICAL
    elif composite_score >= 50:  # noqa: PLR2004
        risk_level = RiskLevel.HIGH
    elif composite_score >= 25:  # noqa: PLR2004
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    # Combine all risk factors
    all_risk_factors = (
        kyc_result["risk_factors"]
        + transaction_result["risk_factors"]
        + behavioral_result["risk_factors"]
    )

    return {
        "customer_id": profile.customer_id,
        "composite_risk_score": round(composite_score, 2),
        "risk_level": risk_level.value,
        "component_scores": {
            "kyc": kyc_result["kyc_risk_score"],
            "transaction": transaction_result["transaction_risk_score"],
            "behavioral": behavioral_result["behavioral_risk_score"],
        },
        "risk_factors": all_risk_factors,
        "weights_applied": weights,
        "timestamp": datetime.now().isoformat(),
    }


def get_enhanced_due_diligence_required(risk_assessment: dict[str, any]) -> bool:
    """
    Determine if Enhanced Due Diligence (EDD) is required per policy KYC-001.

    Policy KYC-001 requires EDD for:
    - High or Critical risk customers
    - PEP customers
    - Customers from high-risk jurisdictions

    Args:
        risk_assessment: Risk assessment result

    Returns:
        True if EDD is required
    """
    risk_level = risk_assessment.get("risk_level")

    # Policy KYC-001: EDD required for high/critical risk
    if risk_level in ["high", "critical"]:
        return True

    # Check for specific risk factors requiring EDD
    risk_factors = risk_assessment.get("risk_factors", [])

    edd_triggers = [
        "Politically Exposed Person",
        "High-risk jurisdiction",
        "Sanctions screening not completed",
    ]

    for factor in risk_factors:
        for trigger in edd_triggers:
            if trigger in factor:
                return True

    return False


# Test cases
if __name__ == "__main__":
    # Test profile
    test_profile = CustomerProfile(
        customer_id="CUST-12345",
        account_age_days=45,
        occupation="software_engineer",
        country="US",
        expected_monthly_volume=5000.0,
        actual_monthly_volume=15000.0,  # 3x variance - should trigger flag
        kyc_verified=True,
        kyc_last_updated=datetime.now() - timedelta(days=30),
        pep_status=False,
        sanctions_check=True,
        adverse_media_hits=0,
    )

    test_history = TransactionHistory(
        total_transactions=50,
        total_volume=15000.0,
        international_count=10,
        cash_transactions=5,
        high_risk_countries=["XX"],
        suspicious_flags=1,
        average_transaction=300.0,
        max_transaction=5000.0,
    )

    # Calculate risk
    risk = calculate_composite_risk_score(test_profile, test_history)

    for _component, _score in risk["component_scores"].items():
        pass

    for _factor in risk["risk_factors"]:
        pass
