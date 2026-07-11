# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from pyafipws.wsfev1 import WSFEv1
from pyafipws.wsfexv1 import WSFEXv1
from pyafipws.wsaa import WSAA
import hashlib
import time
import os
import sys
import traceback
import logging

from trytond.model import Model, ModelView, ModelSQL, fields
from trytond.i18n import gettext
from .exceptions import PyAfipWsError

logger = logging.getLogger(__name__)


class PyAfipWsMixin:
    """Mixin para trabajar con pyafipws."""
    __slots__ = ()

    @classmethod
    def authenticate(cls, service, crt, key, wsdl=None, proxy=None,
            wrapper=None, cacert=None, cache=None):
        "Método unificado para obtener el ticket de acceso (cacheado)"
        DEFAULT_TTL = 60 * 60 * 5   # five hours

        wsaa = WSAA()
        wsaa.LanzarExcepciones = True
        try:
            # cache default compartido con party_ar (para tests y prod)
            if not cache:
                _dir = os.path.dirname(os.path.abspath(__file__))
                cache = os.path.join(_dir, 'cache')
                os.makedirs(cache, exist_ok=True)

            # creo el nombre para el archivo del TA (según credenciales y ws)
            ta_src = (service + crt + key).encode("utf8")
            fn = os.path.join(cache, "TA-%s.xml" % hashlib.md5(ta_src).hexdigest())

            # leer el ticket de acceso (si fue previamente solicitado)
            if not os.path.exists(fn) or os.path.getsize(fn) == 0 or \
               os.path.getmtime(fn) + (DEFAULT_TTL) < time.time():
                # ticket de acceso (TA) vencido, crear un nuevo req. (TRA)
                logger.debug("Creando TRA...")
                tra = wsaa.CreateTRA(service=service, ttl=DEFAULT_TTL)
                # firmarlo criptográficamente
                logger.debug("Frimando TRA...")
                cms = wsaa.SignTRA(tra, crt, key)
                # concectar con el servicio web:
                logger.debug("Conectando a WSAA...")
                ok = wsaa.Conectar(cache, wsdl, proxy, wrapper, cacert)
                if not ok or wsaa.Excepcion:
                    raise RuntimeError("Fallo la conexión: %s" %
                        wsaa.Excepcion)
                # llamar al método remoto para solicitar el TA
                logger.debug("Llamando WSAA...")
                ta = wsaa.LoginCMS(cms)
                if not ta:
                    raise RuntimeError("Ticket de acceso vacio: %s" %
                        WSAA.Excepcion)
                # grabar el ticket de acceso para poder reutilizarlo luego
                logger.debug("Grabando TA en %s...", fn)
                try:
                    f = open(fn, 'w')
                    f.write(ta)
                    f.close()
                except IOError as e:
                    wsaa.Excepcion = (
                        "Imposible grabar ticket de accesso: %s" % fn)
            else:
                # leer el ticket de acceso del archivo en cache
                logger.debug("Leyendo TA de %s...", fn)
                f = open(fn, 'r')
                ta = f.read()
                f.close()
            # analizar el ticket de acceso y extraer los datos relevantes
            wsaa.AnalizarXml(xml=ta)
            wsaa.Token = wsaa.ObtenerTagXml("token")
            wsaa.Sign = wsaa.ObtenerTagXml("sign")
        except Exception:
            ta = ""
            if wsaa.Excepcion:
                # get the exception already parsed by the helper
                err_msg = wsaa.Excepcion
            else:
                # avoid encoding problem when reporting exceptions to the user:
                err_msg = traceback.format_exception_only(
                    sys.exc_info()[0], sys.exc_info()[1])[0]
            raise PyAfipWsError(gettext('party_ar.msg_pyafipws_error',
                    message=str(err_msg)))
        return ta

    @classmethod
    def connect(cls, ta, wsdl, service, vat_number, cache=None, cacert=True):
        "Método unificado para connectarse a webservices desde pyafipws"
        if service == 'wsfe':
            ws = WSFEv1()
        elif service == 'wsfex':
            ws = WSFEXv1()
        else:
            msg = 'webservice_not_supported',
            raise PyAfipWsError(gettext(
                'party_ar.msg_pyafipws_error', message=msg))

        # cache default compartido con party_ar
        if not cache:
            _dir = os.path.dirname(os.path.abspath(__file__))
            cache = os.path.join(_dir, 'cache')
            os.makedirs(cache, exist_ok=True)

        ws.LanzarExcepciones = True
        ws.SetTicketAcceso(ta)
        ws.Cuit = vat_number
        ws.Conectar(wsdl=wsdl, cache=cache, cacert=True)
        return ws


class AFIPCountry(ModelSQL, ModelView):
    'AFIP Country'
    __name__ = 'afip.country'

    code = fields.Char('Code')
    name = fields.Char('Name')
