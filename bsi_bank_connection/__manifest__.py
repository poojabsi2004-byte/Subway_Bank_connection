{
    'name': 'BSI Bank Connection',
    'version': '19.0',
    'category': 'BSI Bank',
    'summary': 'Upload and parse BAI files',
    'depends': ['base', 'bsi_subway_base'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/ir.cron.xml',
        'views/bsi_bank_accounts.xml',
        'views/bsi_bank_statements.xml',
        'views/bsi_bank_transactions.xml',
        'views/mapping.xml',
        'views/bsi_sftp_files.xml',
        'views/res_config_setting.xml',
    ],
    'installable': True,
}
