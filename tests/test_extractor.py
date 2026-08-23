import pytest
from sec_keyterms.extractor import SEC424B2Extractor
from sec_keyterms.validators import SecurityReferenceSchema

MOCK_INDIAN_NCD_HTML = """
<!DOCTYPE html>
<html>
<head><title>HDFC BANK LIMITED - NCD TRANCHE I</title></head>
<body>
    <h1>Information Memorandum - Debt Issuance</h1>
    <table>
        <tr><td>Issuer:</td><td>HDFC Bank Limited</td></tr>
        <tr><td>ISIN:</td><td>INE040A08435</td></tr>
        <tr><td>BSE Scrip Code:</td><td>500180</td></tr>
        <tr><td>Coupon Rate:</td><td>7.70%</td></tr>
        <tr><td>Redemption Date:</td><td>2031-03-25</td></tr>
        <tr><td>Credit Rating:</td><td>CRISIL AAA</td></tr>
    </table>
</body>
</html>
"""


def test_indian_debt_extraction_and_validation():
    extractor = SEC424B2Extractor()
    raw_data = extractor.extract_from_html(MOCK_INDIAN_NCD_HTML)

    # Validate extracted data through Pydantic
    validated = SecurityReferenceSchema(**raw_data)

    assert validated.isin == "INE040A08435"
    assert validated.bse_scrip_code == "500180"
    assert validated.coupon_rate == 7.70
    assert validated.credit_rating == "CRISIL AAA"
    assert validated.currency == "INR"


def test_invalid_indian_isin_rejection():
    invalid_data = {
        "isin": "US0378331005",  # US ISIN
        "issuer_name": "Invalid Entity",
        "coupon_rate": 8.0,
        "maturity_date": "2029-01-01"
    }
    with pytest.raises(ValueError, match="Invalid ISIN prefix"):
        SecurityReferenceSchema(**invalid_data)