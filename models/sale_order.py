# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests
import xmltodict, json


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    dispatch_sn = fields.Char(string='Dispatch Serial Number')
    dispatch_bn = fields.Char(string='Dispatch Batch Number')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dispatch_notification_id = fields.Integer(string='Dispatch Notification ID')
    dispatch_cancel_notification_id = fields.Integer(string='Dispatch Cancel Notification ID')
    dispatch_expiry = fields.Date(string='Dispatch Expiry')



    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        print('developing on action confirm')
        # self.env['stock.move.line'].create(move_line_vals_list)
        for line in self.picking_ids.move_ids_without_package:
            if line.product_uom_qty > 1:
                items = line.product_uom_qty
                line.product_uom_qty = 1
                for x in range(int(items)-1):
                    line.copy()

                    print(x)
        for line in self.picking_ids.move_ids_without_package:

            serial_record = self.env['serial.record'].search([('product_id', '=', line.product_id.id),
                                                              ('product_status', '=', 'Not Sold')], order='create_date asc',
                                                             limit=line.product_qty)
            if serial_record:
                line.lot_bn = serial_record[0].product_batch_number
                line.ser_num = serial_record[0].product_serial_number
                line.product_expiry = serial_record[0].expiry_date
                self.picking_ids.product_info_move_lines = [(0, 0, {'product_id': line.product_id.id,
                                                                    'product_serial_number': line.ser_num,
                                                                    'product_expiry': line.product_expiry,
                                                                    'product_qty': line.product_uom_qty,
                                                                    'product_batch_number': line.lot_bn,
                                                                    'picking_id': self.id,
                                                                    'serial_track': serial_record.id})]

                for serial in serial_record:
                    serial.product_status = 'Sold'
        return res

    # picking.write({
    #     'move_line_ids': [(0, 0, {
    #         'product_id': self.productB.id,
    #         'product_uom_qty': 7.0,
    #         'qty_done': 7.0,
    #         'product_uom_id': self.productB.uom_id.id,
    #         'location_id': self.customer_location.id,
    #         'location_dest_id': shelf2_location.id,
    #         'picking_id': picking.id,
    #         'state': 'confirmed',
    #     })]
    # })


    def create_request_vals(self):
        return {
            'URL_druglist': "http://tandtwstest.sfda.gov.sa:8080/ws/DrugListService/DrugListService",
            'URL_citylist': "http://tandtwstest.sfda.gov.sa:8080/ws/CityListService/CityListService",
            'URL_stakeholderlist': "http://tandtwstest.sfda.gov.sa:8080/ws/StakeholderListService/StakeholderListService",
            'URL_dispatch': "http://tandtwstest.sfda.gov.sa:8080/ws/DispatchService/DispatchService",
            'URL_dispatchcancel': "http://tandtwstest.sfda.gov.sa:8080/ws/DispatchCancelService/DispatchCancelService",
            'HEADER': {'Content-Type': 'text/xml; charset=utf-8'},
            'USERNAME': '62864990000190000',
            'PASSWORD': 'Sameh_2021'
        }


    # def action_confirm(self):
    #     res = super(SaleOrder, self).action_confirm()
    #     print('developing on action confirm')
    #     request_vals = self.create_request_vals()
    #     product_list = ''
    #     for product in self.order_line:
    #         product_list += "<PRODUCT>\n<GTIN>" + product.product_id.product_tmpl_id.gtin + "</GTIN>\n<SN>" + product.dispatch_sn + "</SN>\n <!--Optional: -->\n <BN>" + product.dispatch_bn + "</BN>\n <!--Optional: -->\n <XD>" + str(self.dispatch_expiry) + "</XD>\n </PRODUCT>\n"
    #     # product_list = "<PRODUCTLIST>\n            <!--1 or more repetitions:-->\n            <PRODUCT>\n               <GTIN>" + self.dispatch_gtin + "</GTIN>\n               <SN>" + self.dispatch_sn + "</SN>\n               <!--Optional:-->\n               <BN>" + self.dispatch_batch + "</BN>\n               <!--Optional:-->\n               <XD>" + str(self.dispatch_expiry) + "</XD>\n            </PRODUCT>\n         </PRODUCTLIST>\n"
    #     body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchServiceRequest>\n         <TOGLN>" + self.partner_id.gln + "</TOGLN>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n"+product_list+"</PRODUCTLIST>\n      </dis:DispatchServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
    #     response = requests.request("POST", request_vals.get('URL_dispatch'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
    #     print(response.text)
    #     if response.status_code == 200:
    #         response_dict = xmltodict.parse(response.text)
    #         print(response_dict)
    #         print('status code 200')
    #         if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID'):
    #             notification_id = response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID')
    #             self.dispatch_notification_id = int(notification_id)
    #     return True


    # def action_cancel(self):
    #     print('developing dipatch cancel')
    #     request_vals = self.create_request_vals()
    #     product_list = ''
    #     for product in self.order_line:
    #         product_list += "<PRODUCT>\n<GTIN>" + product.product_id.product_tmpl_id.gtin + "</GTIN>\n<SN>" + product.dispatch_sn + "</SN>\n <!--Optional: -->\n <BN>" + product.dispatch_bn + "</BN>\n <!--Optional: -->\n <XD>" + str(self.dispatch_expiry) + "</XD>\n </PRODUCT>\n"
    #     # product_list = "<PRODUCTLIST>\n            <!--1 or more repetitions:-->\n            <PRODUCT>\n               <GTIN>" + self.dispatch_gtin + "</GTIN>\n               <SN>" + self.dispatch_sn + "</SN>\n               <!--Optional:-->\n               <BN>" + self.dispatch_batch + "</BN>\n               <!--Optional:-->\n               <XD>" + str(self.dispatch_expiry) + "</XD>\n            </PRODUCT>\n         </PRODUCTLIST>\n"
    #     body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchCancelService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchCancelServiceRequest>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n" + product_list + "</PRODUCTLIST>\n      </dis:DispatchCancelServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
    #     response = requests.request("POST", request_vals.get('URL_dispatchcancel'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
    #     print(response.text)
    #     if response.status_code == 200:
    #         response_dict = xmltodict.parse(response.text)
    #         print(response_dict)
    #         print('status code 200')
    #         if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchCancelServiceResponse').get('NOTIFICATIONID'):
    #             notification_id = response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchCancelServiceResponse').get('NOTIFICATIONID')
    #             self.dispatch_cancel_notification_id = int(notification_id)
    #     return super(SaleOrder, self).action_cancel()

