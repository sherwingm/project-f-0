"""Index-options paper trading and measurement (S3), kept apart from S1 F&O (server/paper.py) and S2.

ledger.py: positions, fills, observations and the bid-based peak; pods.py: the registered index pods (all off);
runner.py: one tick of signal -> entry -> observe -> exit -> after-exit; report.py: per-pod research numbers.
Nothing here places a real order, and nothing turns a pod on by itself.
"""
