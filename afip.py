# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import os
import logging

from trytond.model import ModelView, ModelSQL, fields

logger = logging.getLogger(__name__)

__all__ = ['AFIPCountry']


def get_module_install_dir():
    basepath = __file__
    return os.path.dirname(os.path.abspath(basepath))


def get_cache_dir():
    return os.path.join(get_module_install_dir(), 'cache')


class AFIPCountry(ModelSQL, ModelView):
    'AFIP Country'
    __name__ = 'afip.country'

    code = fields.Char('Code')
    name = fields.Char('Name')
