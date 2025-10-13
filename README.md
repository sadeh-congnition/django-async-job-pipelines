# djjp

The simplest job queue ever with no extra dependencies.

## Benchmark

Setup: Mac mini 2025, M4, 24 GB, Python 3.13.5

Task: sleep between 0.01 to 0.1 seconds.

## Creating/Consuming Jobs One by One

| No. of Jobs | Creation | Consumption | No. Threads | No. asyncio Tasks | DB Engine |
| ----------- | -------- | ----------- | ----------- | ----------------- | ------ |
| 100 | < 1s | 6s | 1 | - | Sqlite3 |
| 1,000 | < 1s | < 1s | 1 | - | Sqlite3 |
| 10,000 | 2s | 64s | 1 | - | Sqlite3 |
| 100 | < 1s | 3s | 5 | - | Sqlite3 |
| 1,000 | < 1s | 19s | 10 | - | Sqlite3 |
| 1,000 | < 1s | 7s | 20 | - | Sqlite3 |
| 1,000 | < 1s | 4s | 50 | - | Sqlite3 |
| 10,000 | 2s | 10s | 10 | - | Sqlite3 |
| 100,000 | 20s | 2 | 10 | - | Sqlite3 |
| 10,000 | 2s | 10s | 10 | - | Sqlite3 |
| 100,000 | 20s | 2 | 10 | - | Sqlite3 |
