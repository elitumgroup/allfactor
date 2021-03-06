# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import re


class Invoice(models.Model):
    _inherit = 'account.invoice'

    ISSUANCE_DOCUMENTS = [
        'out_invoice',
        'out_refund'
    ]

    @api.multi
    def name_get(self):
        """
        Cambios los registros a mostrar
        :return:
        """
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Credit Note'),
            'in_refund': _('Vendor Credit note'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s [%s]" % (TYPES[inv.type], inv.reference or '*')))
        return result

    @api.one
    @api.depends('serial_number', 'invoice_number', 'point_printing_id')
    def _compute_reference(self):
        """
        Calcular el número de documento dependiendo del tipo
        :return:
        """
        if self.type in self.ISSUANCE_DOCUMENTS:
            self.reference = '{0}-{1}-{2}'.format(
                self.point_printing_id.shop_id.establishment,
                self.point_printing_id.emission_point,
                self.invoice_number if self.invoice_number else '*'
            )
        else:
            self.reference = '{0}-{1}'.format(
                self.serial_number,
                self.invoice_number
            )

    @api.onchange('invoice_number')
    def _onchange_invoice_number(self):
        """
        Rellenamos de 0 el número de factura
        :return:
        """
        if self.invoice_number:
            self.invoice_number = self.invoice_number.zfill(9)

    @api.multi
    def action_move_create(self):
        """
        Agregamos el proyecto y división al movimiento creado
        :return:
        """
        result = super(Invoice, self).action_move_create()
        for inv in self:
            inv.move_id.write({
                'company_division_id': inv.company_division_id.id,
                'project_id': inv.project_id.id
            })
        return result

    @api.constrains('invoice_number')
    def _check_invoice_number(self):
        """
        Validamos qué secuencial este entre el rango ingresado en autorización
        :return:
        """
        if not self.type in self.ISSUANCE_DOCUMENTS:
            return
        if self.invoice_number and not self.is_electronic:
            self.sri_authorization_id.is_valid_number(int(self.invoice_number))

    @api.constrains('authorization')
    def _check_authorization(self):
        """
        Verificamos que la autorización sean los dígitos correctos para plantilla ATS (Compras)
        :return:
        """
        if self.type in self.ISSUANCE_DOCUMENTS:
            return
        if self.authorization and len(self.authorization) not in [10, 35, 49]:
            raise ValidationError('Debe ingresar 10, 35 o 49 dígitos según el tipo de autorización.')

    @api.one
    @api.depends('amount_total')
    def _compute_validate_payment_form(self):
        """
        Calcular si se debe colocar la forma de pago
        :return:
        """
        self.validate_payment_form = self.amount_total > 1000

    @api.constrains('serial_number')
    def _check_serial_number(self):
        """
        Verificamos qué número de serie de proveedores sea correcto
        :return:
        """
        if self.type not in self.ISSUANCE_DOCUMENTS:
            if not re.match("\d{3,}-\d{3,}", self.serial_number):
                raise ValidationError("Nº Serie debe ser 001-001.")

    @api.multi
    def invoice_validate(self):
        """
        ME: Revisamos factura d cliente no esté repetida
        :return:
        """
        result = super(Invoice, self).invoice_validate()
        self._check_duplicate_reference()
        return result

    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            # MM: Le quitamos el filtro de la compañía
            # refuse to validate a vendor bill/credit note if there already exists one with the same reference for the same partner,
            # because it's probably a double encoding of the same bill/credit note
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference),
                                ('commercial_partner_id', '=', invoice.commercial_partner_id.id),
                                ('state', 'in', ['open', 'paid']),
                                ('id', '!=', invoice.id)]):
                    raise UserError(_(
                        "Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."))

    @api.multi
    def _check_duplicate_reference(self):
        """
        Verificamos no existan documentos de cliente repetidos
        :return:
        """
        for invoice in self:
            if invoice.type in ('out_invoice', 'out_refund') and invoice.reference and not invoice.is_electronic:
                if self.search([('type', '=', invoice.type), ('reference', '=', invoice.reference),
                                ('id', '!=', invoice.id), ('company_id', '=', invoice.company_id.id)]):
                    raise UserError(_(
                        "Se detectó secuencial duplicado para pre-impreso de Autorización del SRI (%s)." % invoice.sri_authorization_id.authorization))

    @api.multi
    def copy(self, default=None):
        """
        Al duplicar eliminamos origen y comentario si está cancelada
        :param default:
        :return:
        """
        default = default or {}
        default['comment'] = False if self.state == 'cancel' else self.comment
        default['origin'] = False
        record = super(Invoice, self).copy(default=default)
        return record

    @api.model
    def _default_point_printing(self):
        """
        Defecto de punto de impresión
        :return:
        """
        company = self.env.user.company_id.id
        point_printing_ids = self.env['sri.point.printing'].search([('company_id', '=', company)], limit=1)
        return point_printing_ids

    @api.model
    def _default_payment_form(self):
        """
        Defecto forma de pago
        :return:
        """
        payment_forms_ids = self.env['sri.payment.forms'].search([], limit=1)
        return payment_forms_ids

    @api.model
    def _default_authorized_voucher(self):
        """
        Por defecto colocamos el tipo de comprobante dependiendo del TYPE
        :return:
        """
        context = dict(self._context or {})
        object_voucher = self.env['sri.authorized.vouchers']
        voucher = False
        if context.get('type') and not context.get('default_authorized_voucher'):
            type = context.get('type')
            if type == 'in_invoice':
                code = '01'
            elif type == 'out_invoice':
                code = '18'
            elif type == 'in_refund':
                code = '05'
            else:
                code = '04'
            voucher = object_voucher.search([('code', '=', code)])
        elif context.get('default_authorized_voucher'):
            voucher = object_voucher.search([('code', '=', context.get('default_authorized_voucher'))])
        return voucher.id if voucher else False

    @api.one
    @api.depends('type', 'point_printing_id')
    def _compute_is_electronic(self):
        """
        Dejar para futuras implementaciones de F.E. (Lo colocamos en Falso)
        :return:
        """
        self.is_electronic = False

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        """
        ME: Aumentamos dirección de cliente
        :return:
        """
        res = super(Invoice, self)._onchange_partner_id()
        self.billing_adress = self.partner_id.street if self.partner_id else '-'
        return res

    authorized_voucher_id = fields.Many2one('sri.authorized.vouchers', 'Tipo de comprobante',
                                            readonly=True, states={'draft': [('readonly', False)]},
                                            required=True,
                                            default=_default_authorized_voucher)
    invoice_number = fields.Char('Secuencial', readonly=True, states={'draft': [('readonly', False)]},
                                 help="Número de factura de la compañía según el tipo.", copy=False, size=9)  # CM
    validate_payment_form = fields.Boolean('Validación forma de pago', compute='_compute_validate_payment_form')
    payment_form_id = fields.Many2one('sri.payment.forms', string='Forma de pago', readonly=True,
                                      states={'draft': [('readonly', False)]}, default=_default_payment_form)
    point_printing_id = fields.Many2one('sri.point.printing', string='Punto de impresión', readonly=True,
                                        states={'draft': [('readonly', False)]}, default=_default_point_printing)
    sri_authorization_id = fields.Many2one('sri.authorization', string='Autorización SRI', readonly=True,
                                           domain="[('authorized_voucher_id.code', '=', {'out_invoice': ['18'], 'out_refund': ['04']}.get(type, [])), ('point_printing_id', '=', point_printing_id)]",
                                           states={'draft': [('readonly', False)]})
    authorization = fields.Char('Nº Autorización', readonly=True, size=49,
                                states={'draft': [('readonly', False)]})
    reference = fields.Char('Nº Documento (SRI)', compute='_compute_reference', store=True, readonly=True,
                            copy=False)  # Modificamos el campo para facilitar referencia (SRI Ecuador)
    proof_support_id = fields.Many2one('sri.proof.support', string='Sustento del comprobante', readonly=True,
                                       states={'draft': [('readonly', False)]})
    serial_number = fields.Char(string='Nº Serie', default='001-001', size=7,
                                readonly=True, states={'draft': [('readonly', False)]})
    is_electronic = fields.Boolean(string='Es electrónica?',
                                   store=True,
                                   help="Técnico: sirve para saber si el documento es electrónico.",
                                   compute='_compute_is_electronic')
    concept = fields.Char('Concepto', readonly=True, states={'draft': [('readonly', False)]})
    billing_adress = fields.Char('Dirección de facturación', readonly=True, states={'draft': [('readonly', False)]},
                                 track_visibility='onchange')