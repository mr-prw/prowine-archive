{
    'name': 'Google Place Autocomplete & Map',
    'sequence': 20,
    'author': 'D.Jane',
    'summary': 'Sync between map marker and input value.',
    'version': '1.0',
    'description': "Google Map"
                   " Google Place Autocomplete",
    'depends': ['web'],
    'data': [
        'views/header.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
    'images': ['static/description/banner.png'],
    'license': 'OPL-1',
}
