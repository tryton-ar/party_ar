# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from pyafipws.ws_sr_padron import WSSrPadronA4
import stdnum.ar.cuit as cuit
import stdnum.exceptions
from ast import literal_eval
from actividades import CODES

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pyson import Bool, Eval, Equal, Not, And, In
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.modules.account_invoice_ar.afip_auth import get_cache_dir
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

    @classmethod
    def get_ws_afip(cls, vat_number):
        try:
            # authenticate against AFIP:
            ws = WSSrPadronA4()
            Company = Pool().get('company.company')
            if Transaction().context.get('company'):
                company = Company(Transaction().context['company'])
            else:
                logger.error('The company is not defined')
                cls.raise_user_error('company_not_defined')
            auth_data = company.pyafipws_authenticate(service='ws_sr_padron_a4')
            # connect to the webservice and call to the test method
            ws.LanzarExcepciones = True
            cache_dir = get_cache_dir()
            if company.pyafipws_mode_cert == 'homologacion':
                WSDL = 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl'
            elif company.pyafipws_mode_cert == 'produccion':
                WSDL = 'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl'
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
        partys = Pool().get('party.party').search([
                ('vat_number', '!=', None),
                ])

        for party in partys:
            padron = cls.get_ws_afip(party.vat_number)
            if padron:
                logging.info('got "%s" afip_ws_sr_padron_a4: "%s"' %
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
        party_afip_vat_country = PartyAFIPVatCountry.__table__()
        party_address = PartyAddress.__table__()
        party = Party.__table__()
        country_table = Country.__table__()
        sql_table = cls.__table__()
        cursor = Transaction().cursor
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
            party_row = cursor.dictfetchone()
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
                cursor_pa = Transaction().cursor
                cursor_pa.execute(*party_address.join(country_table,
                        condition=(party_address.country == country_table.id)
                        ).select(country_table.code,
                        where=(party_address.party == party_id)))
                row = cursor_pa.dictfetchone()
                if row:
                    vat_country = row['code']
                    country, = Country.search([('code', '=', vat_country)])
                    cursor_pa = Transaction().cursor
                    cursor_pa.execute(*party_afip_vat_country.select(
                        party_afip_vat_country.vat_country,
                        where=(party_afip_vat_country.vat_number == code)))
                    afip_vat_country = cursor_pa.dictfetchone()
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
            padron = Party.get_ws_afip(party.vat_number)
            if padron:
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
                self.raise_user_error('vat_number_not_found')
        return res

    def transition_update_party(self):
        # Actualizamos la party con la data que vino de AFIP
        Party = Pool().get('party.party')
        party = Party(Transaction().context.get('active_id'))
        padron = Party.get_ws_afip(party.vat_number)
        if padron:
            logging.info('got "%s" afip_ws_sr_padron_a4: "%s"' %
                (party.vat_number, padron.data))
            party.set_padron(padron)
        return 'end'
