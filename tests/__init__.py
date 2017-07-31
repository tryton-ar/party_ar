try:
    from trytond.modules.party_ar.tests.tests import suite
except ImportError:
    from .tests import suite

__all__ = ['suite']
