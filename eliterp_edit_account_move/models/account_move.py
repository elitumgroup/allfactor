# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class Move(models.Model):
    _inherit = 'account.move'

    editing = fields.Boolean('Editando', default=False, help="Sirve para saber si se está editando asiento contable.")
