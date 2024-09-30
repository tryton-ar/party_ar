# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from sql.conditionals import Case
from sql import Literal, Null

from pyafipws.ws_sr_padron import WSSrPadronA5
import stdnum.ar.cuit as cuit
import stdnum.exceptions
import logging

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Equal
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.tools import cursor_dict
from trytond.modules.party.exceptions import InvalidIdentifierCode
from .exceptions import CompanyNotDefined, VatNumberNotFound
from .actividades import CODES

logger = logging.getLogger(__name__)

TIPO_DOCUMENTO = [
    ('0', 'CI Policía Federal'),
    ('1', 'CI Buenos Aires'),
    ('2', 'CI Catamarca'),
    ('3', 'CI Córdoba'),
    ('4', 'CI Corrientes'),
    ('5', 'CI Entre Ríos'),
    ('6', 'CI Jujuy'),
    ('7', 'CI Mendoza'),
    ('8', 'CI La Rioja'),
    ('9', 'CI Salta'),
    ('10', 'CI San Juan'),
    ('11', 'CI San Luis'),
    ('12', 'CI Santa Fe'),
    ('13', 'CI Santiago del Estero'),
    ('14', 'CI Tucumán'),
    ('16', 'CI Chaco'),
    ('17', 'CI Chubut'),
    ('18', 'CI Formosa'),
    ('19', 'CI Misiones'),
    ('20', 'CI Neuquén'),
    ('21', 'CI La Pampa'),
    ('22', 'CI Río Negro'),
    ('23', 'CI Santa Cruz'),
    ('24', 'CI Tierra del Fuego'),
    ('80', 'CUIT'),
    ('86', 'CUIL'),
    ('87', 'CDI'),
    ('89', 'LE'),
    ('90', 'LC'),
    ('91', 'CI extranjera'),
    ('92', 'en trámite'),
    ('93', 'Acta nacimiento'),
    ('94', 'Pasaporte'),
    ('95', 'CI Bs. As. RNP'),
    ('96', 'DNI'),
    ('99', 'Sin identificar/venta global diaria'),
    ('30', 'Certificado de Migración'),
    ('88', 'Usado por Anses para Padrón'),
    ]

PROVINCIAS = {
    0: 'Ciudad Autónoma de Buenos Aires',
    1: 'Buenos Aires',
    2: 'Catamarca',
    3: 'Cordoba',
    4: 'Corrientes',
    5: 'Entre Rios',
    6: 'Jujuy',
    7: 'Mendoza',
    8: 'La Rioja',
    9: 'Salta',
    10: 'San Juan',
    11: 'San Luis',
    12: 'Santa Fe',
    13: 'Santiago del Estero',
    14: 'Tucuman',
    16: 'Chaco',
    17: 'Chubut',
    18: 'Formosa',
    19: 'Misiones',
    20: 'Neuquen',
    21: 'La Pampa',
    22: 'Rio Negro',
    23: 'Santa Cruz',
    24: 'Tierra del Fuego',
    }


class Configuration(metaclass=PoolMeta):
    __name__ = 'party.configuration'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.identifier_types.selection += [
                ('ar_cuit', 'CUIT'),
                ('ar_dni', 'DNI'),
                ('ar_foreign', 'CUIT AFIP Foreign'),
                ]


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
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        pool = Pool()
        table = cls.__table__()
        country = pool.get('country.country').__table__()
        afip_country = pool.get('afip.country').__table__()

        table_h = cls.__table_handler__(module_name)

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

        # Migration legacy: vat_country -> afip_country
        if table_h.column_exist('vat_country'):
            cursor.execute(*table.select(
                    table.id, table.vat_country))

            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country.select(country.code,
                            where=(country.id == vat_country_id)))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    dst = pais_dst_cmp.get(row[0].lower(), None)
                    if not dst:
                        continue
                    cursor.execute(*afip_country.select(afip_country.id,
                            where=(afip_country.code == str(dst))))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cursor.execute(*table.update(
                        [table.afip_country], [row[0]],
                        where=table.id == id))
            table_h.drop_column('vat_country')


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    iva_condition = fields.Selection([
        (None, ''),
        ('responsable_inscripto', 'Responsable Inscripto'),
        ('exento', 'Sujeto Exento'),
        ('consumidor_final', 'Consumidor Final'),
        ('monotributo', 'Responsable Monotributo'),
        ('proveedor_exterior', 'Proveedor del Exterior'),
        ('cliente_exterior', 'Cliente del Exterior'),
        ('no_alcanzado', 'No Alcanzado'),
        ], 'Condición ante IVA', sort=False,
        states={'required': Bool(Eval('vat_number'))})
    iva_condition_string = iva_condition.translated('iva_condition')
    iibb_condition = fields.Selection([
        (None, ''),
        ('in', 'Inscripto Jurisdicción Local'),
        ('cm', 'Inscripto Convenio Multilateral'),
        ('rs', 'Régimen Simplificado'),
        ('ex', 'Exento'),
        ('ni', 'No Inscripto'),
        ('na', 'No Alcanzado'),
        ('cs', 'Consumidor Final'),
        ], 'Condición ante IIBB', sort=False)
    iibb_condition_string = iibb_condition.translated('iibb_condition')
    iibb_number = fields.Char('Nro. IIBB',
        states={
            'required': Eval('iibb_condition').in_(['in', 'cm', 'rs'])
            })
    ganancias_condition = fields.Selection([
        (None, ''),
        ('in', 'Inscripto'),
        ('ex', 'Exento'),
        ('ni', 'No Inscripto'),
        ], 'Condición ante Ganancias', sort=False)
    ganancias_condition_string = ganancias_condition.translated(
        'ganancias_condition')
    company_name = fields.Char('Company Name')
    company_type = fields.Selection([
        (None, ''),
        ('cooperativa', 'Cooperativa'),
        ('srl', 'SRL'),
        ('sa', 'SA'),
        ('s_de_h', 'S de H'),
        ('estado', 'Estado'),
        ('exterior', 'Exterior'),
        ], 'Company Type')
    primary_activity_code = fields.Selection(CODES,
        'Primary Activity Code')
    secondary_activity_code = fields.Selection(CODES,
        'Secondary Activity Code')
    start_activity_date = fields.Date('Start activity date')
    controlling_entity = fields.Char('Entidad controladora',
        help='Controlling entity')
    controlling_entity_number = fields.Char('Nro. entidad controladora',
        help='Controlling entity number')
    tipo_documento = fields.Selection(TIPO_DOCUMENTO,
        'Tipo documento')
    vat_number = fields.Function(fields.Char('CUIT',
        states={
            'required': Bool(Eval('iva_condition').in_(
                ['responsable_inscripto', 'exento', 'monotributo'])),
            }), 'get_vat_number', setter='set_vat_number',
        searcher='search_vat_number')
    vat_number_afip_foreign = fields.Function(fields.Char('CUIT AFIP Foreign'),
        'get_vat_number_afip_foreign',
        searcher='search_vat_number_afip_foreign')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        sql_table = cls.__table__()
        table_h = cls.__table_handler__(module_name)

        iibb_type_exist = table_h.column_exist('iibb_type')
        super().__register__(module_name)
        if iibb_type_exist:
            cursor.execute(*sql_table.update([sql_table.iibb_condition], [
                Case((sql_table.iibb_type == 'cm', 'cm'),
                else_=Case((sql_table.iibb_type == 'rs', 'rs'),
                else_=Case((sql_table.iibb_type == 'exento', 'ex'),
                else_=Null)))],
                where=Literal(True)))
            table_h.drop_column('iibb_type')

            cursor.execute(*sql_table.update(
                [sql_table.iva_condition], [Null],
                where=sql_table.iva_condition == ''))

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'get_afip_data': {},
            })

    @staticmethod
    def default_tipo_documento():
        return '80'

    @classmethod
    def tax_identifier_types(cls):
        types = super().tax_identifier_types()
        types.extend(['ar_cuit', 'ar_dni', 'ar_foreign'])
        return types

    def get_vat_number(self, name):
        for identifier in self.identifiers:
            if identifier.type == 'ar_cuit':
                return identifier.code

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
        # authenticate against AFIP:
        pool = Pool()
        Company = pool.get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
        else:
            logger.error('The company is not defined')
            raise CompanyNotDefined(gettext(
                'party_ar.msg_company_not_defined'))

        ws = WSSrPadronA5()
        ws.LanzarExcepciones = True
        cache = Company.get_cache_dir()

        # set AFIP webservice credentials
        ta = company.pyafipws_authenticate(
            service='ws_sr_constancia_inscripcion')
        ws.SetTicketAcceso(ta)
        ws.Cuit = company.party.vat_number

        if company.pyafipws_mode_cert == 'homologacion':
            WSDL = ('https://awshomo.afip.gov.ar/sr-padron/webservices/'
                'personaServiceA5?wsdl')
        elif company.pyafipws_mode_cert == 'produccion':
            WSDL = ('https://aws.afip.gov.ar/sr-padron/webservices/'
                'personaServiceA5?wsdl')
        # connect to the webservice and call to the test method
        ws.Conectar(wsdl=WSDL, cache=cache, cacert=True)
        ws.Consultar(vat_number)
        return ws

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

        self.ganancias_condition = 'ni'
        if any(item in [10, 11] for item in impuestos):
            self.ganancias_condition = 'in'
        elif 12 in impuestos:
            self.ganancias_condition = 'ex'

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
            if address_:
                address_.active = False
                address_.save()
            for domicilio in padron.domicilios:
                if domicilio.get('tipoDomicilio') == 'FISCAL':
                    address = Address()
                    address.street = domicilio.get('direccion', '')
                    address.city = domicilio.get('localidad', '')
                    address.postal_code = domicilio.get('codPostal')
                    address.country = self.get_afip_country()
                    address.subdivision = self.get_afip_subdivision(
                        domicilio.get('idProvincia', 0))
                    address.party = self
                    if domicilio.get('tipoDomicilio') == 'FISCAL':
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
    def import_census(cls, configs):
        '''
        Update iva_condition, active fields from afip.
        '''
        partys = cls.search([('vat_number', '!=', None)])
        for party in partys:
            try:
                padron = cls.get_ws_afip(party.vat_number)
                logging.info('got "%s" afip_ws_sr_padron_a5: "%s"' %
                    (party.vat_number, padron.data))
                if not padron.data:
                    msg = ''.join([e['error'] for e in padron.errores])
                    raise ValueError(msg)
                party.set_padron(padron, button_afip=False)
                Transaction().commit()
            except Exception as e:
                msg = str(e)
                logger.error('Could not retrieve "%s" msg AFIP: "%s".' %
                    (party.vat_number, msg))

    @classmethod
    def import_cron_afip(cls, args=None):
        '''
        Cron update afip iva_condition.
        '''
        logger.info('Start Scheduler start update afip census.')
        cls.import_census(args)
        logger.info('End Scheduler update afip census.')


class PartyIdentifier(metaclass=PoolMeta):
    __name__ = 'party.identifier'

    afip_country = fields.Many2One('afip.country', 'Country',
        states={'invisible': ~Equal(Eval('type'), 'ar_foreign')})

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
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

        table_h = cls.__table_handler__(module_name)
        super().__register__(module_name)

        # Migration to 3.8
        if table_h.column_exist('vat_country'):
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
                            country, = Country.search([
                                ('code', '=', vat_country),
                                ])
                            afip_vat_countrys.append(PartyAFIPVatCountry(
                                type_code='0', vat_country=country,
                                vat_number=code))
                            PartyAFIPVatCountry.save(afip_vat_countrys)
                identifiers.append(
                    cls(id=identifier_id, code=code, type=type,
                        vat_country=vat_country, party=party_id))
            cls.save(identifiers)

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

        # Migration legacy: country -> afip_country
        if table_h.column_exist('country'):
            cursor.execute(*sql_table.select(
                    sql_table.id, sql_table.country))
            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country_table.select(country_table.code,
                            where=(country_table.id == vat_country_id)))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    dst = pais_dst_cmp.get(row[0].lower(), None)
                    if not dst:
                        continue
                    cursor.execute(*afip_country.select(afip_country.id,
                            where=(afip_country.code == str(dst))))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cursor.execute(*sql_table.update(
                        [sql_table.afip_country], [row[0]],
                        where=sql_table.id == id))
            table_h.drop_column('country')

        # Migration legacy: vat_country -> afip_country
        if table_h.column_exist('vat_country'):
            cursor.execute(*sql_table.select(
                sql_table.id, sql_table.vat_country,
                where=(sql_table.type == 'ar_foreign')))
            for id, vat_country in cursor.fetchall():
                if vat_country != '':
                    dst = pais_dst_cmp.get(vat_country.lower(), None)
                    if not dst:
                        continue
                    cursor.execute(*afip_country.select(afip_country.id,
                            where=(afip_country.code == str(dst))))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cursor.execute(*sql_table.update(
                        [sql_table.afip_country], [row[0]],
                        where=sql_table.id == id))
            table_h.drop_column('vat_country')

    @fields.depends('type', 'code')
    def on_change_with_code(self):
        code = super().on_change_with_code()
        if self.type == 'ar_cuit':
            try:
                return cuit.compact(code)
            except stdnum.exceptions.ValidationError:
                pass
        return code

    @classmethod
    def validate(cls, identifiers):
        super().validate(identifiers)
        for identifier in identifiers:
            identifier.check_code()

    def check_code(self):
        super().check_code()
        if self.type == 'ar_cuit':
            if not cuit.is_valid(self.code):
                raise InvalidIdentifierCode(
                    gettext('party.msg_invalid_vat_number',
                    code=self.code, party=self.party.rec_name))
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
            raise InvalidIdentifierCode(
                gettext('party.msg_invalid_vat_number',
                code=self.code, party=self.party.name))


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

    start = StateView(
        'party.get_afip_data.start',
        'party_ar.get_afip_data_start_view', [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('OK', 'update_party', 'tryton-ok', default=True),
        ])
    update_party = StateTransition()

    def default_start(self, fields):
        Party = Pool().get('party.party')

        party = Party(Transaction().context['active_id'])
        if not party:
            return {}

        try:
            padron = Party.get_ws_afip(party.vat_number)
            if not padron.data:
                msg = ''.join([e['error'] for e in padron.errores])
                raise ValueError(msg)
        except Exception as e:
            msg = str(e)
            logger.error('Could not retrieve "%s" msg AFIP: "%s".' %
                (party.vat_number, msg))
            raise VatNumberNotFound(
                gettext('party_ar.msg_vat_number_not_found',
                party=party.rec_name,
                error=msg))
        res = {}
        activ = padron.actividades
        for domicilio in padron.domicilios:
            if domicilio.get('tipoDomicilio') == 'FISCAL':
                res['direccion'] = domicilio.get("direccion", "")
                # no usado en CABA
                res['localidad'] = domicilio.get("localidad", "")
                res['subdivision_code'] = domicilio.get("idProvincia", 0)
                res['codigo_postal'] = domicilio.get("codPostal")

        activ1 = str(activ[0]) if len(activ) >= 1 else ''
        activ2 = str(activ[1]) if len(activ) >= 2 else ''
        if activ1:
            activ1 = activ1.rjust(6, '0')
        if activ2:
            activ2 = activ2.rjust(6, '0')

        if padron.tipo_persona == 'FISICA':
            res['name'] = "%s, %s" % (
                padron.data.get('apellido'), padron.data.get('nombre'))
        else:
            res['name'] = padron.data.get('razonSocial', '')

        res.update({
            'fecha_inscripcion': padron.data.get('fechaInscripcion', None),
            'primary_activity_code': activ1,
            'secondary_activity_code': activ2,
            'estado': padron.data.get('estadoClave', ''),
            })
        return res

    def transition_update_party(self):
        # Actualizamos la party con la data que vino de AFIP
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        try:
            padron = Party.get_ws_afip(party.vat_number)
            logging.info('got "%s" afip_ws_sr_padron_a5: "%s"' %
                (party.vat_number, padron.data))
            if not padron.data:
                msg = ''.join([e['error'] for e in padron.errores])
                raise ValueError(msg)
            party.set_padron(padron)
        except Exception as e:
            msg = str(e)
            logger.error('Could not retrieve "%s" msg AFIP: "%s".' %
                (party.vat_number, msg))
        return 'end'


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('party.party|import_cron_afip', "Import AFIP Census"),
                ])
