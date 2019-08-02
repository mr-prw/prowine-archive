# -*- coding: utf-8 -*-

from http import client
from io import StringIO
import json
import logging
from urllib.parse import urlparse
from odoo import api, fields, models, _
from odoo.exceptions import Warning

_logger = logging.getLogger(__name__)


class NovaPoshtaConfig(models.Model):
    _name = "nova.poshta.config"

    name = fields.Char('Account Name')
    key = fields.Char('API key', required=True)
    url = fields.Char('Host', default='https://api.novaposhta.ua/v2.0/json/')

    @api.model
    def verify_response(self, response):
        if response['success'] != True:
            if isinstance(response['errors'], list):
                error_text = response['errors'][0]
                error_code = response['errorCodes'][0]
                raise Warning('Error during Nova Poshta API connection: {}.\n'
                              'Code: {}'.format(error_text,error_code))
            else:
                _logger.info("<Nova Poshta API> Error "
                             "response: {}".format(response))

    @api.multi
    def connect(self, model_name, called_method, method_properties=None):
        """
        Connect to Nova Poshta API 2.0 by JSON format
        """
        for record in self:
            u = urlparse(record.url)
            headers = {
                'Content-type': 'application/json',
            }
            request_data = {
                'apiKey': record.key,
                'modelName': model_name,
                'calledMethod': called_method,
            }
            if method_properties:
                request_data.update({
                    'methodProperties': method_properties,
                })
            json_data = json.dumps(request_data)
            connection = client.HTTPSConnection(u.hostname)
            connection.request('POST', u.path, headers=headers, body=json_data)
            response = connection.getresponse()
            json_str = response.read().decode('utf-8')
            response_dict = json.loads(json_str)
            return response_dict

    @api.multi
    def get_cities(self):
        """
        Get list of cities where :
        - Ref: string[36] - Идентификатор Области
        - Description: string[50] - Город на украинском языке
        - DescriptionRu: string[50] - Город на русском языке
        - Delivery1- Delivery7: int[1] - Наличие доставки отправления в днях недели
        - Area: string[36] - Идентификатор области
        - Conglomerates: null - Конгломерат
        - CityID: int[] - Код населенного пункта
        - SettlementType: string[36] - Идентификатор (REF) со справочника населенных пунктов Украины
        - SettlementTypeDescriptionRu: string[36] - Описание типа населенного пункта на Русском языке
        - SettlementTypeDescription: string[36] - Описание типа населенного пункта на Украинском языке
        """
        for record in self:
            response = self.connect('Address', 'getCities')
            city_obj = self.env['nova.poshta.city']
            self.verify_response(response)
            for line in response['data']:
                vals = {
                    'ref': line['Ref'],
                    'name': line['Description'],
                    'name_ru': line['DescriptionRu'],
                    'code': int(line['CityID']),
                    'area': line['Area'],
                    'settlement_type': line['SettlementType'],
                    'delivery_1': bool(line['Delivery1']),
                    'delivery_2': bool(line['Delivery2']),
                    'delivery_3': bool(line['Delivery3']),
                    'delivery_4': bool(line['Delivery4']),
                    'delivery_5': bool(line['Delivery5']),
                    'delivery_6': bool(line['Delivery6']),
                    'delivery_7': bool(line['Delivery7']),
                }
                if 'SettlementTypeDescription' in line.keys():
                    vals.update({
                        'settlement_type_description': line['SettlementTypeDescription']
                    })
                if 'SettlementTypeDescriptionRu' in line.keys():
                    vals.update({
                        'settlement_type_description_ru': line['SettlementTypeDescriptionRu']
                    })
                if line['Area']:
                    area = self.env['nova.poshta.area'].search([
                        ('ref', 'like', line['Area'])
                    ])
                    if area:
                        vals.update({'area_id': area.id})
                record_exist = city_obj.search([
                    ('ref', '=', line['Ref']),
                ])
                if record_exist:
                    city_obj.write(vals)
                else:
                    city_obj.create(vals)

    @api.multi
    def get_settlements(self):
        """
        Get list of settlements where :
        """
        for record in self:
            page = 0
            stop = False
            while not stop:
                properties = {'Page': str(page)}
                response = self.connect('AddressGeneral', 'getSettlements', properties)
                self.verify_response(response)
                if response['data']:
                    page += 1
                else:
                    stop = True
                settlement_obj = self.env['nova.poshta.settlement']
                # _logger.debug("\n   >>>   page={}, data={}".format(page, len(response['data'])))
                for line in response['data']:
                    vals = {
                        'ref': line['Ref'],
                        'type': line['SettlementType'],
                        'name': line['Description'],
                        'name_ru': line['DescriptionRu'],
                        'area': line['Area'],
                        'type_description': line['SettlementTypeDescription'],
                        'type_description_ru': line['SettlementTypeDescriptionRu'],
                        'region': line['Region'],
                        'region_description': line['RegionsDescription'],
                        'region_description_ru': line['RegionsDescriptionRu'],
                        'index_1': line['Index1'],
                        'index_2': line['Index2'],
                        'index_coatsu_1': line['IndexCOATSU1'],
                        'delivery_1': bool(line['Delivery1']),
                        'delivery_2': bool(line['Delivery2']),
                        'delivery_3': bool(line['Delivery3']),
                        'delivery_4': bool(line['Delivery4']),
                        'delivery_5': bool(line['Delivery5']),
                        'delivery_6': bool(line['Delivery6']),
                        'delivery_7': bool(line['Delivery7']),
                        'warehouse': line['Warehouse'],
                    }
                    if line['Area']:
                        area = self.env['nova.poshta.area'].search([
                            ('ref', 'like', line['Area'])
                        ])
                        if area:
                            vals.update({'area_id': area.id})
                    record_exist = settlement_obj.search([
                        ('ref', '=', line['Ref']),
                    ])
                    if record_exist:
                        settlement_obj.write(vals)
                    else:
                        settlement_obj.create(vals)

    @api.multi
    def get_warehouses(self):
        """
        Get list of cities where :
        - Ref: string[36] - Идентификатор Области
        - Ref string[36] Идентификатор адреса
        - SiteKey decimal[9999999999] Код отделения
        - Description string[99] Название отделения на Украинском
        - DescriptionRu string[99] Название отделения на русском
        - TypeOfWarehouse string[36] Тип отделения
        - Ref string[36] Идентификатор отделения
        - Number int[99999] Номер отделения
        - CityRef string[36] Идентификатор населенного пункта
        - CityDescription string[50] Название населенного пункта на Украинском
        - CityDescriptionRu string[50] Название населенного пункта на русском
        - Longitude int[50] Долгота
        - Latitude int[50] Широта
        - PostFinance int[1] (1/0) Наличие кассы Пост-Финанс
        - POSTerminal int[1] (1/0) Наличие пос-терминала на отделении
        - InternationalShipping int[1] (1/0) Возможность оформления Международного отправления
        - TotalMaxWeightAllowed int[9999999999] Максимальный вес отправления
        - PlaceMaxWeightAllowed int[9999999999] Максимальный вес одного места отправления
        - Reception array[7] График приема отправлений
        - Delivery array[7] График отправки день в день
        - Schedule array[7] График работы
        """
        for record in self:
            properties = {'Language': 'ru'}
            response = self.connect('AddressGeneral', 'getWarehouses', properties)
            self.verify_response(response)
            warehouse_obj = self.env['nova.poshta.warehouse']
            for line in response['data']:
                vals = {
                    'ref': line['Ref'],
                    'name': line['Description'],
                    'name_ru': line['DescriptionRu'],
                    'site_key': line['SiteKey'],
                    'type': line['TypeOfWarehouse'],
                    'number': line['Number'],
                    'city_ref': line['CityRef'],
                    'city_description': line['CityDescription'],
                    'city_description_ru': line['CityDescriptionRu'],
                }
                record_exist = warehouse_obj.search([
                    ('ref', '=', line['Ref']),
                ])
                if record_exist:
                    warehouse_obj.write(vals)
                else:
                    warehouse_obj.create(vals)

    @api.multi
    def get_areas(self):
        """
        Get list of areas of Ukraine:
        - Ref: string[36] - Идентификатор Области
        - Description: string[50] - Описание на украинском языке
        - AreasCenter: string[36] - Идентификатор города, который является областным центром
        """
        for record in self:
            properties = {'Language': 'ru'}
            response = self.connect('Address', 'getAreas')
            self.verify_response(response)
            area_obj = self.env['nova.poshta.area']
            for line in response['data']:
                vals = {
                    'ref': line['Ref'],
                    'name': line['Description'],
                    'center': line['AreasCenter'],
                }
                record_exist = area_obj.search([
                    ('ref', '=', line['Ref']),
                ])
                if record_exist:
                    area_obj.write(vals)
                else:
                    area_obj.create(vals)

    @api.multi
    def action_sync_catalogs(self):
        """ Synchronization of Nova Poshta catalogs."""
        self.ensure_one()
        _logger.debug(">>> Start of Nova Poshta catalog sync "
                      "for account ID: {}.".format(self.id))
        self.get_areas()
        self.get_settlements()
        self.get_cities()
        self.get_warehouses()
        _logger.debug("<<< End of Nova Poshta catalog sync.")

    @api.model
    def sync_catalogs(self):
        """Run catalogs synchronization."""
        return self.search([], limit=1).action_sync_catalogs()
