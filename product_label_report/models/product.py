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

    # Capacidad de una linea en "unidades de ancho", donde 1.0 es una minuscula
    # normal. No son caracteres: la fuente es proporcional y un conteo plano se
    # queda corto justo con las palabras anchas, que es cuando el texto se va a
    # una linea de mas y se recorta. Sale del ancho de SU columna (65% ~ 34mm):
    # si se cambia el width del td hay que rehacer este numero.
    # El limite de la columna de al lado no es el codigo -va a .6em y sobra
    # sitio- sino la talla, que es nowrap a 3.4em: si se le quita ancho no se
    # parte, desborda, y vuelve a disparar el encogimiento de wkhtmltopdf.
    # Calibrado con doc/Etiqueta tirantes sin econgimiento.pdf (rollo de 30mm,
    # Lato): "TIRANTES BOTONES" (19.2 unidades con los pesos de abajo) ocupa el
    # 90.5% de la columna medido con pdftotext -bbox, luego la columna real son
    # ~21.2 unidades; se deja un 3% por debajo para que el error, si lo hay,
    # sea reservar de mas y no que una linea sin reservar caiga sobre el
    # precio. El 18 anterior salia de una foto de "CAMISA HARPER" tomada con la
    # columna del nombre mas estrecha (antes de independizar las dos columnas)
    # y estimaba 3 lineas para nombres que el render hacia en 2.
    # Para recalibrar: generar el PDF sin encogimiento, pdftotext -bbox, y
    # dividir el ancho de una linea llena entre el ancho de la columna
    # (x del primer texto de la columna hasta ~154pt en pagina de 161pt).
    _LABEL_NAME_LINE_UNITS = 20.5
    # Anchos relativos aproximados a Helvetica, con la minuscula media (~0.52em)
    # como 1.0: mayuscula ~0.68em, digito ~0.56em, espacio ~0.28em. Solo hay
    # que ser mas fino que "todos igual": el error que importa es el de la
    # palabra ancha que fuerza linea extra.
    _LABEL_NAME_NARROW = " iljtfrI.,;:'|!()[]-"
    _LABEL_NAME_WIDE = 'mwMW@%'
    # Techo del presupuesto vertical: mas lineas empujarian la linea del color
    # fuera del rollo. Pasado el techo se recorta, que es el mal menor.
    _LABEL_NAME_MAX_LINES = 3
    # 1.2 y no 1.05: tiene que cubrir ascendentes y descendentes de la fuente
    # de cada base (Lato, en la que se pisaba, los tiene mas largos que
    # Helvetica). Ha de coincidir con el line-height del div en la plantilla.
    _LABEL_NAME_LINE_HEIGHT = 1.2
    # Que parte de las lineas que el nombre no usa se pasa como hueco encima
    # del precio. Con 1.0 el precio queda siempre a la altura del caso de 3
    # lineas, a 1pt del borde util del rollo de 30: cualquier desalineacion de
    # la impresora lo recorta. Con 0.5 un nombre de una linea deja una linea de
    # hueco y el precio sube ~10pt del borde; con dos lineas, media.
    _LABEL_PRICE_SPARE_RATIO = 0.5

    @api.model
    def _label_name_char_width(self, char):
        if char in self._LABEL_NAME_NARROW:
            return 0.5
        if char in self._LABEL_NAME_WIDE:
            return 1.6
        if char.isupper():
            return 1.3
        if char.isdigit():
            return 1.05
        return 1.0

    @api.model
    def _label_name_width(self, text):
        return sum(self._label_name_char_width(c) for c in text)

    @api.model
    def _label_name_line_count(self, text, line_units):
        """Lineas que ocupa `text` en una columna de `line_units` de ancho."""
        space = self._label_name_char_width(' ')
        lines = 0
        current = 0.0
        for word in (text or '').split():
            width = self._label_name_width(word)
            # Palabra mas ancha que la columna: break-word la corta donde llega,
            # sin guion, y consume una linea entera por cada trozo. Se parte por
            # ancho acumulado, no por numero de caracteres.
            while width > line_units:
                if current:
                    lines += 1
                    current = 0.0
                cut = 0.0
                index = 0
                for index, char in enumerate(word):
                    step = self._label_name_char_width(char)
                    if cut + step > line_units:
                        break
                    cut += step
                else:
                    index = len(word)
                lines += 1
                word = word[index or 1:]
                width = self._label_name_width(word)
            if not word:
                continue
            needed = width if not current else current + space + width
            if needed <= line_units:
                current = needed
            else:
                lines += 1
                current = width
        if current:
            lines += 1
        return max(lines, 1)

    @api.model
    def _label_name_lines(self, text):
        """Lineas a reservar para el nombre, con el techo aplicado."""
        lines = self._label_name_line_count(text, self._LABEL_NAME_LINE_UNITS)
        return min(lines, self._LABEL_NAME_MAX_LINES)

    @api.model
    def _label_name_height(self, text):
        """Alto en em a reservar para el nombre."""
        return round(self._label_name_lines(text) * self._LABEL_NAME_LINE_HEIGHT, 2)

    @api.model
    def _label_price_offset(self, text):
        """Margen extra en em sobre el precio: parte de las lineas del techo
        que el nombre no usa. El presupuesto vertical del rollo esta calculado
        para _LABEL_NAME_MAX_LINES, asi que con menos lineas sobra ese alto;
        pasando una parte encima del precio, el hueco con el nombre crece en
        vez de quedar pegado, sin llevar el precio al borde del rollo. Es la
        alternativa a dar alto fijo a la tabla, que es lo que rompia el rollo.
        """
        spare = self._LABEL_NAME_MAX_LINES - self._label_name_lines(text)
        return round(spare * self._LABEL_PRICE_SPARE_RATIO * self._LABEL_NAME_LINE_HEIGHT, 2)
