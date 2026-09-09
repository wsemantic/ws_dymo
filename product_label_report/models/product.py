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

class ProductLabelNameFit(models.AbstractModel):
    """Cuantas lineas ocupa el nombre en la etiqueta Dymo.

    Solo calcula ALTO: el cuerpo es siempre el mismo. Hubo escalones que
    encogian la fuente para meter mas texto en el mismo hueco, pero obligaban a
    una tabla de umbrales y a resolver una circularidad -los caracteres por
    linea dependen del cuerpo y el cuerpo de las lineas- que no compensaba.

    El alto se reserva en vez de dejar crecer al div porque el nombre vive
    dentro de un td: en wkhtmltopdf, max-height + overflow no recorta de forma
    fiable dentro de una celda y el sobrante se monta sobre el precio (ver
    README, caminos descartados).

    El conteo simula el ajuste real -greedy por palabras, partiendo la palabra
    que no quepa, que es lo que hace word-wrap:break-word-, no la longitud
    total del texto: un nombre de 26 caracteres con palabras largas se va a
    tres lineas aunque por longitud parezcan dos.
    """
    _name = 'product.label.name.fit'
    _description = 'Ajuste del nombre en la etiqueta'

    # Caracteres por linea del ancho de SU columna (65% ~ 34mm), no del ancho
    # de la etiqueta: si se cambia el width del td hay que rehacer este numero.
    # El limite de la columna de al lado no es el codigo -va a .6em y sobra
    # sitio- sino la talla, que es nowrap a 3.4em: si se le quita ancho no se
    # parte, desborda, y vuelve a disparar el encogimiento de wkhtmltopdf.
    _LABEL_NAME_CHARS_PER_LINE = 15
    # Techo del presupuesto vertical: mas lineas empujarian la linea del color
    # fuera del rollo. Pasado el techo se recorta, que es el mal menor.
    _LABEL_NAME_MAX_LINES = 3
    _LABEL_NAME_LINE_HEIGHT = 1.05

    @api.model
    def _label_name_line_count(self, text, chars_per_line):
        """Lineas que ocupa `text` partido a `chars_per_line` caracteres."""
        lines = 0
        current = 0
        for word in (text or '').split():
            # Palabra mas ancha que la columna: break-word la corta donde llega,
            # sin guion, y consume una linea entera por cada trozo.
            while len(word) > chars_per_line:
                if current:
                    lines += 1
                    current = 0
                lines += 1
                word = word[chars_per_line:]
            if not word:
                continue
            needed = len(word) if not current else current + 1 + len(word)
            if needed <= chars_per_line:
                current = needed
            else:
                lines += 1
                current = len(word)
        if current:
            lines += 1
        return max(lines, 1)

    @api.model
    def _label_name_height(self, text):
        """Alto en em a reservar para el nombre, con el techo aplicado."""
        lines = self._label_name_line_count(text, self._LABEL_NAME_CHARS_PER_LINE)
        lines = min(lines, self._LABEL_NAME_MAX_LINES)
        return round(lines * self._LABEL_NAME_LINE_HEIGHT, 2)
