# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class Order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(Order, self)._prepare_invoice()
        invoice_number = self.point_printing_id._get_electronic_sequence()
        invoice_vals['invoice_number'] = invoice_number
        return invoice_vals

    @api.multi
    def make_electronic_invoice(self):
        """
        Generamos factura electrónica y si edificio
        tienen configurado picking automático lo hacemos.
        :return:
        """
        self.ensure_one()
        if self.state != 'sale':
            raise ValidationError(_("Notas de pedido deben estar en estado 'nota de pedido'."))

        # Listado de IDS de facturas creadas
        invoices = self.action_invoice_create()

        # Validamos cada factura, primero hacemos el método onchange de
        # invoice_number para cálculo de campo reference
        object_invoice = self.env['account.invoice']
        for id_invoice in invoices:
            invoice = object_invoice.browse(id_invoice)
            invoice._onchange_invoice_number()
            invoice.action_invoice_open()
        return self.action_view_invoice()
