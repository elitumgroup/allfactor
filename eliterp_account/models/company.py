# -*- coding: utf-8 -*-

from odoo import models, api, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def setting_chart_of_accounts_action(self):
        """
        ME: Añadimos al dominio tipos de cuentas diferentes a las de vista
        :return:
        """
        res = super(ResCompany, self).setting_chart_of_accounts_action()
        res['domain'].append(('internal_type', '!=', 'view'))
        return res

    # Configuración para empresa de Factoring
    portfolio_account_id = fields.Many2one('account.account', string="Cuenta de cartera")
    reserve_account_id = fields.Many2one('account.account', string="Cuenta de reserva")
    customer_retention_account_id = fields.Many2one('account.account', string="Cuenta de retención",
                                                    help="Cuenta contable utilizada para la generación de retenciones.")
