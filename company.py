# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
import os

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.exceptions import UserError
from trytond.i18n import gettext
from .afip import PyAfipWsMixin

logger = logging.getLogger(__name__)


class Company(PyAfipWsMixin, metaclass=PoolMeta):
    __name__ = 'company.company'

    pyafipws_certificate = fields.Text('Certificado AFIP WS',
        help='Certificado (.crt) de la empresa para webservices AFIP')
    pyafipws_private_key = fields.Text('Clave Privada AFIP WS',
        help='Clave Privada (.key) de la empresa para webservices AFIP')
    pyafipws_mode_cert = fields.Selection([
        ('', 'n/a'),
        ('homologacion', 'Homologación'),
        ('produccion', 'Producción'),
        ], 'Modo de certificación',
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

    def pyafipws_get_base_url(self):
        if self.pyafipws_mode_cert == 'homologacion':
            base_url = 'https://wswhomo.afip.gov.ar'
        elif self.pyafipws_mode_cert == 'produccion':
            base_url = 'https://servicios1.afip.gov.ar'
        else:
            raise UserError(gettext(
                'party_ar.msg_wrong_pyafipws_mode',
                message=('El modo de certificación no es ni producción, ni '
                    'homologación. Configure su Empresa')))
        return base_url

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

        ta = self.authenticate(service, crt, key, wsdl=WSAA_URL, cache=cache)
        return ta

    def pyafipws_connect(self, ta, service):
        '''
        Connect to webservices
        '''
        base_url = self.pyafipws_get_base_url()
        if service == 'wsfe':
            wsdl = f'{base_url}/wsfev1/service.asmx?WSDL'
        elif service == 'wsfex':
            wsdl = f'{base_url}/wsfexv1/service.asmx?WSDL'
        else:
            logger.critical('AFIP ws is not yet supported! %s', service)
            raise UserError(gettext(
                'party_ar.msg_webservice_not_supported',
                service=service))

        cache = self.get_cache_dir()
        cacert = True
        try:
            ws = self.connect(ta, wsdl, service, self.party.vat_number, cache, cacert)
        except Exception as e:
            msg = ws.Excepcion + ' ' + str(e)
            logger.error('WSAA connecting to afip: %s' % msg)
            raise UserError(gettext(
                'party_ar.msg_wsaa_error', msg=msg))

        return ws
