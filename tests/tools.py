# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from proteus import Model

from trytond.tools import file_open
from trytond.modules.company.tests.tools import get_company

__all__ = ['set_afip_certs']


def set_afip_certs(company=None, config=None):
    "Set AFIP certificates"
    if not company:
        company = get_company()
    with file_open('party_ar/tests/gcoop.crt', mode='rb') as fp:
        crt = fp.read()
        company.pyafipws_certificate = crt.decode('utf8')
    with file_open('party_ar/tests/gcoop.key', mode='rb') as fp:
        key = fp.read()
        company.pyafipws_private_key = key.decode('utf8')
    company.pyafipws_mode_cert = 'homologacion'
    company.save()
    return company
