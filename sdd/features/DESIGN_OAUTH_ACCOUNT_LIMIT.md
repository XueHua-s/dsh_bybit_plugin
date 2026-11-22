# Design: Bybit AI-account OAuth guard

## Scope

Harden the existing environment-scoped PKCE OAuth module without adding an
exchange execution path. The module owns the Bybit AI-sub-account creation
precondition and the authorize URL contract; callers continue to choose an
account explicitly.

## Decisions

- `BybitOAuth.createAccount()` first lists AI sub-accounts and refuses creation
  when the provider's documented limit of five is reached.
- The authorize URL remains a Testnet/Mainnet endpoint selected by the explicit
  environment, with `client_id=ai-agent`, `scope=ai-account`, loopback
  `redirect_uri`, PKCE S256, and state.
- Credentials and tokens remain private files; no values are returned or
  printed. This slice does not grant trading authority.

## Invariants

- No create request is sent after five accounts are observed.
- Mainnet and Testnet paths remain isolated.
- Tests use temporary files and mocked fetch only.

## Verification

`pnpm --filter @bybit-quant/dsh-plugin verify`
