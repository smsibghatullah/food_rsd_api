from odoo import models, fields, api

class ProductTemplate(models.Model):
    _name = 'product.info'

    product_id = fields.Many2one('product.product', string='Product ID')
    picking_id = fields.Many2one(
        'stock.picking', 'Transfer', auto_join=True,
        check_company=True,
        index=True,
        help='The stock operation where the packing has been made')

    product_serial_number = fields.Char(string='Product Serial Number')
    product_expiry = fields.Date(string='Expiry Date')
    product_qty = fields.Float(string='Quantity')
    product_batch_number = fields.Char(string='Batch Number')
    serial_track = fields.Many2one('serial.record', string='Serial Record ID')
