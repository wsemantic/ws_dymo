# -*- coding: utf-8 -*-

from odoo import fields, models 

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    attribute_type = fields.Selection([('size', 'Size'), ('color', 'Color')])
