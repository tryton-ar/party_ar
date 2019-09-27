# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from pyafipws.ws_sr_padron import WSSrPadronA5
import stdnum.ar.cuit as cuit
import stdnum.exceptions
from actividades import CODES

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pyson import Bool, Eval, Equal, Not, And, In
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import cursor_dict
from trytond import backend
import logging
logger = logging.getLogger(__name__)

__all__ = ['AFIPVatCountry', 'Party', 'PartyIdentifier', 'GetAFIPData',
    'GetAFIPDataStart']

TIPO_DOCUMENTO = [
    ('0', u'CI Policía Federal'),
    ('1', u'CI Buenos Aires'),
    ('2', u'CI Catamarca'),
    ('3', u'CI Córdoba'),
    ('4', u'CI Corrientes'),
    ('5', u'CI Entre Ríos'),
    ('6', u'CI Jujuy'),
    ('7', u'CI Mendoza'),
    ('8', u'CI La Rioja'),
    ('9', u'CI Salta'),
    ('10', u'CI San Juan'),
    ('11', u'CI San Luis'),
    ('12', u'CI Santa Fe'),
    ('13', u'CI Santiago del Estero'),
    ('14', u'CI Tucumán'),
    ('16', u'CI Chaco'),
    ('17', u'CI Chubut'),
    ('18', u'CI Formosa'),
    ('19', u'CI Misiones'),
    ('20', u'CI Neuquén'),
    ('21', u'CI La Pampa'),
    ('22', u'CI Río Negro'),
    ('23', u'CI Santa Cruz'),
    ('24', u'CI Tierra del Fuego'),
    ('80', u'CUIT'),
    ('86', u'CUIL'),
    ('87', u'CDI'),
    ('89', u'LE'),
    ('90', u'LC'),
    ('91', u'CI extranjera'),
    ('92', u'en trámite'),
    ('93', u'Acta nacimiento'),
    ('94', u'Pasaporte'),
    ('95', u'CI Bs. As. RNP'),
    ('96', u'DNI'),
    ('99', u'Sin identificar/venta global diaria'),
    ('30', u'Certificado de Migración'),
    ('88', u'Usado por Anses para Padrón'),
    ]

PROVINCIAS = {
    0: u'Ciudad Autónoma de Buenos Aires',
    1: u'Buenos Aires',
    2: u'Catamarca',
    3: u'Cordoba',
    4: u'Corrientes',
    5: u'Entre Rios',
    6: u'Jujuy',
    7: u'Mendoza',
    8: u'La Rioja',
    9: u'Salta',
    10: u'San Juan',
    11: u'San Luis',
    12: u'Santa Fe',
    13: u'Santiago del Estero',
    14: u'Tucuman',
    16: u'Chaco',
    17: u'Chubut',
    18: u'Formosa',
    19: u'Misiones',
    20: u'Neuquen',
    21: u'La Pampa',
    22: u'Rio Negro',
    23: u'Santa Cruz',
    24: u'Tierra del Fuego',
    }


class AFIPVatCountry(ModelSQL, ModelView):
    'AFIP Vat Country'
    __name__ = 'party.afip.vat.country'

    vat_number = fields.Char('VAT Number')
    afip_country = fields.Many2One('afip.country', 'Country')
    type_code = fields.Selection([
        ('0', 'Juridica'),
        ('1', 'Fisica'),
        ('2', 'Otro Tipo de Entidad'),
        ], 'Type Code')

    @classmethod
    def __register__(cls, module_name):
        super(AFIPVatCountry, cls).__register__(module_name)
        pool = Pool()
        Country = pool.get('country.country')
        AFIPCountry = pool.get('afip.country')
        table = cls.__table__()
        country = Country.__table__()
        afip_country = AFIPCountry.__table__()
        cursor = Transaction().connection.cursor()
        TableHandler = backend.get('TableHandler')
        table_handler = TableHandler(cls, module_name)
        # Migration legacy: vat_country -> afip_country
        # map ISO country code to AFIP destination country code:
        pais_dst_cmp = {
            'bf': 101, 'dz': 102, 'bw': 103, 'bi': 104, 'cm': 105,
            'cf': 107, 'cg': 108, 'cd': 109, 'ci': 110, 'td': 111,
            'bj': 112, 'eg': 113, 'ga': 115, 'gm': 116, 'gh': 117,
            'gn': 118, 'gq': 119, 'ke': 120, 'ls': 121, 'lr': 122,
            'ly': 123, 'mg': 124, 'mw': 125, 'ml': 126, 'ma': 127,
            'mu': 128, 'mr': 129, 'ne': 130, 'ng': 131, 'zw': 132,
            'rw': 133, 'sn': 134, 'sl': 135, 'so': 136, 'sz': 137,
            'sd': 138, 'tz': 139, 'tg': 140, 'tn': 141, 'ug': 142,
            'zm': 144, 'ao': 149, 'cv': 150, 'mz': 151, 'sc': 152,
            'dj': 153, 'km': 155, 'gw': 156, 'st': 157, 'na': 158,
            'za': 159, 'er': 160, 'et': 161, 'ar': 200, 'bb': 201,
            'bo': 202, 'br': 203, 'ca': 204, 'co': 205, 'cr': 206,
            'cu': 207, 'cl': 208, 'do': 209, 'ec': 210, 'sv': 211,
            'us': 212, 'gt': 213, 'gy': 214, 'ht': 215, 'hn': 216,
            'jm': 217, 'mx': 218, 'ni': 219, 'pa': 220, 'py': 221,
            'pe': 222, 'pr': 223, 'tt': 224, 'uy': 225, 've': 226,
            'sr': 232, 'dm': 233, 'lc': 234, 'vc': 235, 'bz': 236,
            'ag': 237, 'kn': 238, 'bs': 239, 'gd': 240, 'af': 301,
            'sa': 302, 'bh': 303, 'mm': 304, 'bt': 305, 'kh': 306,
            'lk': 307, 'kp': 308, 'kr': 309, 'cn': 310, 'ph': 312,
            'tw': 313, 'in': 315, 'id': 316, 'iq': 317, 'ir': 318,
            'il': 319, 'jp': 320, 'jo': 321, 'qa': 322, 'kw': 323,
            'la': 324, 'lb': 325, 'my': 326, 'mv': 327, 'om': 328,
            'mn': 329, 'np': 330, 'ae': 331, 'pk': 332, 'sg': 333,
            'sy': 334, 'th': 335, 'vn': 337, 'hk': 341, 'mo': 344,
            'bd': 345, 'bn': 346, 'ye': 348, 'am': 349, 'az': 350,
            'ge': 351, 'kz': 352, 'kg': 353, 'tj': 354, 'tm': 355,
            'uz': 356, 'ps': 357, 'al': 401, 'ad': 404, 'at': 405,
            'be': 406, 'bg': 407, 'dk': 409, 'es': 410, 'fi': 411,
            'fr': 412, 'gr': 413, 'hu': 414, 'ie': 415, 'is': 416,
            'it': 417, 'li': 418, 'lu': 419, 'mt': 420, 'mc': 421,
            'no': 422, 'nl': 423, 'pl': 424, 'pt': 425, 'gb': 426,
            'ro': 427, 'sm': 428, 'se': 429, 'ch': 430, 'va': 431,
            'cy': 435, 'tr': 436, 'de': 438, 'by': 439, 'ee': 440,
            'lv': 441, 'lt': 442, 'md': 443, 'ru': 444, 'ua': 445,
            'ba': 446, 'hr': 447, 'sk': 448, 'si': 449, 'mk': 450,
            'cz': 451, 'me': 453, 'rs': 454, 'au': 501, 'nr': 503,
            'nz': 504, 'vu': 505, 'ws': 506, 'fj': 512, 'pg': 513,
            'ki': 514, 'fm': 515, 'pw': 516, 'tv': 517, 'sb': 518,
            'to': 519, 'mh': 520, 'mp': 521,
            }
        if table_handler.column_exist('vat_country'):
            cursor.execute(*table.select(
                    table.id, table.vat_country))

            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country.select(country.code,
                            where=(country.id == vat_country_id)))
                    row, = cursor_dict(cursor)
                    dst = pais_dst_cmp.get(row['code'].lower(), None)
                    if not dst:
                        continue
                    cursor.execute(*afip_country.select(afip_country.id,
                            where=(afip_country.code == str(dst))))
                    try:
                        row, = cursor_dict(cursor)
                    except:
                        continue
                    cursor.execute(*table.update(
                        [table.afip_country], [row['id']],
                        where=table.id == id))
            table_handler.drop_column('vat_country')


class Party:
    __metaclass__ = PoolMeta
    __name__ = 'party.party'

    iva_condition = fields.Selection([
        ('', ''),
        ('responsable_inscripto', 'Responsable Inscripto'),
        ('exento', 'Exento'),
        ('consumidor_final', 'Consumidor Final'),
        ('monotributo', 'Monotributo'),
        ('no_alcanzado', 'No alcanzado'),
        ], 'Condicion ante el IVA', states={
            'readonly': ~Eval('active', True),
            'required': Bool(Eval('vat_number')),
            }, depends=['active', 'vat_number'])
    company_name = fields.Char('Company Name',
        states={'readonly': ~Eval('active', True)},
        depends=['active'])
    company_type = fields.Selection([
        ('', ''),
        ('cooperativa', 'Cooperativa'),
        ('srl', 'SRL'),
        ('sa', 'SA'),
        ('s_de_h', 'S de H'),
        ('estado', 'Estado'),
        ('exterior', 'Exterior'),
        ], 'Company Type', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    iibb_type = fields.Selection([
        ('', ''),
        ('cm', 'Convenio Multilateral'),
        ('rs', 'Regimen Simplificado'),
        ('exento', 'Exento'),
        ], 'Inscripcion II BB', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    iibb_number = fields.Char('Nro .II BB', states={
        'readonly': ~Eval('active', True),
        'required': And(
            Not(Equal(Eval('iibb_type'), 'exento')),
            Bool(Eval('iibb_type'))),
        }, depends=['active', 'iibb_type'])
    primary_activity_code = fields.Selection(CODES,
        'Primary Activity Code', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    secondary_activity_code = fields.Selection(CODES,
        'Secondary Activity Code', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    start_activity_date = fields.Date('Start activity date',
        states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    controlling_entity = fields.Char('Entidad controladora',
        help='Controlling entity', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    controlling_entity_number = fields.Char('Nro. entidad controladora',
        help='Controlling entity', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    tipo_documento = fields.Selection(TIPO_DOCUMENTO,
        'Tipo documento', states={
            'readonly': ~Eval('active', True),
            }, depends=['active'])
    vat_number = fields.Function(fields.Char('CUIT', states={
        'readonly': ~Eval('active', True),
        'required': ~In(Eval('iva_condition'),
            ['', 'consumidor_final', 'no_alcanzado']),
        }, depends=['active', 'iva_condition']),
        'get_vat_number', setter='set_vat_number',
        searcher='search_vat_number')
    vat_number_afip_foreign = fields.Function(fields.Char('CUIT AFIP Foreign'),
        'get_vat_number_afip_foreign',
        searcher='search_vat_number_afip_foreign')

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        cls._buttons.update({
            'get_afip_data': {},
            'import_census': {},
            })

    @staticmethod
    def default_iva_condition():
        return ''

    @staticmethod
    def default_tipo_documento():
        return '80'

    def get_vat_number(self, name):
        for identifier in self.identifiers:
            if identifier.type == 'ar_cuit':
                return identifier.code

    @classmethod
    def _vat_types(cls):
        vat_types = super(Party, cls)._vat_types()
        vat_types.append('ar_cuit')
        vat_types.append('ar_dni')
        vat_types.append('ar_foreign')
        return vat_types

    @classmethod
    def set_vat_number(cls, partys, name, value):
        party_id = partys[0].id
        PartyIdentifier = Pool().get('party.identifier')
        identifiers = PartyIdentifier.search([
            ('party', 'in', partys),
            ('type', '=', 'ar_cuit'),
            ])
        PartyIdentifier.delete(identifiers)
        if not value:
            return
        PartyIdentifier.create([{
            'code': cuit.compact(value),
            'type': 'ar_cuit',
            'party': party_id,
            }])

    @classmethod
    def search_vat_number(cls, name, clause):
        return [
            ('identifiers.code',) + tuple(clause[1:]),
            ('identifiers.type', '=', 'ar_cuit'),
            ]

    def get_vat_number_afip_foreign(self, name):
        for identifier in self.identifiers:
            if identifier.type == 'ar_foreign':
                return identifier.code

    @classmethod
    def search_vat_number_afip_foreign(cls, name, clause):
        return [
            ('identifiers.code',) + tuple(clause[1:]),
            ('identifiers.type', '=', 'ar_foreign'),
            ]

    @classmethod
    def get_ws_afip(cls, vat_number):
        try:
            # authenticate against AFIP:
            from trytond.modules.account_invoice_ar.afip_auth import get_cache_dir
            ws = WSSrPadronA5()
            Company = Pool().get('company.company')
            if Transaction().context.get('company'):
                company = Company(Transaction().context['company'])
            else:
                logger.error('The company is not defined')
                cls.raise_user_error('company_not_defined')
            auth_data = company.pyafipws_authenticate(service='ws_sr_padron_a5')
            # connect to the webservice and call to the test method
            ws.LanzarExcepciones = True
            cache_dir = get_cache_dir()
            if company.pyafipws_mode_cert == 'homologacion':
                WSDL = 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl'
            elif company.pyafipws_mode_cert == 'produccion':
                WSDL = 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl'
            ws.Conectar(wsdl=WSDL, cache=cache_dir)
            # set AFIP webservice credentials:
            ws.Cuit = company.party.vat_number
            ws.Token = auth_data['token']
            ws.Sign = auth_data['sign']
            ws.Consultar(vat_number)
            return ws
        except Exception, e:
            logger.error('Could not retrieve "%s" msg AFIP: "%s".' %
                (vat_number, repr(e)))
            return None

    def set_padron(self, padron, button_afip=True):
        if padron.tipo_persona == 'FISICA':
            self.name = "%s, %s" % \
                (padron.data.get('apellido'), padron.data.get('nombre'))
        else:
            self.name = padron.data.get('razonSocial', '')
        if padron.data.get('estadoClave') == 'ACTIVO':
            self.active = True
        else:
            self.active = False

        mt = 'S' == padron.monotributo
        impuestos = padron.impuestos
        if 32 in impuestos:
            self.iva_condition = 'exento'
        elif 34 in impuestos:
            self.iva_condition = 'no_alcanzado'
        else:
            if mt:
                self.iva_condition = 'monotributo'
            elif 30 in impuestos:
                self.iva_condition = 'responsable_inscripto'
            else:
                self.iva_condition = 'consumidor_final'

        if button_afip:
            fecha_inscripcion = padron.data.get('fechaInscripcion', None)
            if fecha_inscripcion:
                self.start_activity_date = fecha_inscripcion.date()
            activ = padron.actividades
            activ1 = str(activ[0]) if len(activ) >= 1 else ''
            activ2 = str(activ[1]) if len(activ) >= 2 else ''
            if activ1:
                self.primary_activity_code = activ1.rjust(6, '0')
            if activ2:
                self.secondary_activity_code = activ2.rjust(6, '0')

            Address = Pool().get('party.address')
            address_ = self.address_get('invoice')
            address_.active = False
            address_.save()
            for domicilio in padron.domicilios:
                if domicilio.get('tipoDomicilio') == 'FISCAL':
                    address = Address()
                    address.street = domicilio.get('direccion', '')
                    address.city = domicilio.get('localidad', '')
                    address.zip = domicilio.get('codPostal')
                    address.country = self.get_afip_country()
                    address.subdivision = \
                        self.get_afip_subdivision(domicilio.get('idProvincia', 0))
                    address.party = self
                    if domicilio.get('tipoDomicilio') ==  'FISCAL':
                        address.invoice = True
                    address.save()
        self.save()

    @classmethod
    def get_afip_subdivision(cls, subdivision_code):
        Subdivision = Pool().get('country.subdivision')
        subdivision = PROVINCIAS[subdivision_code]
        subdivision = Subdivision().search(
            ['name', '=', subdivision]
        )
        if len(subdivision) > 0:
            return subdivision[0]
        else:
            return ''

    @classmethod
    def get_afip_country(cls):
        Country = Pool().get('country.country')
        return Country().search(['code', '=', 'AR'])[0]

    # Button de AFIP
    @classmethod
    @ModelView.button_action('party_ar.wizard_get_afip_data')
    def get_afip_data(cls, parties):
        pass

    @classmethod
    @ModelView.button
    def import_census(cls, configs):
        '''
        Update iva_condition, active fields from afip.
        '''
        partys = cls.search([
                ('vat_number', '!=', None),
                ])

        for party in partys:
            padron = cls.get_ws_afip(party.vat_number)
            if hasattr(padron, 'data') and padron.data:
                logging.info('got "%s" afip_ws_sr_padron_a5: "%s"' %
                    (party.vat_number, padron.data))
                party.set_padron(padron, button_afip=False)
            Transaction().cursor.commit()

    @classmethod
    def import_cron_afip(cls, args=None):
        '''
        Cron update afip iva_condition.
        '''
        logger.info('Start Scheduler start update afip census.')
        cls.import_census(args)
        logger.info('End Scheduler update afip census.')


class PartyIdentifier:
    __metaclass__ = PoolMeta
    __name__ = 'party.identifier'

    afip_country = fields.Many2One('afip.country', 'Country', states={
            'invisible': ~Equal(Eval('type'), 'ar_foreign'),
            }, depends=['type'])


    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        Country = pool.get('country.country')
        Party = pool.get('party.party')
        PartyAddress = pool.get('party.address')
        PartyAFIPVatCountry = pool.get('party.afip.vat.country')
        AFIPCountry = pool.get('afip.country')
        party_afip_vat_country = PartyAFIPVatCountry.__table__()
        party_address = PartyAddress.__table__()
        party = Party.__table__()
        country_table = Country.__table__()
        afip_country = AFIPCountry.__table__()
        sql_table = cls.__table__()
        cursor = Transaction().connection.cursor()
        TableHandler = backend.get('TableHandler')
        table_a = TableHandler(cls, module_name)
        super(PartyIdentifier, cls).__register__(module_name)

        # Migration to 3.8
        if table_a.column_exist('vat_country'):
            identifiers = []
            cursor.execute(*sql_table.select(
                sql_table.id, sql_table.party, sql_table.code, sql_table.type,
                where=(sql_table.code != 'AR')))
            for identifier_id, party_id, code_country, identifier_type in \
                    cursor.fetchall():
                identifiers = []
                if not code_country or identifier_type is not None:
                    continue

                type = identifier_type
                code = None
                vat_country = ''
                cursor.execute(*party.select(
                    party.tipo_documento, where=(party.id == party_id)))
                party_row, = cursor_dict(cursor)
                if (party_row['tipo_documento'] and
                        party_row['tipo_documento'] == '96' and
                        len(code_country) < 11):
                    code = code_country
                    type = 'ar_dni'
                elif code_country.startswith('AR'):
                    code = code_country[2:]
                    if cuit.is_valid(code):
                        type = 'ar_cuit'
                    else:
                        type = identifier_type
                elif len(code_country) < 11:
                    code = code_country
                    type = 'ar_dni'
                else:
                        code = code_country
                        type = 'ar_foreign'
                        cursor_pa = Transaction().connection.cursor()
                        cursor_pa.execute(*party_address.join(country_table,
                                condition=(party_address.country == country_table.id)
                                ).select(country_table.code,
                                where=(party_address.party == party_id)))
                        row, = cursor_dict(cursor_pa)
                        if row:
                            vat_country = row['code']
                            country, = Country.search([('code', '=', vat_country)])
                            cursor_pa = Transaction().connection.cursor()
                            cursor_pa.execute(*party_afip_vat_country.select(
                                party_afip_vat_country.vat_country,
                                where=(party_afip_vat_country.vat_number == code)))
                            afip_vat_country, = cursor_dict(cursor_pa)
                            if afip_vat_country is None:
                                afip_vat_countrys = []
                                country, = Country.search([('code', '=', vat_country)])
                                afip_vat_countrys.append(PartyAFIPVatCountry(
                                    type_code='0', vat_country=country,
                                    vat_number=code))
                                PartyAFIPVatCountry.save(afip_vat_countrys)
                identifiers.append(
                    cls(id=identifier_id, code=code, type=type,
                        vat_country=vat_country, party=party_id))
            cls.save(identifiers)

        # Migrate to 4.0
        if table_a.column_exist('vat_country'):
            if table_a.column_exist('country'):
                cursor.execute(*sql_table.select(
                    sql_table.id, sql_table.vat_country, sql_table.country,
                    where=(sql_table.type == 'ar_foreign')))

                for identifier_id, vat_country, country in cursor.fetchall():
                    if vat_country != '':
                        country_code, = Country.search([
                            ('code', '=', vat_country),
                            ])
                        cursor.execute(*sql_table.update(
                            [sql_table.country, sql_table.vat_country],
                            [country_code.id, ''],
                            where=(sql_table.id == identifier_id)))
            table_a.drop_column('vat_country')

        # Migration legacy: country -> afip_country
        # map ISO country code to AFIP destination country code:
        pais_dst_cmp = {
            'bf': 101, 'dz': 102, 'bw': 103, 'bi': 104, 'cm': 105,
            'cf': 107, 'cg': 108, 'cd': 109, 'ci': 110, 'td': 111,
            'bj': 112, 'eg': 113, 'ga': 115, 'gm': 116, 'gh': 117,
            'gn': 118, 'gq': 119, 'ke': 120, 'ls': 121, 'lr': 122,
            'ly': 123, 'mg': 124, 'mw': 125, 'ml': 126, 'ma': 127,
            'mu': 128, 'mr': 129, 'ne': 130, 'ng': 131, 'zw': 132,
            'rw': 133, 'sn': 134, 'sl': 135, 'so': 136, 'sz': 137,
            'sd': 138, 'tz': 139, 'tg': 140, 'tn': 141, 'ug': 142,
            'zm': 144, 'ao': 149, 'cv': 150, 'mz': 151, 'sc': 152,
            'dj': 153, 'km': 155, 'gw': 156, 'st': 157, 'na': 158,
            'za': 159, 'er': 160, 'et': 161, 'ar': 200, 'bb': 201,
            'bo': 202, 'br': 203, 'ca': 204, 'co': 205, 'cr': 206,
            'cu': 207, 'cl': 208, 'do': 209, 'ec': 210, 'sv': 211,
            'us': 212, 'gt': 213, 'gy': 214, 'ht': 215, 'hn': 216,
            'jm': 217, 'mx': 218, 'ni': 219, 'pa': 220, 'py': 221,
            'pe': 222, 'pr': 223, 'tt': 224, 'uy': 225, 've': 226,
            'sr': 232, 'dm': 233, 'lc': 234, 'vc': 235, 'bz': 236,
            'ag': 237, 'kn': 238, 'bs': 239, 'gd': 240, 'af': 301,
            'sa': 302, 'bh': 303, 'mm': 304, 'bt': 305, 'kh': 306,
            'lk': 307, 'kp': 308, 'kr': 309, 'cn': 310, 'ph': 312,
            'tw': 313, 'in': 315, 'id': 316, 'iq': 317, 'ir': 318,
            'il': 319, 'jp': 320, 'jo': 321, 'qa': 322, 'kw': 323,
            'la': 324, 'lb': 325, 'my': 326, 'mv': 327, 'om': 328,
            'mn': 329, 'np': 330, 'ae': 331, 'pk': 332, 'sg': 333,
            'sy': 334, 'th': 335, 'vn': 337, 'hk': 341, 'mo': 344,
            'bd': 345, 'bn': 346, 'ye': 348, 'am': 349, 'az': 350,
            'ge': 351, 'kz': 352, 'kg': 353, 'tj': 354, 'tm': 355,
            'uz': 356, 'ps': 357, 'al': 401, 'ad': 404, 'at': 405,
            'be': 406, 'bg': 407, 'dk': 409, 'es': 410, 'fi': 411,
            'fr': 412, 'gr': 413, 'hu': 414, 'ie': 415, 'is': 416,
            'it': 417, 'li': 418, 'lu': 419, 'mt': 420, 'mc': 421,
            'no': 422, 'nl': 423, 'pl': 424, 'pt': 425, 'gb': 426,
            'ro': 427, 'sm': 428, 'se': 429, 'ch': 430, 'va': 431,
            'cy': 435, 'tr': 436, 'de': 438, 'by': 439, 'ee': 440,
            'lv': 441, 'lt': 442, 'md': 443, 'ru': 444, 'ua': 445,
            'ba': 446, 'hr': 447, 'sk': 448, 'si': 449, 'mk': 450,
            'cz': 451, 'me': 453, 'rs': 454, 'au': 501, 'nr': 503,
            'nz': 504, 'vu': 505, 'ws': 506, 'fj': 512, 'pg': 513,
            'ki': 514, 'fm': 515, 'pw': 516, 'tv': 517, 'sb': 518,
            'to': 519, 'mh': 520, 'mp': 521,
            }
        if table_a.column_exist('country'):
            cursor.execute(*sql_table.select(
                    sql_table.id, sql_table.country))

            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country_table.select(country_table.code,
                            where=(country_table.id == vat_country_id)))
                    row, = cursor_dict(cursor)
                    dst = pais_dst_cmp.get(row['code'].lower(), None)
                    if not dst:
                        continue
                    cursor.execute(*afip_country.select(afip_country.id,
                            where=(afip_country.code == str(dst))))
                    try:
                        row, = cursor_dict(cursor)
                    except:
                        continue
                    cursor.execute(*sql_table.update(
                        [sql_table.afip_country], [row['id']],
                        where=sql_table.id == id))
            table_a.drop_column('country')

    @classmethod
    def get_types(cls):
        types = super(PartyIdentifier, cls).get_types()
        types.append(('ar_cuit', 'CUIT'))
        types.append(('ar_foreign', 'CUIT AFIP Foreign'))
        types.append(('ar_dni', 'DNI'))
        return types

    @fields.depends('type', 'code')
    def on_change_with_code(self):
        code = super(PartyIdentifier, self).on_change_with_code()
        if self.type == 'ar_cuit':
            try:
                return cuit.compact(code)
            except stdnum.exceptions.ValidationError:
                pass
        return code

    @classmethod
    def validate(cls, identifiers):
        super(PartyIdentifier, cls).validate(identifiers)
        for identifier in identifiers:
            identifier.check_code()

    def check_code(self):
        super(PartyIdentifier, self).check_code()
        if self.type == 'ar_cuit':
            if not cuit.is_valid(self.code):
                self.raise_user_error('invalid_vat', {
                        'code': self.code,
                        'party': self.party.rec_name,
                        })
        elif self.type == 'ar_foreign':
            self.check_foreign_vat()

    def check_foreign_vat(self):
        AFIPVatCountry = Pool().get('party.afip.vat.country')

        if not self.afip_country:
            return

        vat_numbers = AFIPVatCountry.search([
            ('afip_country.code', '=', self.afip_country.code),
            ('vat_number', '=', self.code),
            ])

        if not vat_numbers:
            self.raise_user_error('invalid_vat', {
                'code': self.code,
                'party': self.party.name,
                })


class GetAFIPDataStart(ModelView):
    'Get AFIP Data Start'
    __name__ = 'party.get_afip_data.start'
    name = fields.Char('Name', readonly=True)
    direccion = fields.Char('Direccion', readonly=True)
    localidad = fields.Char('Localidad', readonly=True)
    codigo_postal = fields.Char('Codigo Postal', readonly=True)
    fecha_inscripcion = fields.Date('Fecha de Inscripcion', readonly=True)
    subdivision_code = fields.Integer('Subdivision', readonly=True)
    primary_activity_code = fields.Selection(CODES, 'Actividad primaria',
        readonly=True)
    secondary_activity_code = fields.Selection(CODES, 'Actividad secundaria',
        readonly=True)
    estado = fields.Char('Estado', readonly=True)


class GetAFIPData(Wizard):
    'Get AFIP Data'
    __name__ = 'party.get_afip_data'

    @classmethod
    def __setup__(cls):
        super(GetAFIPData, cls).__setup__()
        cls._error_messages.update({
            'vat_number_not_found':
                u'No fue posible obtener el CUIT del Tercero "%(party)s" '
                u'Mensaje AFIP: "%(error)s"',
        })

    start = StateView(
        'party.get_afip_data.start',
        'party_ar.get_afip_data_start_view', [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('OK', 'update_party', 'tryton-ok', default=True),
        ])
    update_party = StateTransition()

    def default_start(self, fields):
        Party = Pool().get('party.party')
        res = {}
        party = Party(Transaction().context['active_id'])
        if party:
            padron = Party.get_ws_afip(party.vat_number)
            if hasattr(padron, 'data') and padron.data:
                activ = padron.actividades
                for domicilio in padron.domicilios:
                    if domicilio.get('tipoDomicilio') == 'FISCAL':
                        res['direccion'] = domicilio.get("direccion", "")
                        res['localidad'] = domicilio.get("localidad", "")  # no usado en CABA
                        res['subdivision_code'] = domicilio.get("idProvincia", 0)
                        res['codigo_postal'] = domicilio.get("codPostal")

                activ1 = str(activ[0]) if len(activ) >= 1 else ''
                activ2 = str(activ[1]) if len(activ) >= 2 else ''
                if activ1:
                    activ1 = activ1.rjust(6, '0')
                if activ2:
                    activ2 = activ2.rjust(6, '0')

                if padron.tipo_persona == 'FISICA':
                    res['name'] = "%s, %s" % \
                        (padron.data.get('apellido'), padron.data.get('nombre'))
                else:
                    res['name'] = padron.data.get('razonSocial', '')

                res.update({
                    'fecha_inscripcion': padron.data.get('fechaInscripcion', None),
                    'primary_activity_code': activ1,
                    'secondary_activity_code': activ2,
                    'estado': padron.data.get('estadoClave', ''),
                })
            else:
                self.raise_user_error('vat_number_not_found', {
                        'party': party.rec_name,
                        'error': ''.join([e['error'] for e in padron.errores]),
                        })
        return res

    def transition_update_party(self):
        # Actualizamos la party con la data que vino de AFIP
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        padron = Party.get_ws_afip(party.vat_number)
        if hasattr(padron, 'data') and padron.data:
            logging.info('got "%s" afip_ws_sr_padron_a5: "%s"' %
                (party.vat_number, padron.data))
            party.set_padron(padron)
        return 'end'
