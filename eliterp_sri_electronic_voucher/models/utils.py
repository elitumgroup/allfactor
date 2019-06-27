# -*- coding: utf-8 -*-

MESSAGE_404 = "URL no existe o API está inactiva. Consultar con proveedor de API."
MESSAGE_500 = "Error al consultar API, error en origen (Odoo) o SRI."
MESSAGE_CERTIFICATE = 'No tiene certificado digital válido en compañía.'

# TODO: Ver estados
STATES = [
    ('new', 'Nuevo'),
    ('sign_xml', 'Documento firmado'),
    ('rejected_sri', 'Rechazado SRI'),
    ('authorized_offline', 'Autorizado Off-line'),
    ('authorized_sri', 'Autorizado SRI'),
    ('not_authorized_sri', 'No autorizado SRI'),
    ('cancel', 'Anulado')
]

TEMPLATES = {
    'out_invoice': 'out_invoice.xml',
    'out_refund': 'out_refund.xml',
    'retention': 'retention.xml'
}

table3 = {
    '04': '04',
    '05': '05',
    '06': '06',
    '07': '07',
    '18': '01',
}

table6 = {
    '0': '04',
    '1': '05',
    '3': '07'
}

# TODO: No existe ICE, ni IRBPNR. Por eso siempre 2
# table16 = 2

table19 = {
    'rent': '1',
    'iva': '2'
}

table20 = {
    0: '7',
    10: '9',
    20: '10',
    30: '1',
    50: '11',
    70: '2',
    100: '3'
}