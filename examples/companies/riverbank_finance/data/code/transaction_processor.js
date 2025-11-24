/**
 * RiverBank Finance - Transaction Processing Module
 *
 * This module processes and validates financial transactions.
 * All transactions must comply with transaction_limits.md and aml_policy.md
 *
 * Policy Reference: TXN-001 (Transaction Limits)
 * Policy Reference: AML-001 (Anti-Money Laundering Checks)
 */

const DAILY_LIMIT = 10000;  // Policy TXN-001: $10,000 daily limit
const SINGLE_TX_LIMIT = 5000;  // Policy TXN-001: $5,000 per transaction
const VELOCITY_THRESHOLD = 5;  // Policy AML-001: Max 5 transactions per hour

/**
 * Validate a transaction against business rules and compliance policies.
 *
 * @param {Object} transaction - Transaction details
 * @param {string} transaction.id - Transaction ID
 * @param {string} transaction.customerId - Customer ID
 * @param {number} transaction.amount - Transaction amount
 * @param {string} transaction.type - Transaction type (debit, credit, transfer)
 * @param {string} transaction.counterparty - Counterparty ID
 * @param {Date} transaction.timestamp - Transaction timestamp
 * @returns {Object} Validation result
 */
function validateTransaction(transaction) {
    const errors = [];
    const warnings = [];

    // Policy TXN-001: Check single transaction limit
    if (transaction.amount > SINGLE_TX_LIMIT) {
        errors.push({
            code: "TXN_LIMIT_EXCEEDED",
            policy: "TXN-001",
            message: `Transaction amount $${transaction.amount} exceeds single transaction limit of $${SINGLE_TX_LIMIT}`
        });
    }

    // Policy TXN-001: Check for negative amounts
    if (transaction.amount < 0) {
        errors.push({
            code: "INVALID_AMOUNT",
            policy: "TXN-001",
            message: "Transaction amount cannot be negative"
        });
    }

    // Policy AML-001: Flag large round numbers (structuring indicator)
    if (transaction.amount >= 9000 && transaction.amount % 1000 === 0) {
        warnings.push({
            code: "SUSPICIOUS_ROUND_AMOUNT",
            policy: "AML-001",
            message: "Large round number transaction may indicate structuring"
        });
    }

    // BUG: Missing check for required fields!
    // Policy TXN-001 requires validation of customerId, but this is not checked

    return {
        valid: errors.length === 0,
        errors: errors,
        warnings: warnings,
        transactionId: transaction.id
    };
}

/**
 * Check daily transaction velocity for AML compliance.
 *
 * **BUG**: This function does NOT properly implement AML-001 velocity checks!
 * It only counts transactions but doesn't check time windows correctly.
 *
 * @param {string} customerId - Customer ID
 * @param {Array} recentTransactions - Recent transactions for this customer
 * @returns {Object} Velocity check result
 */
function checkTransactionVelocity(customerId, recentTransactions) {
    // BUG: This only counts transactions, doesn't check hourly windows!
    // Policy AML-001 requires checking transactions per HOUR, not just total count

    const txCount = recentTransactions.length;
    const totalAmount = recentTransactions.reduce((sum, tx) => sum + tx.amount, 0);

    // WRONG: Should check rolling hourly windows
    const velocityRisk = txCount > VELOCITY_THRESHOLD ? "HIGH" : "LOW";

    // Also missing: Check for rapid-fire transactions (< 1 min apart)

    return {
        customerId: customerId,
        transactionCount: txCount,
        totalAmount: totalAmount,
        riskLevel: velocityRisk,
        // BUG: Should include hourly breakdown
        notes: velocityRisk === "HIGH" ? "Customer exceeds velocity threshold" : "Normal velocity"
    };
}

/**
 * Detect potentially suspicious transaction patterns.
 *
 * Policy Reference: AML-001 (Pattern Detection)
 *
 * @param {Array} transactions - Array of transactions to analyze
 * @returns {Array} Suspicious patterns detected
 */
function detectSuspiciousPatterns(transactions) {
    const patterns = [];

    // Pattern 1: Structuring (multiple transactions just below reporting threshold)
    const structuringTxs = transactions.filter(tx =>
        tx.amount >= 8000 && tx.amount < 10000
    );

    if (structuringTxs.length >= 3) {
        patterns.push({
            type: "POTENTIAL_STRUCTURING",
            policy: "AML-001",
            severity: "HIGH",
            description: `${structuringTxs.length} transactions between $8k-$10k detected`,
            transactionIds: structuringTxs.map(tx => tx.id)
        });
    }

    // Pattern 2: Circular transactions
    const counterparties = {};
    transactions.forEach(tx => {
        const key = `${tx.customerId}-${tx.counterparty}`;
        counterparties[key] = (counterparties[key] || 0) + 1;
    });

    for (const [pair, count] of Object.entries(counterparties)) {
        if (count >= 5) {
            patterns.push({
                type: "HIGH_FREQUENCY_COUNTERPARTY",
                policy: "AML-001",
                severity: "MEDIUM",
                description: `${count} transactions between same parties`,
                counterpartyPair: pair
            });
        }
    }

    // Pattern 3: Rapid escalation in transaction amounts
    if (transactions.length >= 5) {
        const amounts = transactions.map(tx => tx.amount).sort((a, b) => a - b);
        const ratio = amounts[amounts.length - 1] / amounts[0];

        if (ratio > 10) {
            patterns.push({
                type: "AMOUNT_ESCALATION",
                policy: "AML-001",
                severity: "MEDIUM",
                description: `Transaction amounts escalated by ${ratio.toFixed(1)}x`,
                minAmount: amounts[0],
                maxAmount: amounts[amounts.length - 1]
            });
        }
    }

    return patterns;
}

/**
 * Calculate risk score for a transaction.
 *
 * **POTENTIAL ISSUE**: Risk scoring logic not documented in any policy!
 * No clear policy reference for risk score thresholds.
 *
 * @param {Object} transaction - Transaction to score
 * @param {Object} customerProfile - Customer profile data
 * @returns {number} Risk score (0-100)
 */
function calculateRiskScore(transaction, customerProfile) {
    let score = 0;

    // Amount-based risk (no policy reference)
    if (transaction.amount > 5000) score += 30;
    else if (transaction.amount > 2000) score += 15;
    else if (transaction.amount > 1000) score += 5;

    // Customer history (no policy reference)
    if (customerProfile.accountAge < 90) score += 20;  // New account
    if (customerProfile.previousSuspiciousActivity) score += 40;

    // Transaction type (no policy reference)
    if (transaction.type === 'international') score += 15;
    if (transaction.type === 'cash_withdrawal') score += 10;

    // Velocity (no policy reference)
    if (customerProfile.transactionsToday > 10) score += 25;

    return Math.min(score, 100);  // Cap at 100
}

/**
 * Process a batch of transactions with compliance checks.
 *
 * @param {Array} transactions - Array of transactions to process
 * @returns {Object} Processing results
 */
function processBatch(transactions) {
    const results = {
        processed: 0,
        approved: 0,
        rejected: 0,
        flaggedForReview: 0,
        suspiciousPatterns: []
    };

    // Validate each transaction
    transactions.forEach(tx => {
        const validation = validateTransaction(tx);
        results.processed++;

        if (!validation.valid) {
            results.rejected++;
            tx.status = 'REJECTED';
            tx.rejectionReasons = validation.errors;
        } else if (validation.warnings.length > 0) {
            results.flaggedForReview++;
            tx.status = 'REVIEW';
            tx.warnings = validation.warnings;
        } else {
            results.approved++;
            tx.status = 'APPROVED';
        }
    });

    // Detect patterns across batch
    results.suspiciousPatterns = detectSuspiciousPatterns(
        transactions.filter(tx => tx.status === 'APPROVED')
    );

    return results;
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateTransaction,
        checkTransactionVelocity,
        detectSuspiciousPatterns,
        calculateRiskScore,
        processBatch,
        DAILY_LIMIT,
        SINGLE_TX_LIMIT,
        VELOCITY_THRESHOLD
    };
}

// Test cases
if (require.main === module) {
    console.log("Transaction Processor Test Cases");
    console.log("=".repeat(50));

    const testTx = {
        id: "TXN-001",
        customerId: "CUST-123",
        amount: 3000,
        type: "transfer",
        counterparty: "CUST-456",
        timestamp: new Date()
    };

    const result = validateTransaction(testTx);
    console.log("Validation result:", JSON.stringify(result, null, 2));

    // Test suspicious pattern detection
    const testTransactions = [
        { id: "TX1", customerId: "C1", counterparty: "C2", amount: 9000 },
        { id: "TX2", customerId: "C1", counterparty: "C2", amount: 9500 },
        { id: "TX3", customerId: "C1", counterparty: "C2", amount: 9800 }
    ];

    const patterns = detectSuspiciousPatterns(testTransactions);
    console.log("\nSuspicious patterns:", JSON.stringify(patterns, null, 2));
}
