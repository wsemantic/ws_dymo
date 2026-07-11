# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection([
        ('dymo', 'Etiquetas'),
        ('2x7xprice', '2 x 7 with price'),
        ('4x7xprice', '4 x 7 with price'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 with price')], string="Format", default='dymo', required=True)
    use_stock_quantity = fields.Boolean(string="Usar cantidad de stock", default=False)
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Almacén",
        default=lambda self: self._get_default_warehouse(),
        domain="[('company_id', '=', company_id)]",
        check_company=True,
    )

    @api.model
    def _get_default_warehouse(self):
        company = self.env.company
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', company.id)
        ], limit=1)
        if not warehouse:
            warehouse = self.env['stock.warehouse'].search([], limit=1)
        return warehouse.id

    def _get_product_stock_quantity(self, product):
        self.ensure_one()
        if not self.use_stock_quantity:
            return 0
        ctx = {
            'warehouse': self.warehouse_id.id if self.warehouse_id else False,
            'company_id': self.company_id.id if self.company_id else False,
            'allowed_company_ids': self.company_id.ids if self.company_id else self.env.companies.ids,
        }
        product_ctx = product.with_context(**{k: v for k, v in ctx.items() if v})
        quantity = product_ctx.qty_available
        return max(int(round(quantity)), 0)
