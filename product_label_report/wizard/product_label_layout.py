# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'
    
    print_format = fields.Selection([
        ('dymo', 'Etiquetas'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price')], string="Format", default='dymo', required=True)
