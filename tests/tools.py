# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.tools import file_open
from trytond.modules.company.tests.tools import get_company
from ..afip import PyAfipWsMixin

__all__ = ['set_afip_certs', 'get_wsfev1', 'get_wsfexv1']


URL_WSAA = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
URL_WSFEX = "https://wswhomo.afip.gov.ar/wsfexv1/service.asmx?WSDL"
URL_WSFE = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"


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


def get_wsfev1(company=None, config=None):
    "Obtiene instancia WSFEv1 autenticada para tests"
    company = set_afip_certs(company, config)
    service = 'wsfe'
    ta = PyAfipWsMixin.authenticate(
        service,
        str(company.pyafipws_certificate),
        str(company.pyafipws_private_key),
        wsdl=URL_WSAA,
    )
    return PyAfipWsMixin.connect(ta, URL_WSFE, service, company.party.vat_number)


def get_wsfexv1(company=None, config=None):
    "Obtiene instancia WSFEXv1 autenticada para tests"
    company = set_afip_certs(company, config)
    service = 'wsfex'
    ta = PyAfipWsMixin.authenticate(
        service,
        str(company.pyafipws_certificate),
        str(company.pyafipws_private_key),
        wsdl=URL_WSAA,
    )
    return PyAfipWsMixin.connect(ta, URL_WSFEX, service, company.party.vat_number)
