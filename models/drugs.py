# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode = fields.Char('Barcode', compute='_compute_barcode', inverse='_set_barcode', search='_search_barcode')
    name = fields.Char(string='Drug Name', index=True, required=True, translate=False)

    is_importable = fields.Boolean(string="Imported", default=False)
    is_exportable = fields.Boolean(string="Exportable", default=False)
    drug_status = fields.Selection(string='Status', selection=[('-1', 'All'), ('0', 'Active'), ('1', 'Passive')])
    hospital_use = fields.Selection(string="For Only Hospital", selection=[('no', 'No'), ('yes', 'Yes')], default='no')
    legal_status = fields.Integer(string='Legal Status')
    domain_id = fields.Integer(string='Domain ID')
    gtin = fields.Char(string='GTIN',)
    dispatch_sn = fields.Char(string='Dispatch Serial Number')
    dispatch_bn = fields.Char(string='Dispatch Batch Number')
    purchase_price = fields.Float(string='Purchase Price')
    purchase_discount = fields.Float(string='Purchase Discount')



class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        print('testing create')
        rec = super(PurchaseOrderLine, self).create(vals_list)
        for val in rec:
            val.price_unit = val.product_id.product_tmpl_id.purchase_price
#            val.discount = val.product_id.product_tmpl_id.purchase_discount
        return rec


#class AccountMoveLine(models.Model):
#    _inherit = "account.move.line"

#    @api.model_create_multi
#    def create(self, vals_list):
#        print('testing create for account move line')
#        rec = super(AccountMoveLine, self).create(vals_list)
#        for val in rec:
#            val.discount = val.product_id.product_tmpl_id.purchase_discount
#        return rec


