# -*- coding: utf-8 -*-
{
    'name': "Product Label Report",
    'summary': """Product Label Report""",
    'description': """Product Label Report""",
    'author': "Semantic Web Software SL",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['product'],
    'data': [
        'report/product_label_dymo.xml',
        'views/product_attribute_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            ('replace', 'product/static/src/scss/report_label_sheet.scss', 'product_label_report/static/src/scss/report_label_sheet.scss'),
        ],
    },
    'installable': True,
    'application': True
}
