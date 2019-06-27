# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

TYPE = {
    'debit': 'Nota de débito bancaria',
    'credit': 'Nota de crédito bancaria'
}


class BankNoteLine(models.Model):
    _name = "account.bank.note.line"
    _description = _("Línea de nota bancaria")

    account_id = fields.Many2one('account.account', required=True, string="Cuenta contable")
    amount_credit = fields.Float('Monto (Haber)')
    amount = fields.Float('Monto (Debe)')
    note_id = fields.Many2one('account.bank.note', string='Nota bancaria', ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Compañía',
                                 related='note_id.company_id', store=True, readonly=True, related_sudo=False)


class BankNote(models.Model):
    _name = 'account.bank.note'

    _description = _("Nota bancaria")

    @api.model
    def create(self, vals):
        """
        MM: Creamos nuevo registro y validamos período contable
        :param vals:
        :return: object
        """
        if 'note_date' in vals:
            self.env['account.fiscal.year'].valid_period(vals['note_date'])
        res = super(BankNote, self).create(vals)
        return res

    @api.multi
    def action_button_print(self):
        """
        Imprimimos nota bancaria
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_account_bank_note.action_report_bank_note').report_action(self)

    @api.multi
    def action_button_posted(self):
        """
        Contabilizamos la nota bancaria dependiendo del tipo
        le creamos el nombre.
        """
        journal = self._get_journal()
        move_id = self.env['account.move'].create({
            'journal_id': journal.id,
            'ref': self.concept,
            'date': self.note_date,
        })
        MoveLine = self.env['account.move.line']
        if self.type == "debit":
            MoveLine.with_context(check_move_validity=False).create({
                'name': self.journal_id.name,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id  if self.partner_id else False,
                'account_id': self.journal_id.default_debit_account_id.id,
                'move_id': move_id.id,
                'debit': 0.00,
                'credit': self.amount,
                'date': self.note_date
            })
        if self.type == "credit":
            MoveLine.with_context(check_move_validity=False).create({
                'name': self.journal_id.name,
                'journal_id': journal.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'account_id': self.journal_id.default_credit_account_id.id,
                'move_id': move_id.id,
                'debit': self.amount,
                'credit': 0.00,
                'date': self.note_date
            })
        number_accounts = 0
        for line in self.account_ids:
            number_accounts -= 1
            if number_accounts == 0:
                MoveLine.with_context(check_move_validity=True).create({
                    'name': self.concept if self.concept else '/',
                    'journal_id': move_id.journal_id.id,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'credit': line.amount_credit,
                    'debit': line.amount,
                    'date': self.note_date
                })
            else:
                MoveLine.with_context(check_move_validity=False).create({
                    'name': self.concept if self.concept else '/',
                    'journal_id': move_id.journal_id.id,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'credit': line.amount_credit,
                    'debit': line.amount,
                    'date': self.note_date
                })
        if self.type == "debit":
            move_name = 'NDBA-{0}-{1}'.format(
                self.company_id.name[:3],
                self.journal_id.sequence_id.next_by_id()
            )
            move_id.with_context(my_moves=True, move_name=move_name).post()
        else:
            move_id.post()
        return self.write({
            'state': 'posted',
            'name': move_id.name,
            'move_id': move_id.id
        })

    def _get_journal(self):
        """
        Obtenemos el diario de la nota bancaria
        :return:
        """
        company = self.company_id
        domain = [
            ('name', '=', TYPE[self.type]),
            ('company_id', '=', company.id)
        ]
        journal = self.env['account.journal'].search(domain, limit=1)
        if not journal:
            raise UserError(_("No está definido el diario %s para compañía: %s") % (TYPE[self.type], company.name))
        return journal

    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0:
            raise ValidationError(_("La nota bancaria debe tener un monto mayor a 0."))

    @api.multi
    def unlink(self):
        """
        No borrar registros con movimientos contables
        :return:
        """
        for record in self:
            if record.move_id:
                raise UserError(_(
                    'No puedes borrar una nota bancaria con asiento contable.'))
        return super(BankNote, self).unlink()

    name = fields.Char('Referencia', copy=False, index=True)
    concept = fields.Char('Concepto')
    note_date = fields.Date('Fecha de nota bancaria', default=fields.Date.context_today, required=True, readonly=True,
                            states={'draft': [('readonly', False)]})
    amount = fields.Monetary('Monto', required=True, readonly=True,
                             states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal', 'Banco', required=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]})
    move_id = fields.Many2one('account.move', string='Asiento contable', copy=False, readonly=True)

    type = fields.Selection([('credit', 'Crédito'), ('debit', 'Débito')], string='Tipo de nota bancaria')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Contabilizado'),
        ('cancel', 'Anulado')
    ], readonly=True, default='draft', copy=False, string="Estado")
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                  string="Moneda")
    partner_id = fields.Many2one('res.partner', string='Empresa')
    account_ids = fields.One2many('account.bank.note.line',
                                  'note_id',
                                  string='Líneas de nota bancaria',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    # Campo account_id (Ocultar)