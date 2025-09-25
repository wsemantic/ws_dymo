# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError

def _prepare_custom_data(env, data):
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    total = 0
    qty_by_product_in = data.get('quantity_by_product') or {}
    # search for products all at once, ordered by name desc since popitem() used in xml to print the labels
    # is LIFO, which results in ordering by product name in the report
    product_ids = [int(p) for p in qty_by_product_in.keys()]
    if not product_ids:
        product_ids = [int(p) for p in data.get('product_ids', [])] or [int(p) for p in data.get('product_tmpl_ids', [])]
    products = Product.search([('id', 'in', product_ids)], order='name asc, barcode asc') if product_ids else Product.browse()
    quantity_by_product = defaultdict(list)
    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if not layout_wizard:
        return {}
    use_stock_quantity = layout_wizard.use_stock_quantity if layout_wizard else False
    for product in products:
        if use_stock_quantity:
            q = layout_wizard._get_product_stock_quantity(product)
        else:
            q = qty_by_product_in.get(str(product.id), 0)
        if q <= 0:
            continue
        quantity_by_product[product].append((product.barcode, q))
        total += q
    if data.get('custom_barcodes'):
        # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
        for product, barcodes_qtys in data.get('custom_barcodes').items():
            quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
            total += sum(qty for _, qty in barcodes_qtys)

    return {
        'quantity': quantity_by_product,
        'rows': layout_wizard.rows,
        'columns': layout_wizard.columns,
        'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
    }

class ReportProductTemplateLabel(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, data)

class ReportProductTemplateLabelDymo(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel_dymo'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, data)
