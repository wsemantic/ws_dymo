# product_label_report

Etiqueta Dymo de producto para **retail de moda**: talla en grande, precio,
nombre y color, pensada para prendas con variantes de talla y color.

Este documento recoge **por qué** el código está como está. La mayoría de las
decisiones de abajo parecen arbitrarias leyendo la plantilla, y varias se
tomaron después de descartar alternativas que parecían más limpias pero no
funcionan en este entorno.

## Instalación y puesta en marcha

**1. Clasificar los atributos.** La etiqueta decide qué imprime en grande según
el campo `attribute_type` de `product.attribute`, que añade este módulo:

- `size` → se imprime en grande a la izquierda. Solo se usa el primero.
- `color` → se imprime en pequeño en la línea inferior, truncado a 12 caracteres.
- Sin clasificar → cae también en la línea pequeña, junto al color.

Si no se clasifica ningún atributo como `size`, la etiqueta funciona pero pierde
su motivo de ser: la zona grande queda vacía.

**2. Ajustar el paperformat al rollo real.** Ver la sección *Paperformat*.

**3. Verificar con el rollo puesto**, imprimiendo varias etiquetas seguidas y con
el caso peor (nombre largo + talla larga). Ver *Presupuesto vertical*.

## El módulo no es solo estético: corrige un defecto de core

`product.report_productlabel_dymo` (Odoo 18) fija a fuego:

```xml
<t t-set="table_style" t-value="'width:100%;height:32mm;'"/>
<t t-set="padding_page" t-value="'padding: 2mm'"/>
<t t-set="barcode_size" t-value="'width:45.5mm;height:7.5mm'"/>
```

Ese `height:32mm` **no se calcula desde el paperformat**: core asume que el rollo
mide 32mm. Sumado a los 2mm de `padding_page` arriba y abajo, son 36mm de
contenido en la página. En un rollo de 30mm eso desborda, el sobrante empuja a la
página siguiente y el margen superior baila etiqueta sí, etiqueta no.

Como el estilo va **inline**, no hay forma de corregirlo desde SCSS ni desde la
configuración. La única vía es sustituir el `div.o_label_full` entero, que es lo
que hace `report/product_label_dymo.xml`, y no aplicarle `table_style`.

**Si se desinstala este módulo, vuelve el problema.** No es una personalización
prescindible mientras el rollo no mida exactamente 32mm.

## Caminos descartados y por qué

**Tocar el alto en el SCSS.** Inútil frente al estilo inline de core. Se perdió
mucho tiempo aquí. La regla `.o_label_sheet.o_label_dymo { height: auto }` que
sigue en el SCSS es correcta pero secundaria: evita que el contenedor exterior
imponga 32mm, nada más.

**Sobreescribir `.o_label_page.o_label_dymo` (regla de stock).** El contenedor
real es `o_label_sheet`, comprobado en el HTML renderizado. Esa regla no
interviene.

**Calcular alto y escala de fuente desde el paperformat en Python.** Viable, pero
innecesario: los rollos reales de las dos instalaciones son 29 y 30mm, un
milímetro de diferencia. No compensa la complejidad.

**`vh` o `calc()` en el CSS.** El motor de wkhtmltopdf es un WebKit antiguo y no
los maneja de forma fiable. Usar `mm`, `%` y `em`.

**`max-height` + `overflow: hidden` para recortar el nombre.** No recorta de
forma fiable, y menos dentro de un `td`: el sobrante se desborda visualmente y se
monta sobre lo que haya debajo. Usar `height` fijo, y aun así no confiar en el
recorte para evitar solapes; separar los elementos en celdas distintas.

**Nombre en su propio bloque a todo el ancho, bajo el código.** Se ve entero pero
añade ~2,3mm de altura y echa la línea del color fuera de la etiqueta.

**Nombre y precio en la misma celda.** No se pueden anclar uno arriba y otro
abajo. Y al compartir fila con la talla, el nombre la arrastraba hacia abajo.
De ahí la rejilla con `rowspan` (ver abajo).

**`header_spacing` del paperformat.** No hace nada: wkhtmltopdf solo lo aplica si
el informe tiene cabecera, y este no la tiene. El valor 30 que trae es el que
Odoo pone por defecto pensando en A4.

**Encogimiento inteligente (`disable_shrinking`).** Es un zoom calculado sobre el
*ancho*, no un ajuste vertical. Que "arreglara" el desbordamiento era casualidad.
El diseño debe cuadrar con el encogimiento desactivado.

## Estructura de la etiqueta

```
[ barras del codigo, a todo el ancho ]
┌──────────┬─────────────────┐
│ codigo   │                 │
├──────────┤  nombre         │   tabla de 3 filas con rowspan
│  TALLA   │                 │
│          ├─────────────────┤
│          │     precio      │
└──────────┴─────────────────┘
[ color ]
```

La rejilla con `rowspan` existe para que cada elemento se ancle donde le toca sin
arrastrar a los demás: nombre arriba, precio abajo, talla independiente de ambos.
El código alfanumérico entra como primera fila de la izquierda —en vez de ir en
una línea propia a todo el ancho— para que el nombre arranque a su altura y
aproveche el hueco que si no quedaría en blanco a su derecha.

`table-layout: fixed` es **imprescindible**: en modo `auto` el `width` del `td` es
solo una sugerencia y la tabla ensancha la columna para no partir el texto, con lo
que el nombre se queda en una línea y se recorta.

## Ajustes: qué número tocar

| Síntoma | Palanca |
|---|---|
| El nombre se recorta | Bajar los umbrales de longitud del `div.product_barcode_name` |
| Un nombre corto salta de línea sin usarla | Subir esos umbrales |
| Se cambia el `width: 58%` del `td` del nombre | **Revisar los umbrales**: están calibrados para ese ancho (~30mm, unos 14 caracteres por línea a tamaño completo) |
| La talla se aprieta | Bajar el `width: 58%` |
| El código de barras roza por arriba | `margin_top` del paperformat, no la plantilla: es alineación de *esa* impresora |
| Talla y precio muy pegados al código | `margin-top` de la `table` |

Los umbrales de longitud van en pares (altura reservada y tamaño de fuente) y
**deben cambiarse juntos**: el nombre que baja de cuerpo es el mismo que recibe
una línea más.

## Al depurar: no te fíes de lo que ves impreso

Dos capas ocultan los cambios y cuestan horas si no se sabe:

**Los assets se cachean como `ir.attachment`.** Un cambio en el SCSS no llega al
PDF hasta que se regenera el bundle `web.report_assets_common`, y el bundle solo
se construye **cuando se imprime** (no al cargar la interfaz). Reiniciar no
basta. Para trabajar, poner `dev_mode = assets` en el `odoo.conf`: entonces los
bundles no se materializan como adjuntos —que no aparezcan es señal de que el
modo está activo— y se compilan al vuelo. **Quitarlo en producción.**

**Los cambios de XML necesitan `-u product_label_report`.** El modo `assets` no
recarga vistas.

La forma fiable de ver qué recibe wkhtmltopdf, desde `odoo shell`:

```python
report = env['ir.actions.report'].search([('report_name', '=', 'product.report_producttemplatelabel_dymo')])
html = report._render_qweb_html(report.report_name, [TEMPLATE_ID], {'studio': True})[0].decode()
```

`{'studio': True}` no tiene nada que ver con Odoo Studio: es una clave que mira
`wizard/product_label_report.py` y es la única rama que funciona sin los datos del
asistente. `TEMPLATE_ID` debe ser un `product.template` (esa rama hace `browse`
sobre ese modelo), no un `product.product`.

Cinco minutos con esto ahorran una tarde de conjeturas.

## Presupuesto vertical (rollo de 30mm)

30mm menos 2mm×2 de `padding_page` = **26mm útiles**. Reparto aproximado:

| Elemento | Alto |
|---|---|
| Barras | 7,5mm (fijo, `barcode_size` de core) |
| Código + nombre + talla + precio | ~13mm |
| Color | ~2,4mm |

Quedan ~3mm de holgura, que se consumen con nombres de tres líneas. El caso peor
a probar siempre es **nombre largo + talla larga**: es el que decide si la línea
del color entra o se sale.

## Paperformat

`page_height` debe coincidir con el rollo **real**, y conviene comprobarlo en cada
instalación: el paperformat dymo de Odoo viene con 35mm por defecto y es
frecuente que nadie lo haya tocado, aunque el rollo mida 29 o 30.

Mientras el contenido quepa no se nota —la Dymo corta por el sensor de troquel,
no por el alto declarado—, pero una configuración que miente despista a quien
venga después a diagnosticar. Nos costó media sesión.

`margin_top` es la palanca para corregir que el código de barras salga rozado por
arriba. Es **alineación de esa impresora y ese rollo**, no del diseño: por eso va
en el paperformat y no en la plantilla. Ojo a que resta alto útil.

## TODO: el diseño está atado a 26mm útiles

**Limitación conocida.** Todos los tamaños de la plantilla —cuerpo de la talla,
del precio, umbrales de longitud del nombre, alto reservado por línea— están
calibrados a mano para **26mm útiles**, es decir un rollo de 30mm menos los 2mm×2
de `padding_page` de core. Los números son literales repartidos por
`report/product_label_dymo.xml`, no se derivan de nada.

Con un rollo sensiblemente distinto el diseño no se adapta: si es más corto, la
línea del color se sale; si es más largo, sobra espacio sin aprovechar. Para un
módulo genérico de retail esto va a chocar en cuanto se instale con otro rollo.

**Salida prevista**: derivar una escala del paperformat. Todos los tamaños
cuelgan por `em` del contenedor, así que basta con calcular un único `font-size`
en Python a partir del alto útil (`page_height` menos márgenes) y aplicarlo
inline al `div.o_label_full`, que ya sustituimos. Notas de cuando se estudió:

- Se descartó entonces **solo** porque las dos instalaciones existentes se
  diferenciaban en un milímetro y no compensaba. El argumento decae en cuanto
  haya rollos variados.
- Nada de `calc()` ni `vh`: el WebKit de wkhtmltopdf no los maneja bien. Un
  número calculado en servidor e interpolado con `t-attf-style`.
- QWeb no fusiona `style=` con `t-att-style` en el mismo nodo: el dinámico pisa
  al literal sin avisar. Hay que concatenar dentro del propio `t-attf-style`.
- Hace falta una altura de referencia contra la que escalar. Ojo con anclarla al
  paperformat de una instalación concreta: puede estar sin tocar desde el valor
  por defecto de Odoo y no reflejar el rollo real.
- Los **7,5mm del código de barras son fijos** (`barcode_size` de core) y no
  escalan con la fuente. En rollos pequeños son el primer límite duro; habría
  que sobreescribir también `barcode_size`.
- Los umbrales de longitud del nombre dependen del ancho en mm de su columna, no
  del alto, así que **no** deben escalar con esta fórmula.
