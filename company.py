# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from pyafipws.wsaa import WSAA
from pyafipws.ws_sr_padron import WSSrPadronA5
import logging
import os

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.exceptions import UserError
from trytond.i18n import gettext

logger = logging.getLogger(__name__)


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    pyafipws_certificate = fields.Text('Certificado AFIP WS',
        help='Certificado (.crt) de la empresa para webservices AFIP')
    pyafipws_private_key = fields.Text('Clave Privada AFIP WS',
        help='Clave Privada (.key) de la empresa para webservices AFIP')
    pyafipws_mode_cert = fields.Selection([
        ('', 'n/a'),
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
        ], 'Modo de certificacion',
        help=('El objetivo de Homologación (testing), es facilitar las '
            'pruebas. Los certificados de Homologación y Producción son '
            'distintos.'))

    @staticmethod
    def default_pyafipws_mode_cert():
        return ''

    @classmethod
    def validate(cls, companies):
        super().validate(companies)
        for company in companies:
            company.check_pyafipws_mode_cert()

    def check_pyafipws_mode_cert(self):
        if self.pyafipws_mode_cert == '':
            return

        ta = self.pyafipws_authenticate(service='wsfe')

    @classmethod
    def get_cache_dir(cls):

        def get_module_install_dir():
            basepath = __file__
            return os.path.dirname(os.path.abspath(basepath))

        return os.path.join(get_module_install_dir(), 'cache')

    def pyafipws_authenticate(self, service='wsfe', cache=''):
        'Authenticate against AFIP, returns token, sign, err_msg (dict)'
        pool = Pool()
        crt = str(self.pyafipws_certificate)
        key = str(self.pyafipws_private_key)
        if self.pyafipws_mode_cert == 'homologacion':
            WSAA_URL = 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl'
        elif self.pyafipws_mode_cert == 'produccion':
            WSAA_URL = 'https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl'
        else:
            raise UserError(gettext(
                'party_ar.msg_wrong_pyafipws_mode',
                message=('El modo de certificación no es ni producción, ni '
                    'homologación. Configure su Empresa')))

        if not cache:
            cache = self.get_cache_dir()

        PyAfipWsWrapper = pool.get('afip.wrapper')
        ta = PyAfipWsWrapper.authenticate(service, crt, key, wsdl=WSAA_URL,
                cache=cache)
        return ta
