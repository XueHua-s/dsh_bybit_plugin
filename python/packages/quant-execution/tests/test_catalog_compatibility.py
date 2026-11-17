"""Real local native persistence coverage for the explicit fsspec security override."""

from decimal import Decimal as D
from importlib.metadata import version

from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog
from quant_execution import InstrumentSpec, Quote
from quant_execution.fixtures import make_instrument, make_quotes


def test_patched_filesystem_native_catalog_roundtrip(tmp_path):
    assert version("fsspec") == "2026.6.0"
    instrument = make_instrument(
        InstrumentSpec(
            "ETHUSDT",
            "ETH",
            D("0.10"),
            D("0.001"),
            D("0.001"),
            D(100),
            D(5),
        )
    )
    ticks = make_quotes(
        instrument, tuple(Quote(D("2000.00"), D("2000.10"), D("1.000"), (i + 1) * 1_000_000_000) for i in range(3))
    )
    catalog = ParquetDataCatalog(str(tmp_path / "catalog"), fs_protocol="file")
    catalog.write_data([instrument])
    catalog.write_data(ticks)
    restored = catalog.instruments()
    assert len(restored) == 1 and restored[0].id == instrument.id
    loaded = catalog.quote_ticks(instrument_ids=[str(instrument.id)])
    assert len(loaded) == len(ticks)
    for actual, expected in zip(loaded, ticks, strict=True):
        assert actual.instrument_id == expected.instrument_id
        assert actual.ts_event == expected.ts_event
        assert actual.bid_price == expected.bid_price
        assert actual.ask_price == expected.ask_price
        assert actual.bid_size == expected.bid_size
        assert actual.ask_size == expected.ask_size
