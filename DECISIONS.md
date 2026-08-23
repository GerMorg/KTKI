# Decisions (append-only)

## 2026-08-23 D001
Version 0.1 startet read-only. Realhandel ist nicht nur per UI, sondern serverseitig hart gesperrt.

## 2026-08-23 D002
SQLite speichert lokale Zustaende; Geldwerte bleiben als Dezimalstrings erhalten und werden nie binaer gerundet.

## 2026-08-23 D003
Die GUI nutzt keine externen CDNs, damit sie im lokalen HA-Ingress verlaesslich funktioniert.
