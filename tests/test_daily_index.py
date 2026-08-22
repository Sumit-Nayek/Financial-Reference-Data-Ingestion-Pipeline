# tests/test_daily_index.py
from datetime import date
from unittest.mock import MagicMock
import pytest
from sec_keyterms.daily_index import SECDailyIndex

MOCK_INDEX_CONTENT = """Description:           Master Index of EDGAR Dissemination Feed
Last Data Received:    January 15, 2026
Comments:              webmaster@sec.gov

CIK|Company Name|Form Type|Date Filed|File Name
--------------------------------------------------------------------------------
0001018724|AMAZON COM INC|10-K|20260115|edgar/data/1018724/000101872426000001/amzn-20260115.htm
0000072971|WELLS FARGO & COMPANY/MN|424B2|20260115|edgar/data/72971/000007297126000012/wfc-424b2.htm
0001961726|JPMORGAN CHASE & CO|424B2|20260115|edgar/data/1961726/000196172626000030/jpm-424b2.htm
"""


def test_build_index_url():
    indexer = SECDailyIndex(client=MagicMock())
    test_date = date(2026, 4, 15)  # Q2
    expected_url = "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR2/master.20260415.idx"
    assert indexer.build_index_url(test_date) == expected_url


def test_fetch_and_filter():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_INDEX_CONTENT
    mock_client.get.return_value = mock_response

    indexer = SECDailyIndex(client=mock_client)
    df = indexer.fetch_and_filter(date(2026, 1, 15), form_types=["424B2"])

    assert len(df) == 2
    assert list(df["form_type"].unique()) == ["424B2"]
    assert "WELLS FARGO & COMPANY/MN" in df["company_name"].values
    assert df.iloc[0]["file_url"] == "https://www.sec.gov/Archives/edgar/data/72971/000007297126000012/wfc-424b2.htm"