import sys
sys.path.insert(0,'kraken_trader/app')
from display_format import display_number,display_tree
from scanner import MarketScanner

def test_display_number_compacts_common_values():
    assert display_number(62.123456789)=='62,12'
    assert display_number(0.123456789)=='0,1235'
    assert display_number(0.050001)=='0,050001'

def test_display_tree_formats_nested_numeric_values():
    value=display_tree({'a':[62.123456,{'b':'0.123456789'}]})
    assert str(value['a'][0])=='62,12'
    assert str(value['a'][1]['b'])=='0,123456789'

def test_scanner_handles_list_ticker_without_get_error():
    assert MarketScanner._ticker_dict([{'b':['1.0'],'a':['1.1']}])['b'][0]=='1.0'
    assert MarketScanner._ticker_dict([])=={}

def test_scanner_match_rejects_non_dict_payload():
    assert MarketScanner.match([{'b':['1']}],'BTC/EUR') is None
