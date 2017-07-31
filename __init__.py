# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .party import *
from .address import *


def register():
    Pool.register(
        AFIPVatCountry,
        Party,
        PartyIdentifier,
        Address,
        GetAFIPDataStart,
        module='party_ar', type_='model')
    Pool.register(
        GetAFIPData,
        module='party_ar', type_='wizard')
