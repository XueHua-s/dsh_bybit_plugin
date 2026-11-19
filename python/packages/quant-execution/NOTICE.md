# License and third-party notice

Original Bybit Quant execution code is MIT licensed (LICENSES/MIT.txt).
`src/quant_execution/paper_sandbox.py` adapts the constructor in NautilusTrader
`nautilus_trader/adapters/sandbox/execution.py`, version 1.231.0, source commit
`27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`:
https://github.com/nautechsystems/nautilus_trader/blob/27a8e54e7ac3c57d6cbf8891f0283dfbaee97317/nautilus_trader/adapters/sandbox/execution.py

Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
The adaptation retains its upstream LGPL-3.0-only license; the exact pinned
upstream license is distributed in LICENSES/LGPL-3.0-only.txt. LGPLv3 incorporates
the GPLv3 base terms, distributed alongside it as LICENSES/GPL-3.0-only.txt.
That file is the exact GNU text retrieved from https://www.gnu.org/licenses/gpl-3.0.txt
on 2026-11-17 (SHA-256
3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986).
Accompanying GPL base terms do not relicense the original MIT files.
The package is a
mixed-license distribution, expressed as `MIT AND LGPL-3.0-only` in metadata.
The Python adapter source is included in both source and wheel distributions.

Modification: initialize the original live client base and exactly one native
SimulatedExchange with `liquidity_consumption=True`; enforce the fixed synthetic
SIM/USDT/NETTING/MARGIN/L2 configuration; retain native Sandbox data/command
methods. This makes finite synthetic L2 depth consumption available where the
pinned upstream Sandbox config omits that parameter. No native binary was modified.
