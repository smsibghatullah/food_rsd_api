
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from itertools import groupby
import requests
import xmltodict, json



class Picking(models.Model):
    _inherit = "stock.picking"

    dispatch_notification_id = fields.Integer(string='Dispatch Notification ID')
    dispatch_cancel_notification_id = fields.Integer(string='Dispatch Cancel Notification ID')
    dispatch_expiry = fields.Date(string='Dispatch Expiry')
    non_portal = fields.Boolean(string='Non Portal')
    dispatch_check = fields.Boolean(string='Dispatch Check')
    product_info_move_lines = fields.One2many('product.info', 'picking_id', string="Product Information", copy=True)


    def create_request_vals(self):
        return {
            'URL_druglist': "http://tandtwstest.sfda.gov.sa:8080/ws/DrugListService/DrugListService",
            'URL_citylist': "http://tandtwstest.sfda.gov.sa:8080/ws/CityListService/CityListService",
            'URL_stakeholderlist': "http://tandtwstest.sfda.gov.sa:8080/ws/StakeholderListService/StakeholderListService",
            'URL_dispatch': "http://tandtwstest.sfda.gov.sa:8080/ws/DispatchService/DispatchService",
            'URL_dispatchcancel': "http://tandtwstest.sfda.gov.sa:8080/ws/DispatchCancelService/DispatchCancelService",
            'URL_accept': "http://tandtwstest.sfda.gov.sa:8080/ws/AcceptService/AcceptService",
            'HEADER': {'Content-Type': 'text/xml; charset=utf-8'},
            'USERNAME': '62864990000190000',
            'PASSWORD': 'Sameh_2021'
        }


    def action_cancel(self):
        for item in self.product_info_move_lines:
            item.serial_track.product_status='Not Sold'

        request_vals = self.create_request_vals()
        product_list = ''
        for product in self.move_ids_without_package:
            if product.product_id.product_tmpl_id.gtin and product.ser_num and product.lot_bn and product.product_expiry:
                product_list += "<PRODUCT>\n<GTIN>" + str(product.product_id.product_tmpl_id.gtin) + "</GTIN>\n<SN>" + str(product.ser_num) + "</SN>\n <!--Optional: -->\n <BN>" + product.lot_bn + "</BN>\n <!--Optional: -->\n <XD>" + str(product.product_expiry) + "</XD>\n </PRODUCT>\n"
                #product_list += "<PRODUCT>\n<GTIN>" + str(product.product_id.product_tmpl_id.gtin) + "</GTIN>\n<SN>" + str(product.dispatch_sn) + "</SN>\n <!--Optional: -->\n <BN>" + product.dispatch_bn + "</BN>\n <!--Optional: -->\n <XD>" + str(self.dispatch_expiry) + "</XD>\n </PRODUCT>\n"
        body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchCancelService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchCancelServiceRequest>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n" + product_list + "</PRODUCTLIST>\n      </dis:DispatchCancelServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
        response = requests.request("POST", request_vals.get('URL_dispatchcancel'), headers=request_vals.get('HEADER'), data=body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
        print(response.text)
        if response.status_code == 200:
            response_dict = xmltodict.parse(response.text)
            print(response_dict)
            print('status code 200')
            if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchCancelServiceResponse').get('NOTIFICATIONID'):
                notification_id = response_dict.get('S:Envelope').get('S:Body').get(
                    'ns2:DispatchCancelServiceResponse').get('NOTIFICATIONID')
                self.dispatch_cancel_notification_id = int(notification_id)
        return super(Picking, self).action_cancel()


    def button_validate(self):
        res = super(Picking, self).button_validate()
        if not self.non_portal and res==True:
            request_vals = self.create_request_vals()
            product_list = ''
            if self.picking_type_id:
                picking_type = self.env['stock.picking.type'].search([('id', '=', self.picking_type_id.id)])
                if picking_type and picking_type.sequence_code == 'IN':
                    for product in self.move_ids_without_package:
                        if product.product_id.product_tmpl_id.gtin and product.ser_num and product.lot_bn and product.product_expiry:
                            product_list += "<PRODUCT>\n<GTIN>" + product.product_id.product_tmpl_id.gtin + "</GTIN>\n<SN>" + product.ser_num + "</SN>\n <!--Optional: -->\n <BN>" + product.lot_bn + "</BN>\n <!--Optional: -->\n <XD>" + str(product.product_expiry) + "</XD>\n </PRODUCT>\n"
                        else:
                            raise UserError('Some required values missing.')


                    in_body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:acc=\"http://dtts.sfda.gov.sa/AcceptService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <acc:AcceptServiceRequest>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n " + product_list + "</PRODUCTLIST>\n      </acc:AcceptServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
                    if not self.dispatch_check:
                        response = requests.request("POST", request_vals.get('URL_accept'),
                                                    headers=request_vals.get('HEADER'), data=in_body,
                                                    auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
                        if response.status_code == 200:
                            self.dispatch_check = True
                            response_dict = xmltodict.parse(response.text)
                            print(response_dict)
                            print('status code 200')
                            print('successfull accept')
                            if response_dict.get('S:Envelope').get('S:Body').get('ns2:AcceptServiceResponse').get(
                                    'NOTIFICATIONID'):
                                notification_id = response_dict.get('S:Envelope').get('S:Body').get(
                                    'ns2:AcceptServiceResponse').get('NOTIFICATIONID')
                                self.dispatch_notification_id = int(notification_id)
            if self.picking_type_id:
                picking_type = self.env['stock.picking.type'].search([('id', '=', self.picking_type_id.id)])
                if picking_type and picking_type.sequence_code == 'OUT':
                    product_done_qty = {}
                    for item in self.move_line_ids:
                        product_done_qty[item.product_id.id] = item.qty_done

                    product_sync = {}
                    for product_info in self.product_info_move_lines:
                        if product_info.product_id.id not in product_sync.keys():
                            product_sync[product_info.product_id.id] = 0


                        if product_info.product_id.id in product_sync.keys() and \
                            product_sync[product_info.product_id.id] < product_done_qty[product_info.product_id.id]:

                            product_sync[product_info.product_id.id] +=1
                            if product_info.product_id.product_tmpl_id.gtin and product_info.product_serial_number and product_info.product_batch_number and product_info.product_expiry:
                                product_list += "<PRODUCT>\n<GTIN>" + product_info.product_id.product_tmpl_id.gtin + "</GTIN>\n<SN>" + product_info.product_serial_number + "</SN>\n <!--Optional: -->\n <BN>" + product_info.product_batch_number + "</BN>\n <!--Optional: -->\n <XD>" + str(
                                    product_info.product_expiry) + "</XD>\n </PRODUCT>\n"
                            else:
                                raise UserError('Some required values missing.')

                    out_body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchServiceRequest>\n         <TOGLN>" + self.partner_id.gln + "</TOGLN>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n" + product_list + "</PRODUCTLIST>\n      </dis:DispatchServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
                    if not self.dispatch_check:
                        response = requests.request("POST", request_vals.get('URL_dispatch'), headers=request_vals.get('HEADER'), data=out_body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
                        if response.status_code == 200:
                            self.dispatch_check = True
                            response_dict = xmltodict.parse(response.text)
                            print(response_dict)
                            print('status code 200')
                            print('successfull dispatch')
                            if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID'):
                                notification_id = response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID')
                                self.dispatch_notification_id = int(notification_id)

        return res


#    def button_validate(self):
#        res = super(Picking, self).button_validate()
#        if not self.non_portal:
#            request_vals = self.create_request_vals()
#            product_list = ''
#            for product in self.move_ids_without_package:
#                if self.picking_type_id:
#                    picking_type = self.env['stock.picking.type'].search([('id', '=', self.picking_type_id.id)])
#                    if picking_type and picking_type.sequence_code == 'IN':
#                        for move_line in product.move_line_nosuggest_ids:
#                            # if product_quantity <= product.quantity_done:
#                            #     product_quantity += 1
#                            product_list += "<PRODUCT>\n<GTIN>" + str(product.product_id.product_tmpl_id.gtin) + "</GTIN>\n<SN>" + str(product.ser_num) + "</SN>\n <!--Optional: -->\n <BN>" + str(product.lot_bn) + "</BN>\n <!--Optional: -->\n <XD>" + str(
#                                product.product_expiry) + "</XD>\n </PRODUCT>\n"
#
#                        in_body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:acc=\"http://dtts.sfda.gov.sa/AcceptService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <acc:AcceptServiceRequest>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n " + product_list + "</PRODUCTLIST>\n      </acc:AcceptServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
#                        if not self.dispatch_check:
#                            response = requests.request("POST", request_vals.get('URL_accept'),
#                                                    headers=request_vals.get('HEADER'), data=in_body,
#                                                    auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
#                            
#                            if response.status_code == 200:
#                                self.dispatch_check = True
#                                response_dict = xmltodict.parse(response.text)
#                                print(response_dict)
#                                print('status code 200')
#                                print('successfull accept')
#                                if response_dict.get('S:Envelope').get('S:Body').get('ns2:AcceptServiceResponse').get(
#                                        'NOTIFICATIONID'):
#                                    notification_id = response_dict.get('S:Envelope').get('S:Body').get(
#                                        'ns2:AcceptServiceResponse').get('NOTIFICATIONID')
#                                    self.dispatch_notification_id = int(notification_id)
#                    elif picking_type and picking_type.sequence_code == 'OUT':
#                        for move_line in product.move_line_ids:
#                            product_list += "<PRODUCT>\n<GTIN>" + str(product.product_id.product_tmpl_id.gtin) + "</GTIN>\n<SN>" + str(product.ser_num) + "</SN>\n <!--Optional: -->\n <BN>" + str(product.lot_bn) + "</BN>\n <!--Optional: -->\n <XD>" + str(
#                                product.product_expiry) + "</XD>\n </PRODUCT>\n"
#
#                        out_body = "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\" xmlns:dis=\"http://dtts.sfda.gov.sa/DispatchService\">\n   <soapenv:Header/>\n   <soapenv:Body>\n      <dis:DispatchServiceRequest>\n         <TOGLN>" + self.partner_id.gln + "</TOGLN>\n         <PRODUCTLIST>\n            <!--1 or more repetitions:-->\n" + product_list + "</PRODUCTLIST>\n      </dis:DispatchServiceRequest>\n   </soapenv:Body>\n</soapenv:Envelope>"
#                        if not self.dispatch_check:
#                            response = requests.request("POST", request_vals.get('URL_dispatch'), headers=request_vals.get('HEADER'), data=out_body, auth=(request_vals.get('USERNAME'), request_vals.get('PASSWORD')))
#                            if response.status_code == 200:
#                                self.dispatch_check = True
#                                response_dict = xmltodict.parse(response.text)
#                                print(response_dict)
#                                print('status code 200')
#                                print('successfull dispatch')
#                                if response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID'):
#                                    notification_id = response_dict.get('S:Envelope').get('S:Body').get('ns2:DispatchServiceResponse').get('NOTIFICATIONID')
#                                    self.dispatch_notification_id = int(notification_id)
#
#        return res



class StockMove(models.Model):
    _inherit = "stock.move"

    dispatch_sn = fields.Char(string='Dispatch Serial Number')
    dispatch_bn = fields.Char(string='Dispatch Batch Number')
    product_expiry = fields.Date(string='Product Expiry')
    lot_bn = fields.Char(strinf='Batch Number')
    ser_num = fields.Char(string='Serial Number')


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    lot_bn = fields.Char(string='Dispatch Batch Number')

    @api.model_create_multi
    def create(self, values):
        res = super(StockMoveLine, self).create(values)
        for val in res:
            if not val.lot_bn:
                stock_move_line = self.env['stock.move.line'].search([('lot_id', '=', val.lot_id.id), ('lot_bn', '!=', '')], limit=1)
                if stock_move_line:
                    val.lot_bn = stock_move_line.lot_bn
        print('testing')
        return res



class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def set_discount(self):
        if self.product_id:
            sale_order_lines = self.env['sale.order.line'].search([('product_id', '=', self.product_id.id), ('order_partner_id', '=', self.order_partner_id.id)], order='create_date desc')
            if sale_order_lines:
                for order_line in sale_order_lines:
                    if order_line.discount > 0:
                        self.discount = order_line.discount
                        break


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"


    expiry_date = fields.Date(string='Expiry Date')
    batch_no = fields.Char(string='Batch No')
    discount_custom = fields.Float(string='Discount')


    @api.onchange('product_id')
    def set_vat(self):
        print('testing')
        vat_purchase = self.env['account.tax'].search([('name', '=', 'Vat Purchase'), ('type_tax_use', '=', 'purchase')], limit=1)
        vat_sale = self.env['account.tax'].search([('name', '=', 'Vat Sale'), ('type_tax_use', '=', 'sale')], limit=1)
        print('testing vats')


#
#     @api.model_create_multi
#     def create(self, vals):
#         val_dict = vals
#         for val in val_dict:
#             if val.get('product_id'):
#                 move_lines = self.env['account.move.line'].search(['&', ('product_id', '=', val.get('product_id')), ('partner_id', '=', val.get('partner_id'))], order='create_date desc')
#                 if move_lines:
#                     for line in move_lines:
#                         if line.product_id:
#                             if line.discount:
#                                 val['discount'] = line.discount
#                                 break
#         lines = super(AccountMoveLine, self).create(val_dict)
#         return lines

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"


    rsd_import_purchase = fields.Boolean(string='RSD Import Purchase', default=False)
    partner_id = fields.Many2one('res.partner', string='Vendor',
                                 change_default=True, tracking=True,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 help="You can find a vendor by its Name, TIN, Email or Internal Reference.")




    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1) Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
           

            counter = 0
            if order.origin == 'RSD':
                for line in order.order_line:
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                    if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                        if pending_section:
                            invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                            pending_section = None
                        invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
                        invoice_vals['invoice_line_ids'][counter][2].update({'discount': line.product_id.product_tmpl_id.purchase_discount})
                        counter += 1
                invoice_vals_list.append(invoice_vals)
            else:
                for line in order.order_line:
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                    if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                        if pending_section:
                            invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                            pending_section = None
                        invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
                invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
        new_list = []
        for picking in self.picking_ids:
            #new_list = []
            for move_line in picking.move_ids_without_package:
                new_dict = {
                    'expiry_date': move_line.product_expiry,
                    'batch_no': move_line.lot_bn
                }
                new_list.append(new_dict)
            break
        # vat_purchase = self.env['account.tax'].search([('name', '=', 'Vat Purchase'), ('type_tax_use', '=', 'purchase')], limit=1)
        for move in moves:
            counter = 0
            for line in move.invoice_line_ids:
                # if vat_purchase:
                #     line.tax_ids = [(4, vat_purchase.id)]
                line.expiry_date = new_list[counter].get('expiry_date')
                line.batch_no = new_list[counter].get('batch_no')
                counter += 1
        return self.action_view_invoice(moves)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"



    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param('sale.default_deposit_product_id', self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                amount, name = self._get_advance_details(order)

                if self.product_id.invoice_policy != 'order':
                    raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(lambda r: not order.company_id or r.company_id == order.company_id)
                tax_ids = order.fiscal_position_id.map_tax(taxes, self.product_id, order.partner_shipping_id).ids
                analytic_tag_ids = []
                for line in order.order_line:
                    analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]

                so_line_values = self._prepare_so_line(order, analytic_tag_ids, tax_ids, amount)
                so_line = sale_line_obj.create(so_line_values)
                self._create_invoice(order, so_line, amount)
        new_list = []
        for order in sale_orders:
            new_list = []
            for picking in order.picking_ids:
                #new_list = []
                for line in picking.move_ids_without_package:
                    new_dict = {
                        'expiry_date': line.product_expiry,
                        'batch_no': line.lot_bn
                    }
                    new_list.append(new_dict)
            break
        # vat_sale = self.env['account.tax'].search([('name', '=', 'Vat Sale'), ('type_tax_use', '=', 'sale')], limit=1)
        new_list = new_list
        for order in sale_orders:
            for invoice in order.invoice_ids:
                counter = 0
                for line in invoice.invoice_line_ids:
                    # if vat_sale:
                    #     line.tax_ids = [(4, vat_sale.id)]
                    if new_list:
                        line.expiry_date = new_list[counter].get('expiry_date')
                        line.batch_no = new_list[counter].get('batch_no')
                        counter += 1

        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}



