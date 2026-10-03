# Grokking Lab MVP v0.1 — RU/EN localization gate

## Required behavior

- The web UI must support **English and Russian** from the first external test.
- Show an explicit `EN / RU` language switch in the header.
- On first visit, use browser language as the default (`ru*` -> Russian; otherwise English).
- Persist the explicit user choice in `localStorage`.
- Switching language must not reload or reset an active audit result.
- All user-facing static text, loading states, error wrappers, verdict explanations, buttons, empty states, safety notes and pipeline labels must be localized.
- Dynamic audit check labels should use a localization dictionary when a known check ID exists and fall back to the raw machine ID for unknown checks.

## Machine-readable fields that must stay stable

Do **not** translate or mutate values in API responses or evidence packages:

- verdict codes: `VERIFIED`, `FAILED`, `INCOMPLETE`
- check status codes: `PASS`, `FAIL`, `INCOMPLETE`
- experiment IDs
- adapter IDs
- hashes
- filenames / paths
- JSON field names

The UI may display a localized human-readable label alongside the stable machine code.

Recommended Russian display labels:

- `VERIFIED` -> `ПОДТВЕРЖДЕНО`
- `FAILED` -> `НЕ ПРОЙДЕНО`
- `INCOMPLETE` -> `НЕДОСТАТОЧНО ДАННЫХ`
- `PASS` -> `ПРОЙДЕНО`
- `FAIL` -> `ОШИБКА`

## Acceptance criteria

1. A Russian-speaking tester can complete the full upload -> audit -> download flow without reading English explanatory copy.
2. An English-speaking tester sees the current English UX unchanged in meaning.
3. Switching RU/EN after an audit preserves the result and only changes presentation text.
4. Downloaded evidence packages remain byte/semantic-compatible with the deterministic audit core and contain unchanged machine-readable codes.
