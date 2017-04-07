#! -*- coding: utf8 -*-
from trytond.pool import PoolMeta
from trytond.pyson import Id

__all__ = ['Address']

class Address:
    __metaclass__ = PoolMeta
    __name__ = 'party.address'

    @staticmethod
    def default_country():
        return Id('country', 'ar').pyson()
