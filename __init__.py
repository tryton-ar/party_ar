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
