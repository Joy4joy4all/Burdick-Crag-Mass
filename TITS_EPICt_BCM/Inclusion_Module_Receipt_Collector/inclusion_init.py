"""
Inclusion_Module_Receipt_Collector
================================================================
Stream 2 of the GIBUSH Intelligence Triad.

FUSION    → External interviews flow IN     (Why build?)
INCLUSION → Deployed observations flow BACK (What do we see?)
IMMULSION → SaaS recipients co-create       (Does this work for you?)

Master Lens Classification:
  ML0 — Operator Ground Truth
  ML1 — Entrepreneurial Lead (EL)
  ML2 — Technical Lead (TL)
  ML3 — Industry Mentor (IM)

Usage:
    from Inclusion_Module_Receipt_Collector.inclusion_receipt import (
        get_inclusion_for_project,
        get_inclusion_summary,
        get_receipt_collector,
    )

The Person is the Highest Responsibility.
In Memory of Kasie Malcolm and Allen Hornberger.
© 2026 Stephen J. Burdick Sr. — All Rights Reserved.
"""

from .inclusion_receipt import (
    InclusionReceiptCollector,
    get_receipt_collector,
    get_inclusion_for_project,
    get_inclusion_summary,
    MASTER_LENS,
)

__all__ = [
    'InclusionReceiptCollector',
    'get_receipt_collector',
    'get_inclusion_for_project',
    'get_inclusion_summary',
    'MASTER_LENS',
]
