# -*- coding: utf-8 -*-
{
    'name': "kio_isp_business_dashboard",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'web',
        'account',
        'hr_expense',
        'kio_account_accountant',
        'kio_account_reports',
    ],

    # always loaded
    'data': [
        'views/views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kio_isp_business_dashboard/static/src/js/business_overview_dashboard.js',
            'kio_isp_business_dashboard/static/src/xml/business_overview_dashboard.xml',
            'kio_isp_business_dashboard/static/src/scss/business_overview_dashboard.scss',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

