# -*- coding: utf-8 -*-

import os
import time
import logging
import itertools
from jinja2 import Environment, FileSystemLoader
from odoo import api, models, fields
from odoo.exceptions import UserError
from . import utils
from datetime import datetime


class Retention(models.Model):
    _inherit = 'account.retention'

    @api.multi
    def confirm(self):
        for retention in self.filtered(lambda x: x.is_electronic):
            retention.action_electronic_voucher()
            retention.point_printing_id.next("retention")
        return super(Retention, self).confirm()

    def fix_date(self, date):
        d = date.strftime('%d/%m/%Y')
        return d

    def _get_electronic_voucher(self):
        """
        Creamos documento electrónico desde 'account.retention'
        con la clave de acceso generada.
        :return:
        """
        company = self.company_id
        object = self.env['sri.electronic.voucher']
        authorized_voucher = self.env['sri.authorized.vouchers'].search([('code', '=', '07')])[0]
        vals = {
            'name': "0",
            'document_id': '{0},{1}'.format('account.retention', str(self.id)),
            'type_emission': company.type_emission,
            'environment': company.environment,
            'authorized_voucher_id': authorized_voucher.id,
            'document_date': self.date_retention,
            'document_number': self.retention_number,
            'company_id': company.id
        }
        new_object = object.sudo().create(vals)
        return new_object

    def _get_vals_information(self):
        """
        Devolvemos la información necesaria
        para el documento XML.
        :param invoice:
        :return:
        """
        company = self.company_id
        partner = self.partner_id
        point_printing = self.point_printing_id
        informationRetention = {
            'fechaEmision': self.fix_date(self.date_retention),
            'dirEstablecimiento': point_printing.shop_id.street,
            'obligadoContabilidad': 'SI',
            'tipoIdentificacionSujetoRetenido': utils.table6[partner.type_documentation],
            'razonSocialSujetoRetenido': partner.name,
            'identificacionSujetoRetenido': partner.documentation_number,
            'periodoFiscal': self.date_retention.strftime("%m/%Y")
        }

        if company.special_contributor:
            informationRetention.update({'contribuyenteEspecial': company.code_special_contributor})
        return informationRetention

    def _get_vals_taxes(self):
        """
        Detalle de la retención(Líneas)
        :return dict:
        """
        taxes = []
        invoice = self.invoice_id
        for line in self.retention_lines:
            type = line.retention_type
            tax = line.tax_id
            detail = {
                'codigo': utils.table19[type],
                'codigoRetencion': tax.code if type == 'rent' else utils.table20[tax.amount],
                'baseImponible': '{:.2f}'.format(line.base_taxable),
                'porcentajeRetener': '{:.2f}'.format(tax.amount),
                'valorRetenido': '{:.2f}'.format(line.amount),
                'codDocSustento': '01', # TODO
                'numDocSustento': invoice.reference.replace('-', ''),
                'fechaEmisionDocSustento': self.fix_date(invoice.date_invoice)
            }
            taxes.append(detail)
        return {'impuesto': taxes}

    @api.multi
    def action_electronic_voucher(self):
        self.ensure_one()
        electronic_voucher = self._get_electronic_voucher()
        self.write({
            'electronic_voucher_id': electronic_voucher.id
        })


    electronic_voucher_id = fields.Many2one('sri.electronic.voucher', string='Comprobante electrónico', readonly=True, copy=False)
    authorization_date = fields.Datetime(
        'Fecha autorización',
        related='electronic_voucher_id.authorization_date', store=True
    )
    authorization_status = fields.Selection(utils.STATES, related='electronic_voucher_id.state', store=True)
