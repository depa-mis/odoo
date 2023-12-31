
{
    'name': 'สารบรรณ',
    'version': '12.9.26.2020.1',
    'website': 'https://ice-solutions.co/',
    'license': '',
    'author': "Korakot Luechaphonthara",
    'category': 'Localisation/Asia',
    'description': "สารบรรณ",
    'depends': ['base','hr','mail'],
    'data': [
        'security/group_saraban.xml',
        'views/document_main.xml',
        #  'views/session_board.xml',
        'views/hr.xml',
        'views/sequence.xml',
        'views/setting.xml',
        'views/internal_document.xml',
        'wizard/wiz_send_email_view.xml',
        'views/internal_document_announce.xml',
        'views/receive.xml',
        'views/menuitem.xml',
        'views/action_button.xml',
        'wizard/make_approval_wizard_view.xml',
        'wizard/make_approval_wizard_view_receive.xml',
		'wizard_word/word_wizard_wizard_view.xml',
        'data/mail.xml',
        'data/email_template_data.xml',
        'security/ir.model.access.csv',
        'security/group_saraban.xml',
    ],
    'installable': True,
    'application': True,
    'development_status': 'alpha',
    'maintainers': ['Korakot Luechaphonthara'],
    'external_dependencies' : {
        'python' : ['docx'],
    }
}

