"""Shared domain layer for the laboratory accounting bounded context.

The backend is a single DDD bounded context (a modular monolith). This package
hosts cross-aggregate domain primitives — first of all the single Unit of Work
that spans every aggregate, mirroring the staraudio ``identity`` layout.
"""
