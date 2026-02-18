# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('name', 'default_code', 'product_template_attribute_value_ids')
    @api.depends_context('display_default_code')
    def _compute_display_name(self):
        # Migrado de name_get() (v16) a _compute_display_name() (v18)
        for product in self:
            # We extract the base name that would normally include the code and product name.
            # For example: "[ABC] Product X"
            name = product.name or ''

            # Add product code if it should be displayed
            if self._context.get('display_default_code', True) and product.default_code:
                name = "[%s] %s" % (product.default_code, name)

            # Get all attribute values, without filtering if they are unique or not.
            attribute_values = product.product_template_attribute_value_ids.mapped('name')
            if attribute_values:
                # Concatenate all attributes (you can change the comma to another separator if you want)
                combo = ", ".join(attribute_values)
                # Concatenate the base name with the attributes between parentheses
                product.display_name = "%s (%s)" % (name, combo)
            else:
                product.display_name = name