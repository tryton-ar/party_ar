# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import stdnum.ar.cuit as cuit
import stdnum.exceptions
from urllib2 import urlopen
import ssl
import sys
from json import loads, dumps
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
            'gt': 213, 'gr': 413, 'gq': 119, 'gy': 214, 'ge': 351,
            'gb': 426, 'gn': 118, 'gm': 116, 'gh': 117, 'tv': 517,
            'tt': 224, 'lk': 307, 'li': 418, 'lv': 441, 'to': 519,
            'lt': 442, 'lu': 419, 'lr': 122, 'tg': 140, 'td': 111,
            'ly': 123, 'do': 209, 'dm': 233, 'dk': 409, 'uy': 225,
            'qa': 322, 'zm': 144, 'ee': 440, 'eg': 113, 'ec': 210,
            'es': 410, 'er': 160, 'rs': 454, 'bd': 345, 'bg': 407,
            'bb': 201, 'bh': 303, 'bi': 104, 'jm': 217, 'jo': 321,
            'br': 203, 'bs': 239, 'by': 439, 'bz': 236, 'ua': 445,
            'ch': 430, 'co': 205, 'cn': 310, 'cl': 208, 'cg': 108,
            'cy': 435, 'cr': 206, 'cv': 150, 'cu': 207, 'pr': 223,
            'tn': 141, 'pw': 516, 'pt': 425, 'py': 221, 'pk': 332,
            'ph': 312, 'pl': 424, 'hr': 447, 'it': 417, 'hk': 341,
            'hn': 216, 'vn': 337, 'me': 453, 'mg': 124, 'ma': 127,
            'ml': 126, 'mo': 344, 'mn': 329, 'us': 212, 'mt': 420,
            'mw': 125, 'mr': 129, 'ug': 142, 'my': 326, 'mz': 151,
            'vc': 235, 'ad': 404, 'ag': 237, 'iq': 317, 'is': 416,
            'am': 349, 'al': 401, 'ao': 149, 'au': 501, 'at': 405,
            'in': 315, 'ie': 415, 'id': 316, 'ni': 219, 'no': 422,
            'il': 319, 'na': 158, 'ne': 130, 'ng': 131, 'np': 330,
            'so': 136, 'nr': 503, 'fr': 412, 'fi': 411, 'sz': 137,
            'sv': 211, 'sk': 448, 'si': 449, 'kw': 323, 'sn': 134,
            'sm': 428, 'sl': 135, 'sc': 152, 'sg': 333, 'se': 429,
            'uk': 426, 'bo': 202, 'ca': 204, 'mx': 218, 'pe': 222,
            've': 226, 'tw': 313, 'jp': 320, 'be': 406, 'nl': 423,
            'de': 438, 'ru': 444,
            }
        if table_handler.column_exist('vat_country'):
            cursor.execute(*table.select(
                    table.id, table.vat_country))

            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country.select(country.code,
                            where=(country.id == vat_country_id)))
                    row, = cursor_dict(cursor)
                    dst = pais_dst_cmp[row['code'].lower()]
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
            'code': value,
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
        partys = Pool().get('party.party').search([
                ('vat_number', '!=', None),
                ])

        for party in partys:
            afip_dict = {}
            try:
                data = cls.get_json_afip(party.vat_number)
                afip_dict = loads(data)
                success = afip_dict['success']
                if success is True:
                    afip_dict = afip_dict['data']
                else:
                    logger.error('Afip return error message %s.' %
                        afip_dict['error']['mensaje'])
            except:
                logging.error('Could not retrieve vat_number: %s.' %
                    party.vat_number)
            logging.info('got afip_json:\n' + dumps(afip_dict))
            mt = afip_dict.get('categoriasMonotributo', {})
            impuestos = afip_dict.get('impuestos', [])

            if 32 in impuestos:
                party.iva_condition = 'exento'
            else:
                if mt:
                    party.iva_condition = 'monotributo'
                elif 30 in impuestos:
                    party.iva_condition = 'responsable_inscripto'
                else:
                    party.iva_condition = 'consumidor_final'
            party.save()
            Transaction().cursor.commit()

    @classmethod
    def get_json_afip(cls, vat_number):
        try:
            afip_url = 'https://soa.afip.gob.ar/sr-padron/v2/persona/%s' \
                % vat_number
            if sys.version_info >= (2, 7, 9):
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                afip_stream = urlopen(afip_url, context=context)
            else:
                afip_stream = urlopen(afip_url)
            afip_json = afip_stream.read()
            return afip_json
        except Exception, e:
            logger.error('Could not retrieve %s.' % repr(e))

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
    def __setup__(cls):
        super(PartyIdentifier, cls).__setup__()
        cls._error_messages.update({
            'vat_number_not_found': 'El CUIT no ha sido encontrado',
            })

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
                    vat_country=vat_country))
            cls.save(identifiers)

        # Migrate to 4.0
        if table_a.column_exist('vat_country'):
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
            'gt': 213, 'gr': 413, 'gq': 119, 'gy': 214, 'ge': 351,
            'gb': 426, 'gn': 118, 'gm': 116, 'gh': 117, 'tv': 517,
            'tt': 224, 'lk': 307, 'li': 418, 'lv': 441, 'to': 519,
            'lt': 442, 'lu': 419, 'lr': 122, 'tg': 140, 'td': 111,
            'ly': 123, 'do': 209, 'dm': 233, 'dk': 409, 'uy': 225,
            'qa': 322, 'zm': 144, 'ee': 440, 'eg': 113, 'ec': 210,
            'es': 410, 'er': 160, 'rs': 454, 'bd': 345, 'bg': 407,
            'bb': 201, 'bh': 303, 'bi': 104, 'jm': 217, 'jo': 321,
            'br': 203, 'bs': 239, 'by': 439, 'bz': 236, 'ua': 445,
            'ch': 430, 'co': 205, 'cn': 310, 'cl': 208, 'cg': 108,
            'cy': 435, 'cr': 206, 'cv': 150, 'cu': 207, 'pr': 223,
            'tn': 141, 'pw': 516, 'pt': 425, 'py': 221, 'pk': 332,
            'ph': 312, 'pl': 424, 'hr': 447, 'it': 417, 'hk': 341,
            'hn': 216, 'vn': 337, 'me': 453, 'mg': 124, 'ma': 127,
            'ml': 126, 'mo': 344, 'mn': 329, 'us': 212, 'mt': 420,
            'mw': 125, 'mr': 129, 'ug': 142, 'my': 326, 'mz': 151,
            'vc': 235, 'ad': 404, 'ag': 237, 'iq': 317, 'is': 416,
            'am': 349, 'al': 401, 'ao': 149, 'au': 501, 'at': 405,
            'in': 315, 'ie': 415, 'id': 316, 'ni': 219, 'no': 422,
            'il': 319, 'na': 158, 'ne': 130, 'ng': 131, 'np': 330,
            'so': 136, 'nr': 503, 'fr': 412, 'fi': 411, 'sz': 137,
            'sv': 211, 'sk': 448, 'si': 449, 'kw': 323, 'sn': 134,
            'sm': 428, 'sl': 135, 'sc': 152, 'sg': 333, 'se': 429,
            'uk': 426, 'bo': 202, 'ca': 204, 'mx': 218, 'pe': 222,
            've': 226, 'tw': 313, 'jp': 320, 'be': 406, 'nl': 423,
            'de': 438, 'ru': 444,
            }
        if table_a.column_exist('country'):
            cursor.execute(*sql_table.select(
                    sql_table.id, sql_table.country))

            for id, vat_country_id in cursor.fetchall():
                if vat_country_id:
                    cursor.execute(*country_table.select(country_table.code,
                            where=(country_table.id == vat_country_id)))
                    row, = cursor_dict(cursor)
                    dst = pais_dst_cmp[row['code'].lower()]
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
                'party': self.party.rec_name,
                })


class GetAFIPDataStart(ModelView):
    'Get AFIP Data Start'
    __name__ = 'party.get_afip_data.start'
    afip_data = fields.Text('Datos extras')
    nombre = fields.Char('Nombre', readonly=True)
    direccion = fields.Char('Direccion', readonly=True)
    localidad = fields.Char('Localidad', readonly=True)
    codigo_postal = fields.Char('Codigo Postal', readonly=True)
    fecha_inscripcion = fields.Char('Fecha de Inscripcion', readonly=True)
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
            'vat_number_not_found': 'El CUIT no ha sido encontrado',
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
            afip_json = self.get_json(party.vat_number)
            afip_dict = loads(afip_json)
            print '   >>> got json:\n' + dumps(afip_dict)
            if afip_dict['success'] is True:
                afip_dict = afip_dict['data']
            else:
                self.raise_user_error('vat_number_not_found')

            activ = afip_dict.get('actividades', {})
            domicilioFiscal = afip_dict.get('domicilioFiscal', {})
            activ1 = str(activ[0]) if len(activ) >= 1 else ''
            activ2 = str(activ[1]) if len(activ) >= 2 else ''
            if activ1:
                activ1 = activ1.rjust(6, '0')
            if activ2:
                activ2 = activ2.rjust(6, '0')
            res = {
                'nombre': afip_dict['nombre'],
                'direccion': domicilioFiscal.get('direccion', ''),
                'localidad': domicilioFiscal.get('localidad', ''),
                'codigo_postal': domicilioFiscal.get('codPostal', ''),
                'fecha_inscripcion': afip_dict['fechaInscripcion'],
                'primary_activity_code': activ1,
                'secondary_activity_code': activ2,
                'estado': afip_dict['estadoClave'],
                'subdivision_code': domicilioFiscal.get('idProvincia', 0),
                'afip_data': afip_json,
            }

        return res

    def transition_update_party(self):
        # Actualizamos la party con la data que vino de AFIP
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        print '   >>> should be updating party...'

        import datetime
        # formato de fecha: AAAA-MM-DD
        fecha = self.start.fecha_inscripcion.split('-')
        if len(fecha) == 3 and len(fecha) == 3:
            year = int(fecha[0])
            month = int(fecha[1])
            day = int(fecha[2])

        party.name = self.start.nombre
        party.primary_activity_code = self.start.primary_activity_code
        party.secondary_activity_code = self.start.secondary_activity_code
        party.vat_country = 'AR'
        party.start_activity_date = datetime.date(year, month, day)
        if self.start.estado == 'ACTIVO':
            party.active = True
        else:
            party.active = False

        # Direccion
        Address = Pool().get('party.address')
        direccion = Address().search(['party', '=', party])

        if len(direccion) > 0 and (direccion[0].street is None
                or direccion[0].street == ''):
            self._update_direccion(direccion[0], party, self.start)
        else:
            direccion = Address()
            self._update_direccion(direccion, party, self.start)

        afip_dict = loads(self.start.afip_data)['data']
        mt = afip_dict.get('categoriasMonotributo', {})
        impuestos = afip_dict.get('impuestos', [])

        if 32 in impuestos:
            party.iva_condition = 'exento'
        else:
            if mt:
                party.iva_condition = 'monotributo'
            elif 30 in impuestos:
                party.iva_condition = 'responsable_inscripto'
            else:
                party.iva_condition = 'consumidor_final'

        party.save()
        return 'end'

    @classmethod
    def _update_direccion(self, direccion, party, start):
        'Actualizamos direccion de una party'
        direccion.name = start.nombre
        direccion.street = start.direccion
        direccion.city = start.localidad
        direccion.zip = start.codigo_postal
        direccion.subdivision = self.get_subdivision(start.subdivision_code)
        direccion.country = self.get_country()
        direccion.party = party
        direccion.invoice = True
        direccion.save()

    @classmethod
    def get_json(self, vat_number):
        try:
            afip_url = 'https://soa.afip.gob.ar/sr-padron/v2/persona/%s' \
                % vat_number
            if sys.version_info >= (2, 7, 9):
                context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                afip_stream = urlopen(afip_url, context=context)
            else:
                afip_stream = urlopen(afip_url)
            afip_json = afip_stream.read()
            return afip_json
        except Exception:
            self.raise_user_error('vat_number_not_found')

    @classmethod
    def get_subdivision(self, subdivision_code):
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
    def get_country(self):
        Country = Pool().get('country.country')
        country = Country().search(
            ['code', '=', 'AR']
        )[0]
        return country
