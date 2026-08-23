# Issues — append-only

## 2026-08-23 I001
Assetcodes und EUR-Bewertung noch offen.

## 2026-08-23 I002 — gelöst in 0.1.0-dev.2
Tabs führten wegen fehlendem Ingress-Präfix zu 404; Dashboard-Link verließ die App. Gelöst durch X-Ingress-Path-Middleware und konsequentes `url_for`.
