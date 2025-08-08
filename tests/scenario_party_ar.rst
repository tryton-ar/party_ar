=============
AFIP Scenario
=============

Imports::
    >>> import datetime as dt
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.party_ar.tests.tools import set_afip_certs
    >>> from pyafipws.wsaa import WSAA
    >>> today = dt.date.today()

Install party_ar::

    >>> config = activate_modules('party_ar')

Create company::

    >>> currency = get_currency('ARS')
    >>> _ = create_company(currency=currency)
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_vat'
    >>> tax_identifier.code = '30710158254' # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Configure AFIP certificates::

    >>> _ = set_afip_certs(company=company)

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.iva_condition='responsable_inscripto'
    >>> party.vat_number='30710158254'
    >>> party.save()

Get information from Padron::

    >>> party.click('get_afip_data')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    VatNumberNotFound: ...
