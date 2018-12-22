# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta, Pool

__all__ = ['Address']


class Address(metaclass=PoolMeta):
    __name__ = 'party.address'

    @staticmethod
    def default_country():
        country = Pool().get('country.country').search([
            ('code', '=', 'AR'),
            ])
        if country:
            return country[0].id
