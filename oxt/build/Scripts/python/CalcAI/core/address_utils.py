"""Hücre adresi işleme yardımcı fonksiyonları."""

import re


def column_to_index(col_str: str) -> int:
    """
    Sütun harfini 0 tabanlı indekse dönüştürür.

    Args:
        col_str: Sütun harfi (ör. "A", "AB").

    Returns:
        0 tabanlı sütun indeksi.
    """
    result = 0
    for char in col_str.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1


def index_to_column(index: int) -> str:
    """
    0 tabanlı sütun indeksini harf notasyonuna dönüştürür.

    Args:
        index: 0 tabanlı sütun indeksi.

    Returns:
        Sütun harfi (ör. "A", "AB").
    """
    result = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord('A') + remainder) + result
    return result


def parse_address(address: str) -> tuple[int, int]:
    """
    Hücre adresini sütun ve satır indekslerine dönüştürür.

    Args:
        address: Hücre adresi (ör. "A1", "AB10").

    Returns:
        (sütun_indeksi, satır_indeksi) tuple (0 tabanlı).

    Raises:
        ValueError: Geçersiz hücre adresi.
    """
    address = address.strip().upper()
    match = re.match(r'^([A-Z]+)(\d+)$', address)
    if not match:
        raise ValueError(f"Geçersiz hücre adresi: '{address}'")

    col_str = match.group(1)
    row_num = int(match.group(2))

    col_index = column_to_index(col_str)
    row_index = row_num - 1

    return col_index, row_index


def parse_range_string(range_str: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Hücre aralığı dizesini sütun/satır indekslerine dönüştürür.

    Args:
        range_str: "A1:D10" veya "A1" formatında aralık dizesi.

    Returns:
        ((başlangıç_sütun, başlangıç_satır), (bitiş_sütun, bitiş_satır)) tuple.
        Tek hücre için her iki tuple aynıdır.

    Raises:
        ValueError: Geçersiz aralık formatı.
    """
    range_str = range_str.strip().upper()

    pattern = r'^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$'
    match = re.match(pattern, range_str)
    if not match:
        raise ValueError(f"Geçersiz hücre aralığı formatı: '{range_str}'")

    start_col = column_to_index(match.group(1))
    start_row = int(match.group(2)) - 1

    if match.group(3) is not None:
        end_col = column_to_index(match.group(3))
        end_row = int(match.group(4)) - 1
    else:
        end_col = start_col
        end_row = start_row

    return (start_col, start_row), (end_col, end_row)


def format_address(col: int, row: int) -> str:
    """
    Sütun ve satır indekslerinden hücre adresi oluşturur.

    Args:
        col: 0 tabanlı sütun indeksi.
        row: 0 tabanlı satır indeksi.

    Returns:
        Hücre adresi (ör. "A1", "AB10").
    """
    return f"{index_to_column(col)}{row + 1}"
