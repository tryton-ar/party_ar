=============
AFIP Scenario
=============

Imports::
    >>> import datetime
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.party_ar.tests.tools import set_afip_certs
    >>> from pyafipws.wsaa import WSAA
    >>> today = datetime.date.today()

Install account_invoice::

    >>> config = activate_modules('party_ar')

Create company::

    >>> _ = create_company()
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_cuit'
    >>> tax_identifier.code = '30710158254' # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Configure AFIP certificates::

    >>> _ = set_afip_certs(company=company)
