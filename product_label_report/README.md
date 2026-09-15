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

**Rejilla de 3 filas con `rowspan` cruzados** (nombre en filas 1-2, talla en
2-3, precio en la 3). Parecía la forma de anclar cada cosa donde le toca, pero
WebKit reparte el alto sobrante de cada `rowspan` entre sus filas y las
restricciones se encadenan: la fila del precio tenía que absorber además la
parte de la talla que no cabía en la fila 2, y la tabla salía **más alta que
cualquiera de las dos columnas**. Con dos líneas de nombre eso empujaba el color
a la etiqueta siguiente. Sustituida por una sola fila con dos celdas que apilan
lo suyo: así el alto es exactamente `max(izquierda, derecha)`.

**Color debajo de la tabla.** Cae donde acabe la columna más alta, que con tres
líneas de nombre más precio ya toca el borde del rollo de 30mm: el color salía
cortado y arrastraba una etiqueta en blanco. Ahora va en la celda izquierda,
bajo la talla, donde sobra alto y no depende del nombre.

**`line-height: 1.05` en el nombre.** Ajustado al milímetro para Helvetica, pero
la fuente la pone cada instalación (una de ellas usa Lato, con ascendentes y
descendentes más largos) y el texto se salía por abajo de la caja reservada y se
montaba sobre el precio. Va a 1.2, que cubre las fuentes habituales, y el precio
lleva además `margin-top: 0.3em` porque su cifra (`.oe_currency_value` a 1.3em
sobre 1.7em) sobresale por arriba de su propia caja de línea.

**Contar mayúsculas a 1.25 unidades con 14 por línea.** Estimaba 3 líneas para
un nombre que el render hacía en 2, y el alto reservado de más estiraba la
tabla. Medido sobre una etiqueta real: 13 mayúsculas más un espacio llenan el
93% de la columna. Las proporciones actuales de `product.py` (mayúscula 1.3,
dígito 1.05, espacio 0.5, 18 unidades por línea) salen de esa medida. Si se
recalibra, hacerlo con una muestra impresa, no a ojo.

**`header_spacing` del paperformat.** No hace nada: wkhtmltopdf solo lo aplica si
el informe tiene cabecera, y este no la tiene. El valor 30 que trae es el que
Odoo pone por defecto pensando en A4.

**Encogimiento inteligente (`disable_shrinking`).** Es un zoom calculado sobre el
*ancho*, no un ajuste vertical. Y **no es condicional**: wkhtmltopdf maqueta a
96dpi y escala al papel a 75dpi, así que aplica siempre un factor ~0.78 aunque
todo quepa. Que "arreglara" el desbordamiento era casualidad. El diseño debe
cuadrar con el encogimiento desactivado; dos instalaciones con el flag distinto
imprimen la misma plantilla a tamaños distintos y despistan al comparar.

**Vistas huérfanas de un módulo anterior.** Al mover esta personalización desde
otro módulo quedó en una base una vista `...custom` heredando del mismo
`product.report_simple_label_dymo`, con la plantilla antigua. Actualizar este
módulo no la toca, y las dos herencias se aplican sobre el mismo `div`: los
cambios "no llegaban". Si un cambio no se ve tras `-u`, buscar en Ajustes →
Técnico → Vistas todas las que hereden de ese template y comprobar el ID
externo: solo deben quedar la de core y `product_label_report.report_simple_label_dymo`
(nombre "Report Label Dymo").

## Estructura de la etiqueta

```
[ barras del codigo, a todo el ancho ]
┌──────────┬─────────────────┐
│ codigo   │ nombre          │
│  TALLA   │ (1 a 3 lineas)  │   una fila, dos celdas independientes
│ color    │          precio │
└──────────┴─────────────────┘
```

Dos celdas y **ninguna fila compartida**: cada columna apila lo suyo y el alto
de la tabla es `max(izquierda, derecha)`. La izquierda (código, talla, color)
mide siempre lo mismo; la derecha crece con las líneas del nombre y el precio
va justo debajo. El color está en la izquierda a propósito: es lo que garantiza
que un nombre de tres líneas no lo eche fuera del rollo. Como esa columna es
estrecha (~24mm) el color baja de cuerpo con la longitud, igual que la talla.

El alto del nombre se reserva desde Python (`product.label.name.fit`), que
simula el ajuste de línea por palabras con anchos aproximados por carácter.

`table-layout: fixed` es **imprescindible**: en modo `auto` el `width` del `td` es
solo una sugerencia y la tabla ensancha la columna para no partir el texto, con lo
que el nombre se queda en una línea y se recorta.

## Ajustes: qué número tocar

| Síntoma | Palanca |
|---|---|
| El nombre se recorta / salta de línea sin usarla | `_LABEL_NAME_LINE_UNITS` y los anchos por carácter en `models/product.py`. Recalibrar con una muestra impresa |
| Se cambia el `width: 65%` del `td` del nombre | **Rehacer `_LABEL_NAME_LINE_UNITS`**: está calibrado para ese ancho (~34mm) |
| Se cambia el `line-height` del nombre | Cambiarlo también en `_LABEL_NAME_LINE_HEIGHT`; van a la par |
| El precio roza el nombre | `margin-top` del `div` del precio (0.3em) |
| El color desborda su columna | Umbrales de longitud del `div.attrib_val_color` |
| La talla se aprieta | Bajar el `width: 65%` |
| El código de barras roza por arriba | `margin_top` del paperformat, no la plantilla: es alineación de *esa* impresora |

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
