# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import xmltodict, json
import xlrd
from xlrd import open_workbook
from datetime import datetime
import base64





class SerialRecord(models.Model):
    _name = 'serial.record'

    product_id = fields.Many2one('product.product', string='Product ID')
    product_gtin = fields.Char(string='Product GTIN')
    expiry_date = fields.Date(string='Expiry Date')
    product_serial_number = fields.Char(string='Serial Number')
    product_batch_number = fields.Char(string='Batch Number')
    product_status = fields.Char(string='Product Status')




class CountryState(models.Model):
    _inherit = 'res.country.state'

    region_id = fields.Integer(string='Region ID')

class KsaCity(models.Model):
    _name = 'ksa.city'

    ksa_city_id = fields.Integer(string='City ID')
    ksa_city_name = fields.Char(string='City')
    region_id = fields.Many2one('res.country.state', string='Region')

class KsaSync(models.Model):
    _name = 'ksa.sync'

    drug_list_sync = fields.Boolean(string='Sync Drug List')
    drug_status = fields.Selection([('-1', 'All'), ('0', 'Passive'), ('1', 'Active')], string='Drug Status', )

    city_list_sync = fields.Boolean(string='City List Sync')

    stakeholder_list_sync = fields.Boolean(string='Sync Stakeholder List')
    stakeholder_type = fields.Selection([('1', 'Manufacturer'), ('2', 'Warehouse'), ('3', 'Pharmacy'), ('4', 'Consumption Center'), ('5', 'Reimbursment Agency')], string='StakeHolder Type')
    stakeholder_getall = fields.Boolean(string='Get All')
    stakeholder_cityid = fields.Char(string='City ID')

    dispatch = fields.Boolean(string='Create Dispatch')
    dispatch_gln = fields.Char(string='GLN')
    dispatch_gtin = fields.Char(string='GTIN')
    dispatch_sn = fields.Char(string='SN')
    dispatch_batch = fields.Char(string='Batch')
    dispatch_expiry_date = fields.Date(string='Expiry Date')

    upload_serial_number = fields.Binary("Upload Serial Number")

    upload_products = fields.Binary("Upload Products")

    def create_sale_order(self, notification_id):
        customer = self.env['res.partner'].search([('gln', '=', self.dispatch_gln)])
        product = self.env['product.template'].search([('gtin', '=', self.dispatch_gtin)])
        sale_order = self.env['sale.order'].create({
            'partner_id': customer.id,
            'dispatch_notification_id': int(notification_id)
        })
        sale_order_line = self.env['sale.order.line'].create({
            'product_id': product.product_variant_id.id,
            'name': product.product_variant_id.name,
            'product_uom_qty': 1,
            'price_unit': product.list_price,
            'order_id': sale_order.id,
        })
        return sale_order

    def create_dispatch(self):
        print('developing dispatch method')
        request_vals = self.create_request_vals()
        body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchServiceRequest>\n         <TOGLN>"+self.dispatch_gln+"</TOGLN>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n            <PRODUCT>\n               <GTIN>"+self.dispatch_gtin+"</GTIN>\n               <SN>"+self.dispatch_sn+"</SN>\n               <!--Optional:-->\n               <BN>"+self.dispatch_batch+"</BN>\n               <!--Optional:-->\n               <XD>"+str(self.dispatch_expiry_date)+"</XD>\n            </PRODUCT>\n         </PRODUCTLIST>\n      </dis:DispatchServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
        response = requests.request("POST", request_vals.get('URL_dispatch'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
        print(response.text)
        if response.status_code == 200:
            response_dict = xmltodict.parse(response.text)
            print(response_dict)
            print('status code 200')
            if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID'):
                notification_id = response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID')
                sale_order = self.create_sale_order(notification_id)

    def create_product(self, drug_list, available_products_gtn):
        print('creating product')
        product_count = 1
        for drug in drug_list:
            if drug.get('GTIN') not in available_products_gtn:
                vals = {
                    'name': drug.get('DRUGNAME'),
                    'sale_ok': True,
                    'purchase_ok': True,
                    'type': 'product',
                    'list_price': float(drug.get('PRICE') if drug.get('PRICE') else False),
                    'categ_id': 1,
                    'is_importable': True if drug.get('ISIMPORTABLE') == '1' else False,
                    'is_exportable': True if drug.get('ISEXPORTABLE') == '1' else False,
                    'drug_status': drug.get('DRUGSTATUS') if drug.get('DRUGSTATUS') else False,
                    'gtin': drug.get('GTIN') if drug.get('GTIN') else False,
                    'legal_status': int(drug.get('LEGALSTATUS')) if drug.get('LEGALSTATUS') else False,
                    'domain_id': int(drug.get('DOMAINID') if drug.get('DOMAINID') else False)
                }
                product = self.env['product.template'].create(vals)
                print('Product Created for GTIN: ' + drug.get('GTIN'))
                product_count += 1
            else:
                print('Product GTIN: ' + drug.get('GTIN') + 'available in inventory.')
        return product_count


    def create_request_vals(self):
        return {
            'URL_druglist': "http://tandtwstest.sfda.gov.sa:8080/ws/DrugListService/DrugListService",
            'URL_citylist': "http://tandtwstest.sfda.gov.sa:8080/ws/CityListService/CityListService",
            'URL_stakeholderlist': "http://tandtwstest.sfda.gov.sa:8080/ws/StakeholderListService/StakeholderListService",
            'URL_dispatch': "http://tandtwstest.sfda.gov.sa:8080/ws/DispatchService/DispatchService",
            'HEADER': {'Content-Type': 'text/xml; charset=utf-8'},
            'USERNAME': '62864990000190000',
            'PASSWORD': 'Sameh_2021'
        }


    def sync_records(self):
        print('testing done method')
        if self.drug_list_sync:
            self.sync_druglist()
        if self.city_list_sync:
            self.sync_citylist()
        if self.stakeholder_list_sync:
            self.sync_stakeholder()
        if self.dispatch:
            self.create_dispatch()
        if self.upload_serial_number:
            self.upload_serial_numbers()
        if self.upload_products:
            self.upload_products_rsd()


    def upload_products_rsd(self):
        print('upload_products_rsd')
        wb = open_workbook(file_contents=base64.decodestring(self.upload_products))
        for s in wb.sheets():
            cols = s.ncols
            purchase_order = self.env['purchase.order'].create({'origin': 'RSD', 'rsd_import_purchase': True, 'partner_id': 1})
            serial_batch_list = []
            for row in range(2, s.nrows):
                print('testing loop')
                product_template = self.env['product.template'].search([('gtin', '=', str(s.cell_value(row, 0)))], limit=1)
                product_product = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
                if product_product:
                    serial_rec = self.env['stock.production.lot'].search([('name', '=', str(s.cell_value(row, 1))), ('product_id', '=', product_product.id)], limit=1)
                    if serial_rec:
                        exp_date = s.cell_value(row, 3).replace('.', '-')
                        date_obj = datetime.strptime(exp_date, '%d-%m-%Y')
                        new_format = date_obj.strftime('%Y-%m-%d')
                        serial_batch_dict = {
                            'serial_no': serial_rec.name,
                            'batch_no': str(s.cell_value(row, 2)),
                            'expiry_date': new_format
                        }
                        serial_batch_list.append(serial_batch_dict)
                        serial_record = self.env['serial.record'].create(
                            {'product_id': product_product.id,
                             'product_gtin': product_template.gtin,
                             'expiry_date': new_format,
                             'product_serial_number': serial_rec.name,
                             'product_batch_number': str(s.cell_value(row, 2)),
                             'product_status': 'Not Sold'})
                    else:
                        serial_number = self.env['stock.production.lot'].create({'name': str(s.cell_value(row, 1)),
                                                                                 'product_id': product_product.id,
                                                                                 'company_id': 1,
                                                                                 })
                        exp_date = s.cell_value(row, 3).replace('.', '-')
                        date_obj = datetime.strptime(exp_date, '%d-%m-%Y')
                        new_format = date_obj.strftime('%Y-%m-%d')
                        serial_batch_dict = {
                            'serial_no': serial_number.name,
                            'batch_no': str(s.cell_value(row, 2)),
                            'expiry_date': new_format
                        }
                        serial_batch_list.append(serial_batch_dict)
                        serial_record = self.env['serial.record'].create(
                            {'product_id': product_product.id,
                             'product_gtin': product_template.gtin,
                             'expiry_date': new_format,
                             'product_serial_number': serial_number.name,
                             'product_batch_number': str(s.cell_value(row, 2)),
                             'product_status': 'Not Sold'})
                    values = {
                        'product_id': product_product.id,
                        'product_qty': 1,
                        'order_id': purchase_order.id
                    }
                    purchase_line = self.env['purchase.order.line'].create(values)
            purchase_order.button_confirm()
            print('testing')
            purchase_order.picking_ids.non_portal = True
            counter = 0
            for line in purchase_order.picking_ids.move_ids_without_package:
                line.quantity_done = line.product_uom_qty
                line.lot_bn = serial_batch_list[counter].get('batch_no')
                line.ser_num = serial_batch_list[counter].get('serial_no')
                line.product_expiry = serial_batch_list[counter].get('expiry_date')
                counter += 1
            purchase_order.picking_ids.action_assign()
            purchase_order.picking_ids.button_validate()
            print('test')






    def upload_serial_numbers(self):
        print('testing')
        wb = open_workbook(file_contents=base64.decodestring(self.upload_serial_number))
        for s in wb.sheets():
            print('testing')
            print(s.cell_value(0,0))
            cols = s.ncols
            for row in range(1, s.nrows):
                sserial_number = self.env['stock.production.lot'].create({'name': int(s.cell_value(row, 0)),
                                                      'product_id': int(s.cell_value(row, 1)),
                                                      'company_id': int(s.cell_value(row, 2)),
                                                      })



    def sync_stakeholder(self):
        print('testing')
        request_vals = self.create_request_vals()
        city_id = (self.stakeholder_cityid) if self.stakeholder_cityid else ""
        body= "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:stak=\"http://dtts.sfda.gov.sa/StakeholderListService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <stak:StakeholderListServiceRequest>\n         <STAKEHOLDERTYPE>"+str(self.stakeholder_type)+"</STAKEHOLDERTYPE>\n         <GETALL>"+str(self.stakeholder_getall)+"</GETALL>\n         <!--Optional:-->\n         <CITYID>"+city_id+"</CITYID>\n      </stak:StakeholderListServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
        # body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:stak=\"http://dtts.sfda.gov.sa/StakeholderListService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <stak:StakeholderListServiceRequest>\n         <STAKEHOLDERTYPE>"+str(self.stakeholder_type)+"</STAKEHOLDERTYPE>\n         <GETALL>"+str(self.stakeholder_getall)+"</GETALL>\n         <!--Optional:-->\n         \n      </stak:StakeholderListServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
        response = requests.request("POST", request_vals.get('URL_stakeholderlist'), headers=request_vals.get('HEADER'),
                                    data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
        print(response.text)
        if response.status_code == 200:
            response_dict = xmltodict.parse(response.text)
            print(response_dict)
            print('status code 200')
            if response_dict.get('S:Envelope').get('S:Body').get('ns2:StakeholderListServiceResponse').get('STAKEHOLDERLIST').get('STAKEHOLDER'):
                for stakeholder in response_dict.get('S:Envelope').get('S:Body').get('ns2:StakeholderListServiceResponse').get('STAKEHOLDERLIST').get('STAKEHOLDER'):
                    stakeholder_obj = self.env['res.partner'].search([('gln', '=', stakeholder.get('GLN'))])
                    if not stakeholder_obj:
                        stakeholder.get('STAKEHOLDERNAME')
                        city_id = self.env['ksa.city'].search([('ksa_city_name', '=', stakeholder.get('CITYNAME'))])
                        new_stakeholder = self.env['res.partner'].create({
                            'name': stakeholder.get('STAKEHOLDERNAME'),
                            'gln': stakeholder.get('GLN'),
                            'city': city_id.ksa_city_name if city_id else '',
                            'state_id': city_id.region_id.id if city_id else False,
                            'street': stakeholder.get('ADDRESS'),
                            'company_type': 'person'
                        })
                        print(new_stakeholder.name)


    def sync_citylist(self):
        request_vals = self.create_request_vals()
        body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:cit=\"http://dtts.sfda.gov.sa/CityListService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <cit:CityListServiceRequest/>\n   </soapenv:Body>\n</soapenv:Envelope>"
        response = requests.request("POST", request_vals.get('URL_citylist'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
        print(response.text)
        if response.status_code == 200:
            print('status code 200')
            country_obj = self.env['res.country'].search([('name', '=', 'Saudi Arabia')])
            if response.text:
                response_dict = xmltodict.parse(response.text)
                print(response_dict)
                if response_dict.get('S:Envelope').get('S:Body').get('ns2:CityListServiceResponse').get('REGIONLIST').get('REGION'):
                    for region in response_dict.get('S:Envelope').get('S:Body').get('ns2:CityListServiceResponse').get('REGIONLIST').get('REGION'):
                        region_obj = self.env['res.country.state'].search([('name', '=', region.get('REGIONNAME'))])
                        if region_obj:
                            for city in region.get('CITYLIST').get('CITY'):
                                city_obj = self.env['ksa.city'].search(
                                    [('ksa_city_name', '=', city.get('CITYNAME'))])
                                # city_obj = self.env['ksa.city'].search([('ksa_city_name', '=', city.get('CITYNAME').replace("'",""))])
                                if not city_obj:
                                    new_city = self.env['ksa.city'].create(
                                                                        {'ksa_city_name': city.get('CITYNAME'),
                                                                         'ksa_city_id': city.get('CITYID'),
                                                                         'region_id': region_obj.id
                                                                         })
                        else:
                            new_region = self.env['res.country.state'].create(
                                {'country_id': country_obj.id,
                                 'name': region.get('REGIONNAME'),
                                 'code': region.get('REGIONNAME'),
                                 'region_id': region.get('REGIONID')
                                 })
                            city_list = region.get('CITYLIST').get('CITY')
                            if type(city_list) == list:
                                for city in city_list:
                                    city_obj = self.env['ksa.city'].search(
                                        [('ksa_city_name', '=', city.get('CITYNAME'))])
                                    # city_obj = self.env['ksa.city'].search([('ksa_city_name', '=', city.get('CITYNAME').replace("'",""))])
                                    if not city_obj:
                                        if city.get('CITYNAME') == 'Tayma':
                                            print('testing')
                                        print(city.get('CITYNAME'))
                                        new_city = self.env['ksa.city'].create(
                                                                            {'ksa_city_name': city.get('CITYNAME'),
                                                                             'ksa_city_id': city.get('CITYID'),
                                                                             'region_id': new_region.id
                                                                             })
                                        print('record created' + city.get('CITYNAME'))
                            else:
                                city_obj = self.env['ksa.city'].search(
                                    [('ksa_city_name', '=', city_list.get('CITYNAME'))])
                                # city_obj = self.env['ksa.city'].search([('ksa_city_name', '=', city.get('CITYNAME').replace("'",""))])
                                if not city_obj:
                                    if city_list.get('CITYNAME') == 'Tayma':
                                        print('testing')
                                    print(city_list.get('CITYNAME'))
                                    new_city = self.env['ksa.city'].create(
                                        {'ksa_city_name': city_list.get('CITYNAME'),
                                         'ksa_city_id': city_list.get('CITYID'),
                                         'region_id': new_region.id
                                         })
                                    print('record created' + city.get('CITYNAME'))


    def sync_druglist(self):
        request_vals = self.create_request_vals()
        body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:drug=\"http://dtts.sfda.gov.sa/DrugListService\">\n    <soapenv:Header/>\n    <soapenv:Body>\n        <drug:DrugListServiceRequest>\n            <DRUGSTATUS>"+self.drug_status+"</DRUGSTATUS>\n        </drug:DrugListServiceRequest>\n    </soapenv:Body>\n</soapenv:Envelope>"
        response = requests.request("POST", request_vals.get('URL_druglist'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
        print(response.text)
        if response.status_code == 200:
            print('status code 200')
            if response.text:
                response_dict = xmltodict.parse(response.text)
                print(response_dict)
                if response_dict.get('S:Envelope').get('S:Body').get('ns2:DrugListServiceResponse').get('DRUGLIST').get('DRUG'):
                    drug_list = response_dict.get('S:Envelope').get('S:Body').get('ns2:DrugListServiceResponse').get('DRUGLIST').get('DRUG')
                    all_products_gtn = self.env['product.template'].search_read([('id', '!=', 0)], fields=['gtin'])
                    available_products_gtn = [x for x in all_products_gtn if x.get('gtin') != '']
                    product_count = self.create_product(drug_list, available_products_gtn)
                    print(str(product_count) + ' new products created.')




class BatchNumber(models.Model):
    _name = 'batch.number'

    product_id = fields.Many2one('product.product')
    expiry_date = fields.Date('Expiry Date')
    batch_number = fields.Char('Batch Number')
    product_count = fields.Integer('Product Count', default=0)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        rec = super(StockMove, self).create(vals_list)
        for line in rec:
            if line.picking_type_id.name == 'Delivery Orders':
                batch_record = self.env['batch.number'].search([('product_id', '=', line.product_id.id), ('product_count', '>', 0)], order='create_date ASC', limit=1)
                line.lot_bn = batch_record.batch_number
                line.product_expiry = batch_record.expiry_date
                batch_record.product_count = batch_record.product_count - line.product_uom_qty
        return rec



    def write(self, vals):
        result = super(StockMove, self).write(vals)
        print('testing')
        lot_bn = False
        expiry_date = False
        if 'lot_bn' in vals.keys():
            lot_bn = vals.get('lot_bn')
        if 'product_expiry' in vals.keys():
            expiry_date = vals.get('product_expiry')
        if lot_bn:
            batch_rec = self.env['batch.number'].create({
                'product_id': self.product_id.id,
                'expiry_date': expiry_date,
                'batch_number': lot_bn,
                'product_count': self.product_uom_qty
            })
        return result
