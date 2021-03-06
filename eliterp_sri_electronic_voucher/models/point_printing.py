# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import UserError


class PointPrinting(models.Model):
    _inherit = 'sri.point.printing'

    @api.multi
    def button_update_sequence(self):
        """
        Actualizamos secuenciales.
        :return:
        """
        self.ensure_one()
        if self.new_sequence_electronic_invoice > 0:
            self.sequence_electronic_invoice.sudo().update(
                {'number_next_actual': self.new_sequence_electronic_invoice}
            )
        if self.new_sequence_electronic_credit_note > 0:
            self.sequence_electronic_credit_note.sudo().update(
                {'number_next_actual': self.new_sequence_electronic_credit_note}
            )
        if self.new_sequence_electronic_retention> 0:
            self.sequence_electronic_retention.sudo().update(
                {'number_next_actual': self.new_sequence_electronic_retention}
            )
        return True


    @api.one
    def _create_new_sequence(self, type):
        """
        Creamos secuencia de cada documento
        al crear punto de impresión.
        :return:
        """
        sequence = self.env['ir.sequence'].sudo().create({
            'name': _("Secuencia %s electrónica para %s") % (type, self.name),
            'implementation': 'no_gap',
            'number_increment': 1
        })
        if type == "factura":
            self.sequence_electronic_invoice = sequence
        elif type == "n/c":
            self.sequence_electronic_credit_note = sequence
        elif type == "retención":
            self.sequence_electronic_retention = sequence

    @api.model
    def create(self, vals):
        """
        Al crear verificamos no tengan secuencias de documentos
        y las creamos.
        :param vals:
        :return:
        """
        record = super(PointPrinting, self).create(vals)
        if record.allow_electronic_invoice and not record.sequence_electronic_invoice:
            record._create_new_sequence("factura")
        if record.allow_electronic_credit_note and not record.sequence_electronic_credit_note:
            record._create_new_sequence("n/c")
        if record.allow_electronic_retention and not record.sequence_electronic_retention:
            record._create_new_sequence("retención")
        return record

    @api.multi
    def write(self, values):
        result = super(PointPrinting, self).write(values)
        if self.allow_electronic_invoice and not self.sequence_electronic_invoice:
            self._create_new_sequence("factura")
        if self.allow_electronic_credit_note and not self.sequence_electronic_credit_note:
            self._create_new_sequence("n/c")
        if self.allow_electronic_retention and not self.sequence_electronic_retention:
            self._create_new_sequence("retención")
        return result

    def _get_electronic_sequence(self, type='out_invoice'):
        """
        Retornamos el siguiente número de la secuencia
        :param type:
        :return:
        """
        next_number = False
        if type == 'out_invoice':
            next_number = self.sequence_electronic_invoice.number_next_actual
        if type == 'out_refund':
            next_number = self.sequence_electronic_credit_note.number_next_actual
        if type == 'retention':
            next_number = self.sequence_electronic_retention.number_next_actual
        if not next_number:
            raise UserError(
                _(
                    "No está definida la secuencia para documento electrónico para punto de impresión: %s") % self.name)
        return str(next_number)

    @api.multi
    def next(self, type):
        """
        Dependiendo del tipo generamos el nuevo secuencial.
        :param type:
        :return:
        """
        self.ensure_one()
        if type == 'out_invoice':
            self.sequence_electronic_invoice.next_by_id()
        if type == 'out_refund':
            self.sequence_electronic_credit_note.next_by_id()
        if type == 'retention':
            self.sequence_electronic_retention.next_by_id()

    allow_electronic_invoice = fields.Boolean('Permitir factura electrónica?', default=True)
    sequence_electronic_invoice = fields.Many2one('ir.sequence', string="Secuencia factura")
    current_sequence_electronic_invoice = fields.Integer('Secuencia actual',
                                                         related='sequence_electronic_invoice.number_next_actual',
                                                         readonly=True)
    new_sequence_electronic_invoice = fields.Integer('Nueva secuencia', default=1)

    allow_electronic_credit_note = fields.Boolean('Permitir N/C electrónica?', default=True)
    sequence_electronic_credit_note = fields.Many2one('ir.sequence', string="Secuencia N/C")
    current_sequence_electronic_credit_note = fields.Integer('Secuencia actual',
                                                             related='sequence_electronic_credit_note.number_next_actual',
                                                             readonly=True)
    new_sequence_electronic_credit_note = fields.Integer('Nueva secuencia', default=1)

    allow_electronic_retention = fields.Boolean('Permitir retención electrónica?', default=False)
    sequence_electronic_retention = fields.Many2one('ir.sequence', string="Secuencia retención")
    current_sequence_electronic_retention = fields.Integer('Secuencia actual',
                                                           related='sequence_electronic_retention.number_next_actual',
                                                           readonly=True)
    new_sequence_electronic_retention = fields.Integer('Nueva secuencia', default=1)

    allow_electronic_debit_note = fields.Boolean('Permitir N/D electrónica?', default=False)
    sequence_electronic_debit_note = fields.Many2one('ir.sequence', string="Secuencia N/D")

    allow_electronic_waybill = fields.Boolean('Permitir G/R electrónica?', default=False)
    sequence_electronic_waybill = fields.Many2one('ir.sequence', string="Secuencia G/R")


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('type', 'authorized_voucher_id', 'point_printing_id')
    def _compute_is_electronic(self):
        """
        ME:
        :return:
        """
        res = super(Invoice, self)._compute_is_electronic()
        if self.point_printing_id.allow_electronic_invoice and self.type == 'out_invoice':
            self.is_electronic = True
        if self.point_printing_id.allow_electronic_credit_note and self.type == 'out_refund':
            self.is_electronic = True
        return res

    @api.onchange('point_printing_id')
    def _onchange_point_printing_id(self):
        if self.point_printing_id.allow_electronic_invoice and self.type == 'out_invoice':
            sequence = self.point_printing_id._get_electronic_sequence()
            self.invoice_number = sequence
        if self.point_printing_id.allow_electronic_credit_note and self.type == 'out_refund':
            sequence = self.point_printing_id._get_electronic_sequence('out_refund')
            self.invoice_number = sequence


class Retention(models.Model):
    _inherit = 'account.retention'

    @api.one
    @api.depends('type', 'point_printing_id')
    def _compute_is_electronic(self):
        """
        ME:
        :return:
        """
        res = super(Retention, self)._compute_is_electronic()
        if self.point_printing_id.allow_electronic_retention and self.type == 'purchase':
            self.is_electronic = True
        return res

    @api.onchange('point_printing_id')
    def _onchange_point_printing_id(self):
        if self.point_printing_id and self.is_electronic:
            sequence = self.point_printing_id._get_electronic_sequence('retention')
            self.reference = sequence
