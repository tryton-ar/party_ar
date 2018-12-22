# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['AFIPCountry']


class AFIPCountry(ModelSQL, ModelView):
    'AFIP Country'
    __name__ = 'afip.country'

    code = fields.Char('Code')
    name = fields.Char('Name')
