"""Which XBRL tags hold each financial item, in priority order.

Companies do not all use the same tag for the same line, and a company can
change tag over time (Apple used ``SalesRevenueNet`` until 2017, then
``RevenueFromContractWithCustomerExcludingAssessedTax``). For each item we
list the accepted tags: for every fiscal year, the first tag of the list that
has a value is used. The tag actually used is kept in the output
(``xbrl_tag`` column) so every number can be traced back to the 10-K.

Only tags with the SAME meaning are listed. Tags that look close but measure
something else are left out on purpose, because using them would put a wrong
number in a ratio:

* ``Depreciation`` alone (no amortization) is not D&A.
* ``LongTermDebt`` includes the current portion; we want the noncurrent part.
* ``CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`` includes
  restricted cash.
* Net interest tags (interest expense minus interest income) are not interest
  expense.

If none of the tags has a value, the item is reported as "not available".

``kind`` tells how the value is measured:

* ``FLOW``: over a period (income statement, cash flow statement);
* ``INSTANT``: at a date (balance sheet).
"""

FLOW = "flow"
INSTANT = "instant"

ITEMS = {
    "revenue": {
        "kind": FLOW,
        "tags": [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "SalesRevenueNet",
        ],
    },
    "operating_income": {
        "kind": FLOW,
        "tags": [
            "OperatingIncomeLoss",
        ],
    },
    "depreciation_amortization": {
        "kind": FLOW,
        "tags": [
            "DepreciationDepletionAndAmortization",
            "DepreciationAndAmortization",
            "DepreciationAmortizationAndAccretionNet",
        ],
    },
    "interest_expense": {
        "kind": FLOW,
        "tags": [
            "InterestExpense",
            "InterestExpenseNonoperating",
            "InterestExpenseDebt",
            "InterestAndDebtExpense",
        ],
    },
    "total_assets": {
        "kind": INSTANT,
        "tags": [
            "Assets",
        ],
    },
    "total_liabilities": {
        "kind": INSTANT,
        "tags": [
            "Liabilities",
        ],
    },
    "stockholders_equity": {
        "kind": INSTANT,
        "tags": [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
    },
    "current_assets": {
        "kind": INSTANT,
        "tags": [
            "AssetsCurrent",
        ],
    },
    "current_liabilities": {
        "kind": INSTANT,
        "tags": [
            "LiabilitiesCurrent",
        ],
    },
    "cash": {
        "kind": INSTANT,
        "tags": [
            "CashAndCashEquivalentsAtCarryingValue",
            "Cash",
        ],
    },
    "long_term_debt": {
        "kind": INSTANT,
        "tags": [
            "LongTermDebtNoncurrent",
            "LongTermDebtAndCapitalLeaseObligations",
        ],
    },
    "operating_cash_flow": {
        "kind": FLOW,
        "tags": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],
    },
    "capex": {
        "kind": FLOW,
        "tags": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
    },
}
