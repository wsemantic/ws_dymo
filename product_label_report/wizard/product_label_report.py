# -*- coding: utf-8 -*-

from collections import defaultdict
import logging

from odoo import _, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


def _resolve_barcode(product):
    """Return a printable barcode for both templates and variants."""
    barcode = product.barcode
    if barcode:
        return barcode

    if product._name == 'product.template':
        variant_with_barcode = product.product_variant_ids.filtered('barcode')[:1]
        resolved = variant_with_barcode.barcode if variant_with_barcode else False
        if resolved:
            _logger.info(
                "Label barcode fallback for template %s (%s) -> variant barcode %s",
                product.display_name,
                product.id,
                resolved,
            )
        return resolved

    return False


def _prepare_custom_data(env, docids, data):
    _logger.info(
        "Preparing label data | active_model=%s, docids=%s, custom_barcodes=%s",
        data.get('active_model'),
        docids,
        bool(data.get('custom_barcodes')),
    )
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    elif data.get("studio") and docids:
        products = env['product.template'].with_context(display_default_code=False).browse(docids)
        quantity_by_product = defaultdict(list)
        for product in products:
            quantity_by_product[product].append((_resolve_barcode(product), 1))
        return {
            'quantity': quantity_by_product,
            'page_numbers': 1,
            'pricelist': layout_wizard.pricelist_id,
        }
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    total = 0
    qty_by_product_in = data.get('quantity_by_product') or {}
    # search for products all at once, ordered by name desc since popitem() used in xml to print the labels
    # is LIFO, which results in ordering by product name in the report
    product_ids = [int(p) for p in qty_by_product_in.keys()]
    if not product_ids:
        product_ids = [int(p) for p in data.get('product_ids', [])] or [int(p) for p in data.get('product_tmpl_ids', [])]
    products = Product.search([('id', 'in', product_ids)], order='name asc') if product_ids else Product.browse()
    quantity_by_product = defaultdict(list)
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
        resolved_barcode = _resolve_barcode(product)
        if not resolved_barcode:
            _logger.warning(
                "No barcode resolved for product %s (%s) in main label loop",
                product.display_name,
                product.id,
            )
        quantity_by_product[product].append((resolved_barcode, q))
        total += q
    if data.get('custom_barcodes'):
        # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
        for product, barcodes_qtys in data.get('custom_barcodes').items():
            product_record = Product.browse(int(product))
            fallback_barcode = _resolve_barcode(product_record)
            normalized_barcodes_qtys = [
                (barcode or fallback_barcode, qty)
                for barcode, qty in barcodes_qtys
            ]
            if not fallback_barcode and any(not barcode for barcode, _ in barcodes_qtys):
                _logger.warning(
                    "Empty custom barcode and no fallback for product %s (%s)",
                    product_record.display_name,
                    product_record.id,
                )
            quantity_by_product[product_record] += normalized_barcodes_qtys
            total += sum(qty for _, qty in normalized_barcodes_qtys)

    return {
        'quantity': quantity_by_product,
        'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
        'pricelist': layout_wizard.pricelist_id,
    }

class ReportProductTemplateLabel2x7(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel2x7'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, docids, data)

class ReportProductTemplateLabel4x7(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel4x7'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, docids, data)

class ReportProductTemplateLabel4x12(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel4x12'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, docids, data)

class ReportProductTemplateLabel4x12NoPrice(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel4x12noprice'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, docids, data)

class ReportProductTemplateLabelDymo(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel_dymo'

    def _get_report_values(self, docids, data):
        return _prepare_custom_data(self.env, docids, data)
