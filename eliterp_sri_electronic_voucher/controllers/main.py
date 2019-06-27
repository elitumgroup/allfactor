# -*- coding: utf-8 -*-

from datetime import date, timedelta
from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request

class SriElectronicVoucher(http.Controller):

    @http.route('/eliterp_sri_electronic_voucher/data', type='json', auth='user')
    def web_settings_dashboard_data(self, **kw):
        if not request.env.user.has_group('eliterp_sri_electronic_voucher.electronic_voucher_manager'):
            raise AccessError(_("Acceso denegado"))

        # Compañía actual
        company = request.env.user.sudo().company_id

        last_thirty_days = ('create_date', '>=', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))

        # Comprobantes autorizados
        vouchers_authorized = request.env['sri.electronic.voucher'].search_count([
            ('company_id', '=', company.id),
            ('state', '=', 'authorized_sri'),
            last_thirty_days
        ])
        # Comprobantes no autorizados
        vouchers_not_authorized = request.env['sri.electronic.voucher'].search_count([
            ('company_id', '=', company.id),
            ('state', '=', 'not_authorized_sri'),
            last_thirty_days
        ])
        # Otros comprobantes
        vouchers_others = request.env['sri.electronic.voucher'].search_count([
            ('company_id', '=', company.id),
            ('state', 'not in', ['authorized_sri', 'not_authorized_sri']),
            last_thirty_days
        ])

        return {
            'summary': {
                'vouchers_authorized': vouchers_authorized,
                'vouchers_not_authorized': vouchers_not_authorized,
                'vouchers_others': vouchers_others
            },
        }
